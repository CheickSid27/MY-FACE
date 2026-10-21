"""Conservation des donnees, telle que declaree a l'ARTCI :

- selfie : jamais enregistre (voir routers/faces.py) ;
- photos et empreintes faciales : supprimees `retention_photo_days` jours
  (90) apres la date de l'evenement ; l'evenement, lui, reste (nom, date,
  commandes), avec la date de suppression des photos ;
- commandes : le numero de telephone du client est efface
  `retention_order_days` jours (1 an) apres la commande ; montant et date
  restent, sans donnee personnelle, pour la comptabilite.

Un evenement peut etre exempte par un admin (evenement de demonstration du
site, fait de photos de banque d'images).

Tant que RETENTION_ENABLED n'est pas a true, rien n'est supprime : le
passage quotidien journalise seulement ce qu'il ferait (simulation), et la
page Reglages de l'admin affiche la liste."""

import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.event import Event
from app.models.order import Order
from app.models.photo import Photo
from app.services.face_clusters import face_cluster_cache
from app.services.storage import StorageService

logger = logging.getLogger("myface.retention")

ANONYMIZED_PHONE = "(supprimé)"

# Dossiers des fichiers d'une photo dans le stockage (voir ingestion.py,
# watermark.py, face_crops.py). Les QR marchands (payment_qr/) ne sont pas
# des donnees des invites : ils restent.
_PHOTO_PREFIXES = ("originals", "thumbnails", "previews", "previews-wm", "face-crops")


@dataclass
class ExpiredEvent:
    event_id: uuid.UUID
    name: str
    date: datetime
    photo_count: int


@dataclass
class RetentionReport:
    enabled: bool
    photo_days: int
    order_days: int
    events: list[ExpiredEvent] = field(default_factory=list)
    orders_to_anonymize: int = 0
    photos_deleted: int = 0
    orders_anonymized: int = 0


def photos_deadline(event: Event) -> datetime | None:
    """Date a partir de laquelle les photos de l'evenement sont supprimees
    (None : evenement exempte)."""
    if event.retention_exempt:
        return None
    return event.date + timedelta(days=get_settings().retention_photo_days)


async def find_expired_events(db: AsyncSession, now: datetime) -> list[ExpiredEvent]:
    settings = get_settings()
    cutoff = now - timedelta(days=settings.retention_photo_days)
    rows = await db.execute(
        select(Event.id, Event.name, Event.date, func.count(Photo.id))
        .join(Photo, Photo.event_id == Event.id)
        .where(Event.date < cutoff, Event.retention_exempt.is_(False))
        .group_by(Event.id)
        .order_by(Event.date)
    )
    return [ExpiredEvent(event_id=i, name=n, date=d, photo_count=c) for i, n, d, c in rows.all()]


async def count_orders_to_anonymize(db: AsyncSession, now: datetime) -> int:
    cutoff = now - timedelta(days=get_settings().retention_order_days)
    result = await db.execute(
        select(func.count(Order.id)).where(Order.created_at < cutoff, Order.contact_phone != ANONYMIZED_PHONE)
    )
    return result.scalar_one()


async def purge_event_photos(event_id: uuid.UUID, storage: StorageService, db: AsyncSession) -> int:
    """Supprime toutes les photos d'un evenement : lignes en base (avec, en
    cascade, empreintes faciales, articles de panier et lignes de commande),
    puis fichiers du stockage. Renvoie le nombre de photos supprimees."""
    result = await db.execute(delete(Photo).where(Photo.event_id == event_id))
    await db.execute(update(Event).where(Event.id == event_id).values(photos_purged_at=func.now()))
    await db.commit()
    face_cluster_cache.invalidate(event_id, drop=True)
    # Apres le commit : si la base refuse, aucun fichier n'est perdu.
    for prefix in _PHOTO_PREFIXES:
        try:
            await storage.delete_prefix(f"events/{event_id}/{prefix}/")
        except Exception:
            logger.exception("Evenement %s : echec du nettoyage de %s/", event_id, prefix)
    return result.rowcount or 0


async def anonymize_old_orders(db: AsyncSession, now: datetime) -> int:
    cutoff = now - timedelta(days=get_settings().retention_order_days)
    result = await db.execute(
        update(Order)
        .where(Order.created_at < cutoff, Order.contact_phone != ANONYMIZED_PHONE)
        .values(contact_phone=ANONYMIZED_PHONE)
    )
    await db.commit()
    return result.rowcount or 0


async def build_report(db: AsyncSession, now: datetime | None = None) -> RetentionReport:
    settings = get_settings()
    now = now or datetime.now(timezone.utc)
    return RetentionReport(
        enabled=settings.retention_enabled,
        photo_days=settings.retention_photo_days,
        order_days=settings.retention_order_days,
        events=await find_expired_events(db, now),
        orders_to_anonymize=await count_orders_to_anonymize(db, now),
    )


async def run_retention(
    storage: StorageService,
    session_factory: Callable[[], AsyncSession],
    now: datetime | None = None,
    force: bool = False,
) -> RetentionReport:
    """Un passage : supprime (ou, en simulation, liste seulement) ce qui a
    depasse sa duree de conservation. `force` : execute meme si
    RETENTION_ENABLED est faux (tests)."""
    now = now or datetime.now(timezone.utc)
    async with session_factory() as db:
        report = await build_report(db, now)

    if not (report.enabled or force):
        if report.events or report.orders_to_anonymize:
            logger.info(
                "Conservation (simulation, RETENTION_ENABLED=false) : %d evenement(s), %d photo(s) "
                "et %d numero(s) de commande seraient supprimes",
                len(report.events),
                sum(e.photo_count for e in report.events),
                report.orders_to_anonymize,
            )
        return report

    for expired in report.events:
        async with session_factory() as db:
            deleted = await purge_event_photos(expired.event_id, storage, db)
        report.photos_deleted += deleted
        logger.info("Conservation : %d photo(s) de l'evenement %s supprimees", deleted, expired.event_id)
    async with session_factory() as db:
        report.orders_anonymized = await anonymize_old_orders(db, now)
    if report.orders_anonymized:
        logger.info("Conservation : numero efface sur %d commande(s)", report.orders_anonymized)
    return report


async def retention_loop(storage: StorageService, session_factory: Callable[[], AsyncSession]) -> None:
    """Passage au demarrage (apres un court delai) puis toutes les N heures."""
    await asyncio.sleep(60)
    while True:
        try:
            await run_retention(storage, session_factory)
        except Exception:
            logger.exception("Conservation des donnees : echec du passage")
        await asyncio.sleep(max(1, get_settings().retention_interval_hours) * 3600)
