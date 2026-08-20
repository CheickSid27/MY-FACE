"""Envoi de SMS via Africa's Talking.

NON CONFIGURE par defaut (AFRICASTALKING_USERNAME / AFRICASTALKING_API_KEY
absents) : dans ce cas `send_sms` ne fait AUCUN appel reseau, logue un
avertissement avec le contenu qui aurait ete envoye, et retourne False.
Jamais de simulation silencieuse presentee comme un succes."""

import asyncio
import logging

from app.core.config import get_settings

logger = logging.getLogger("myface.sms")

settings = get_settings()


class SmsService:
    def __init__(self) -> None:
        self._configured = bool(settings.africastalking_username and settings.africastalking_api_key)
        self._sms = None
        if self._configured:
            import africastalking

            africastalking.initialize(settings.africastalking_username, settings.africastalking_api_key)
            self._sms = africastalking.SMS

    async def send_sms(self, phone: str, message: str) -> bool:
        if not self._configured or self._sms is None:
            logger.warning(
                "SMS non envoye (Africa's Talking non configure) - destinataire=%s contenu=%r",
                phone,
                message,
            )
            return False

        def _send() -> dict:
            return self._sms.send(message, [phone], settings.africastalking_sender_id or None)

        try:
            response = await asyncio.to_thread(_send)
            logger.info("SMS envoye a %s: %s", phone, response)
            return True
        except Exception:
            logger.exception("Echec envoi SMS a %s", phone)
            return False


_sms_service: SmsService | None = None


def get_sms_service() -> SmsService:
    global _sms_service
    if _sms_service is None:
        _sms_service = SmsService()
    return _sms_service
