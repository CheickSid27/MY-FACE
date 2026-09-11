"""Cycle de vie des commandes : expiration des commandes jamais payees,
changements de statut (avec SMS de confirmation), menage des paniers.

Pourquoi l'expiration : une commande creee puis jamais payee (client parti,
QR jamais scanne) restait "en attente" pour toujours, polluant les
statistiques et la liste de l'organisateur. Passe ORDER_PENDING_TTL_MINUTES,
elle est annulee (statut CANCELLED).

Aucune tache periodique : l'expiration est appliquee au demarrage et a la
lecture (statut consulte par le client, liste/statistiques de
l'organisateur). Un minuteur qui interrogerait la base en permanence
empecherait Neon de se mettre en veille (meme probleme que l'ancien dossier
surveille, voir services/folder_watcher.py).

Une commande "awaiting_confirmation" (le client dit avoir paye) n'expire
JAMAIS automatiquement : de l'argent a peut-etre ete envoye, seul
l'organisateur tranche."""

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.cart import CartSession
from app.models.order import Order, OrderStatus
from app.services.sms import get_sms_service

logger = logging.getLogger("myface.orders")
settings = get_settings()

EXPIRABLE_STATUSES = (OrderStatus.PENDING, OrderStatus.PROCESSING)
# Paniers expires conserves quelques jours (diagnostic) avant suppression.
CART_RETENTION_AFTER_EXPIRY = timedelta(days=7)


def _pending_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=settings.order_pending_ttl_minutes)


def is_stale(order: Order) -> bool:
    return order.status in EXPIRABLE_STATUSES and order.created_at < _pending_cutoff()


async def expire_stale_orders(db: AsyncSession, event_id=None) -> int:
    stmt = (
        update(Order)
        .where(Order.status.in_(EXPIRABLE_STATUSES), Order.created_at < _pending_cutoff())
        .values(status=OrderStatus.CANCELLED)
    )
    if event_id is not None:
        stmt = stmt.where(Order.event_id == event_id)
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount:
        logger.info("%d commande(s) jamais payee(s) annulee(s)", result.rowcount)
    return result.rowcount


async def expire_order_if_stale(order: Order, db: AsyncSession) -> bool:
    if not is_stale(order):
        return False
    order.status = OrderStatus.CANCELLED
    await db.commit()
    await db.refresh(order)
    return True


async def set_order_status(order: Order, new_status: OrderStatus, db: AsyncSession) -> None:
    """Point unique de changement de statut "final" d'une commande (webhook
    operateur, validation/rejet/annulation par l'organisateur) : le SMS de
    confirmation part des qu'une commande devient payee, quel que soit le
    chemin."""
    order.status = new_status
    await db.commit()
    await db.refresh(order)

    if new_status == OrderStatus.SUCCESS:
        sms = get_sms_service()
        download_url = f"{settings.app_base_url}/order/{order.id}/download"
        await sms.send_sms(
            order.contact_phone,
            f"MYFACE: votre paiement est confirme. Telechargez vos photos ici : {download_url}",
        )


async def purge_expired_carts(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - CART_RETENTION_AFTER_EXPIRY
    result = await db.execute(delete(CartSession).where(CartSession.expires_at < cutoff))
    await db.commit()
    if result.rowcount:
        logger.info("%d panier(s) expire(s) supprime(s)", result.rowcount)
    return result.rowcount


async def run_startup_maintenance(session_factory: Callable[[], AsyncSession]) -> None:
    try:
        async with session_factory() as db:
            await expire_stale_orders(db)
            await purge_expired_carts(db)
    except Exception:
        logger.exception("Maintenance des commandes au demarrage : echec")
