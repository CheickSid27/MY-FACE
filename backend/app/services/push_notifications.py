"""Notifications Web Push vers la PWA admin (installee sur telephone) :
alerte a chaque commande necessitant une validation manuelle (le client a
clique "J'ai paye", voir routers/payments.py mark_paid), sans dependre d'une
app mobile separee ni d'un service tiers payant.

Si aucune cle VAPID n'est configuree (voir core/config.py), l'envoi est
silencieusement ignore, meme logique que services/sms.py quand Africa's
Talking n'est pas configure : ne jamais faire echouer le flux metier
(paiement) a cause d'une fonctionnalite annexe non configuree.
"""

import asyncio
import json
import logging
import uuid

from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.push_subscription import PushSubscription

logger = logging.getLogger("myface.push_notifications")
settings = get_settings()


def _send_one(subscription: PushSubscription, payload: dict) -> None:
    webpush(
        subscription_info={
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
        },
        data=json.dumps(payload),
        vapid_private_key=settings.vapid_private_key,
        vapid_claims={"sub": settings.vapid_subject},
    )


async def send_push_to_user(user_id: uuid.UUID, db: AsyncSession, title: str, body: str, url: str) -> None:
    if not settings.vapid_private_key:
        return

    result = await db.execute(select(PushSubscription).where(PushSubscription.user_id == user_id))
    subscriptions = result.scalars().all()
    if not subscriptions:
        return

    payload = {"title": title, "body": body, "url": url}
    dead_endpoints = []

    for subscription in subscriptions:
        try:
            await asyncio.to_thread(_send_one, subscription, payload)
        except WebPushException as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in (404, 410):
                # Abonnement expire/revoque (navigateur desinstalle, permission
                # retiree...) : on le nettoie plutot que de reessayer indefiniment.
                dead_endpoints.append(subscription.endpoint)
            else:
                logger.warning("Push notification: echec envoi (%s)", exc)
        except Exception:
            logger.exception("Push notification: erreur inattendue")

    if dead_endpoints:
        await db.execute(delete(PushSubscription).where(PushSubscription.endpoint.in_(dead_endpoints)))
        await db.commit()
