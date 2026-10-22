"""Inscriptions jamais confirmees : un photographe qui ne clique pas sur le
lien recu par e-mail dans le delai (5 minutes par defaut,
UNVERIFIED_ACCOUNT_TTL_MINUTES) voit son inscription annulee, et tout ce
qu'il a pu faire est supprime. Il peut se reinscrire avec la meme adresse.

Rien ne se passe tant que l'envoi d'e-mails n'est pas en place (sinon
personne ne pourrait jamais confirmer)."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.event import Event
from app.models.user import User, UserRole
from app.services.activity import log_activity, user_label
from app.services.storage import StorageService

logger = logging.getLogger("myface.unverified_accounts")

CHECK_INTERVAL_SECONDS = 60


async def purge_unverified_accounts(
    db: AsyncSession, storage: StorageService, now: datetime | None = None
) -> int:
    settings = get_settings()
    if not settings.email_verification_enforced:
        return 0
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=settings.unverified_account_ttl_minutes)
    users = (
        await db.execute(
            select(User).where(
                User.role == UserRole.PHOTOGRAPHE,
                User.email_verified_at.is_(None),
                User.created_at < cutoff,
                User.created_at >= settings.unverified_account_purge_since,
            )
        )
    ).scalars().all()
    for user in users:
        events = (await db.execute(select(Event).where(Event.organizer_id == user.id))).scalars().all()
        event_ids = [event.id for event in events]
        avatar = user.avatar_key
        label = user_label(user)
        for event in events:
            await db.delete(event)
        await db.delete(user)
        await db.commit()
        for event_id in event_ids:
            try:
                await storage.delete_prefix(f"events/{event_id}/")
            except Exception:  # noqa: BLE001
                logger.exception("Inscription annulee : fichiers de %s non supprimes", event_id)
        if avatar:
            try:
                await storage.delete(avatar)
            except Exception:  # noqa: BLE001
                logger.exception("Inscription annulee : photo de profil non supprimee")
        await log_activity(db, "inscription_annulee", actor_label=label, details={"evenements_supprimes": len(event_ids)})
        logger.info("Inscription non confirmee annulee : %s", label)
    return len(users)


async def unverified_accounts_loop(storage: StorageService, session_factory: Callable[[], AsyncSession]) -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        try:
            async with session_factory() as db:
                await purge_unverified_accounts(db, storage)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("Nettoyage des inscriptions non confirmees : echec")
