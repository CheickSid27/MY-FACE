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
from html import escape
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
    # Version mise en page (bouton, couleurs MYFACE) ; le texte reste la
    # version de secours pour les messageries qui n'affichent pas le HTML.
    html: str | None = None


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
        if message.html:
            email.add_alternative(message.html, subtype="html")

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


def _html_layout(title: str, greeting: str, paragraphs: list[str], button_label: str, link: str, note: str) -> str:
    """Mise en page commune des e-mails : tableaux et styles en ligne, seuls
    compris par toutes les messageries (Gmail, Outlook, telephone)."""
    paras = "".join(
        f'<p style="margin:0 0 14px;font-size:15px;line-height:1.55;color:#33484d">{escape(p)}</p>' for p in paragraphs
    )
    safe_link = escape(link)
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{escape(title)}</title></head>
<body style="margin:0;padding:0;background:#f4efe6">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4efe6;padding:28px 12px">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:18px;overflow:hidden;font-family:Arial,Helvetica,sans-serif">
<tr><td style="background:#0e2429;padding:22px 28px">
<span style="font-size:20px;font-weight:bold;letter-spacing:1px;color:#ffffff">MY<span style="color:#f26a1b">FACE</span></span>
</td></tr>
<tr><td style="padding:28px">
<h1 style="margin:0 0 16px;font-size:21px;line-height:1.3;color:#0e2429">{escape(title)}</h1>
<p style="margin:0 0 14px;font-size:15px;line-height:1.55;color:#33484d">{escape(greeting)}</p>
{paras}
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0"><tr><td style="background:#f26a1b;border-radius:12px">
<a href="{safe_link}" style="display:inline-block;padding:14px 26px;font-size:15px;font-weight:bold;color:#0e2429;text-decoration:none">{escape(button_label)}</a>
</td></tr></table>
<p style="margin:0 0 6px;font-size:13px;line-height:1.5;color:#5e7378">Le bouton ne marche pas ? Copiez ce lien dans votre navigateur :</p>
<p style="margin:0 0 20px;font-size:13px;line-height:1.5;word-break:break-all"><a href="{safe_link}" style="color:#b34a08">{safe_link}</a></p>
<p style="margin:0;font-size:13px;line-height:1.5;color:#5e7378">{escape(note)}</p>
</td></tr>
<tr><td style="padding:18px 28px;border-top:1px solid #eae3d6;font-size:12px;line-height:1.5;color:#5e7378">
L'équipe MYFACE, Abidjan · <a href="https://myfaceci.online" style="color:#5e7378">myfaceci.online</a>
</td></tr>
</table>
</td></tr></table>
</body></html>"""


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
        html=_html_layout(
            title="Confirmez votre adresse e-mail",
            greeting=_greeting(name),
            paragraphs=[
                "Merci d'avoir créé votre compte photographe MYFACE.",
                f"Confirmez votre adresse pour créer vos événements et envoyer vos photos. Le lien est valable {hours} heures.",
            ],
            button_label="Confirmer mon adresse",
            link=link,
            note="Vous n'avez pas créé de compte ? Ignorez ce message.",
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
        html=_html_layout(
            title="Choisissez un nouveau mot de passe",
            greeting=_greeting(name),
            paragraphs=[
                "Vous avez demandé à changer le mot de passe de votre compte MYFACE.",
                f"Le lien est valable {minutes} minutes et ne sert qu'une fois.",
            ],
            button_label="Choisir un nouveau mot de passe",
            link=link,
            note="Vous n'avez rien demandé ? Ignorez ce message : votre mot de passe ne change pas.",
        ),
    )
