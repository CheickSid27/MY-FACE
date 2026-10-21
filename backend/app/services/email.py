"""Envoi des e-mails transactionnels (confirmation de l'adresse d'un
photographe, mot de passe oublie).

- SMTP_HOST renseigne : envoi par SMTP (Brevo, Resend, Gmail...), dans un
  thread pour ne pas bloquer la boucle d'evenements ;
- sinon : rien ne part, le message et son lien sont ecrits dans les logs du
  backend (`docker compose logs backend`), ce qui permet de tester en local
  ou de confirmer un compte a la main.

Un echec d'envoi est journalise et n'interrompt jamais l'inscription : le
photographe peut redemander le lien depuis son espace."""

import asyncio
import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import make_msgid

from app.core.config import get_settings

logger = logging.getLogger("myface.email")


@dataclass
class OutgoingEmail:
    to: str
    subject: str
    text: str


class EmailService:
    async def send(self, message: OutgoingEmail) -> bool:
        raise NotImplementedError


class ConsoleEmailService(EmailService):
    """Aucun envoi reel : message ecrit dans les logs (et garde en memoire,
    pour les tests)."""

    def __init__(self) -> None:
        self.sent: list[OutgoingEmail] = []

    async def send(self, message: OutgoingEmail) -> bool:
        self.sent.append(message)
        logger.warning(
            "E-mail NON envoye (SMTP_HOST vide) a %s : %s\n%s", message.to, message.subject, message.text
        )
        return True


class SmtpEmailService(EmailService):
    def _send_sync(self, message: OutgoingEmail) -> None:
        settings = get_settings()
        email = EmailMessage()
        email["From"] = settings.smtp_from
        email["To"] = message.to
        email["Subject"] = message.subject
        email["Message-ID"] = make_msgid(domain=settings.smtp_from.rsplit("@", 1)[-1].strip("> "))
        email.set_content(message.text)

        context = ssl.create_default_context()
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context, timeout=20) as smtp:
                self._login_and_send(smtp, email)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                smtp.starttls(context=context)
                self._login_and_send(smtp, email)

    @staticmethod
    def _login_and_send(smtp: smtplib.SMTP, email: EmailMessage) -> None:
        settings = get_settings()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(email)

    async def send(self, message: OutgoingEmail) -> bool:
        try:
            await asyncio.to_thread(self._send_sync, message)
            return True
        except Exception:
            logger.exception("Echec de l'envoi de l'e-mail a %s (%s)", message.to, message.subject)
            return False


_console_service = ConsoleEmailService()


def get_email_service() -> EmailService:
    if get_settings().email_sending_configured:
        return SmtpEmailService()
    return _console_service


def _greeting(name: str | None) -> str:
    return f"Bonjour {name.strip()}," if name and name.strip() else "Bonjour,"


def verification_email(to: str, name: str | None, link: str) -> OutgoingEmail:
    hours = get_settings().email_verification_ttl_hours
    return OutgoingEmail(
        to=to,
        subject="Confirmez votre adresse e-mail MYFACE",
        text=(
            f"{_greeting(name)}\n\n"
            "Merci d'avoir créé votre compte photographe MYFACE.\n"
            "Pour confirmer votre adresse e-mail, ouvrez ce lien :\n\n"
            f"{link}\n\n"
            f"Le lien est valable {hours} heures. Tant que l'adresse n'est pas confirmée, "
            "vous ne pouvez ni créer d'événement ni envoyer de photos.\n\n"
            "Si vous n'avez pas créé de compte, ignorez ce message.\n\n"
            "L'équipe MYFACE\nhttps://myfaceci.online"
        ),
    )


def password_reset_email(to: str, name: str | None, link: str) -> OutgoingEmail:
    minutes = get_settings().password_reset_ttl_minutes
    return OutgoingEmail(
        to=to,
        subject="Choisissez un nouveau mot de passe MYFACE",
        text=(
            f"{_greeting(name)}\n\n"
            "Vous avez demandé à changer le mot de passe de votre compte MYFACE.\n"
            "Pour en choisir un nouveau, ouvrez ce lien :\n\n"
            f"{link}\n\n"
            f"Le lien est valable {minutes} minutes et ne sert qu'une fois.\n\n"
            "Si vous n'avez rien demandé, ignorez ce message : votre mot de passe ne change pas.\n\n"
            "L'équipe MYFACE\nhttps://myfaceci.online"
        ),
    )
