"""Espace photographe / admin (application MYFACE Pro) : ce que l'accueil,
l'onglet Ventes et le centre de notifications affichent d'un coup d'oeil,
sur tous les evenements que l'utilisateur gere (tous pour un admin).

Peu de requetes par appel : la base (Neon) est a ~200 ms par aller-retour,
chaque ecran doit rester rapide sur telephone."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.event import Event
from app.models.event_payment_method import EventPaymentMethod
from app.models.order import Order, OrderItem, OrderStatus
from app.models.pack_purchase import PackPurchase, PackPurchaseStatus
from app.models.photo import IndexingStatus, Photo
from app.models.user import User, UserRole
from app.schemas.workspace import ActivityItem, LiveEvent, TodoItem, WorkspaceOrder, WorkspaceSummary
from app.services import paystack
from app.services.orders import expire_stale_orders
from app.services.packs import effective_photo_limit, get_pack
from app.services.retention import photos_deadline

router = APIRouter(prefix="/workspace", tags=["workspace"])

# Seuils des rappels de l'accueil
PACK_ALMOST_FULL = 0.8
DEADLINE_WARNING = timedelta(days=14)
ACTIVITY_WINDOW = timedelta(days=14)


def _fmt(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ")


async def _scope_events(db: AsyncSession, user: User) -> list[tuple[Event, int, User]]:
    query = (
        select(Event, func.count(Photo.id), User)
        .outerjoin(Photo, Photo.event_id == Event.id)
        .join(User, User.id == Event.organizer_id)
        .group_by(Event.id, User.id)
        .order_by(Event.date.desc())
    )
    if user.role != UserRole.ADMIN:
        query = query.where(Event.organizer_id == user.id)
    return [tuple(row) for row in (await db.execute(query)).all()]


def _pick_live_event(rows: list[tuple[Event, int, User]], now: datetime) -> tuple[Event, int, User, str] | None:
    """L'evenement a mettre en avant : celui du jour, sinon le prochain,
    sinon le plus recent."""
    if not rows:
        return None
    today = [r for r in rows if abs((r[0].date - now).total_seconds()) <= 18 * 3600]
    if today:
        return (*min(today, key=lambda r: abs((r[0].date - now).total_seconds())), "live")
    upcoming = [r for r in rows if r[0].date > now]
    if upcoming:
        return (*min(upcoming, key=lambda r: r[0].date), "upcoming")
    return (*rows[0], "past")


@router.get("/summary", response_model=WorkspaceSummary)
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceSummary:
    now = datetime.now(timezone.utc)
    rows = await _scope_events(db, current_user)
    event_ids = [event.id for event, _, _ in rows]
    todo: list[TodoItem] = []

    sales_today = 0.0
    paid_today = 0
    to_confirm = 0
    with_payment: set[uuid.UUID] = set()
    if event_ids:
        await expire_stale_orders(db)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        totals = (
            await db.execute(
                select(
                    func.coalesce(
                        func.sum(
                            case(
                                ((Order.status == OrderStatus.SUCCESS) & (Order.created_at >= start_of_day), Order.total_amount),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                    func.count(case(((Order.status == OrderStatus.SUCCESS) & (Order.created_at >= start_of_day), 1))),
                    func.count(case((Order.status == OrderStatus.AWAITING_CONFIRMATION, 1))),
                ).where(Order.event_id.in_(event_ids))
            )
        ).one()
        sales_today, paid_today, to_confirm = float(totals[0]), int(totals[1]), int(totals[2])
        with_payment = set(
            (
                await db.execute(
                    select(EventPaymentMethod.event_id).where(EventPaymentMethod.event_id.in_(event_ids)).distinct()
                )
            )
            .scalars()
            .all()
        )

    if to_confirm:
        todo.append(
            TodoItem(
                kind="orders",
                title=f"{to_confirm} paiement{'s' if to_confirm > 1 else ''} à confirmer",
                detail="Vérifiez la réception sur votre Wave ou votre Orange Money",
                href="/admin/ventes",
            )
        )

    if current_user.role == UserRole.ADMIN:
        pending_packs = (
            await db.execute(select(func.count(PackPurchase.id)).where(PackPurchase.status == PackPurchaseStatus.PENDING))
        ).scalar_one()
        if pending_packs:
            todo.append(
                TodoItem(
                    kind="packs",
                    title=f"{pending_packs} pack{'s' if pending_packs > 1 else ''} à valider",
                    detail="Paiements de photographes à vérifier",
                    href="/admin/packs",
                )
            )

    for event, photo_count, owner in rows:
        mine = event.organizer_id == current_user.id
        limit = effective_photo_limit(event, owner)
        if mine and limit and photo_count >= PACK_ALMOST_FULL * limit:
            todo.append(
                TodoItem(
                    kind="pack_full",
                    title=f"{event.name} : {photo_count} / {limit} photos",
                    detail=f"Pack {get_pack(event.pack).name} presque plein, passez au pack supérieur",
                    href=f"/admin/events/{event.id}?onglet=reglages",
                )
            )
        no_payment = (
            not event.pricing.get("offert")
            and event.id not in with_payment
            and not paystack.online_payment_available(owner)
            and event.date > now - timedelta(days=2)
        )
        if mine and no_payment:
            todo.append(
                TodoItem(
                    kind="no_payment",
                    title=f"{event.name} : aucun moyen de paiement",
                    detail="Ajoutez votre Wave ou votre Orange Money, sinon les invités ne peuvent pas payer",
                    href=f"/admin/events/{event.id}?onglet=ventes",
                )
            )
        deadline = photos_deadline(event)
        if mine and deadline and event.photos_purged_at is None and now < deadline <= now + DEADLINE_WARNING:
            todo.append(
                TodoItem(
                    kind="deadline",
                    title=event.name,
                    detail=f"Photos en ligne jusqu'au {deadline.strftime('%d/%m/%Y')}, puis supprimées",
                    href=f"/admin/events/{event.id}",
                )
            )

    live = None
    picked = _pick_live_event(rows, now)
    if picked:
        event, photo_count, owner, moment = picked
        done = (
            await db.execute(
                select(func.count(Photo.id)).where(
                    Photo.event_id == event.id, Photo.indexing_status == IndexingStatus.DONE
                )
            )
        ).scalar_one()
        live = LiveEvent(
            id=event.id,
            name=event.name,
            date=event.date,
            location=event.location,
            pack=event.pack,
            photo_count=photo_count,
            photo_limit=effective_photo_limit(event, owner),
            indexed=int(done),
            to_index=photo_count,
            moment=moment,
        )

    return WorkspaceSummary(
        event=live,
        events_count=len(rows),
        sales_today=sales_today,
        paid_orders_today=paid_today,
        orders_to_confirm=to_confirm,
        todo=todo,
    )


async def _orders(
    db: AsyncSession, user: User, statuses: list[OrderStatus], since: datetime | None, limit: int
) -> list[WorkspaceOrder]:
    query = (
        select(
            Order,
            Event.name,
            func.count(OrderItem.id),
            func.count(case((OrderItem.print_requested.is_(True), 1))),
        )
        .join(Event, Event.id == Order.event_id)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(Order.status.in_(statuses))
        .group_by(Order.id, Event.name)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    if user.role != UserRole.ADMIN:
        query = query.where(Event.organizer_id == user.id)
    if since is not None:
        query = query.where(Order.created_at >= since)
    return [
        WorkspaceOrder(
            id=order.id,
            event_id=order.event_id,
            event_name=event_name,
            contact_phone=order.contact_phone,
            total_amount=order.total_amount,
            currency=order.currency,
            status=order.status,
            payment_method=order.payment_method,
            payment_reference=order.payment_reference,
            photo_count=photo_count,
            print_count=print_count,
            created_at=order.created_at,
        )
        for order, event_name, photo_count, print_count in (await db.execute(query)).all()
    ]


@router.get("/orders", response_model=list[WorkspaceOrder])
async def list_orders(
    view: str = Query(default="to_confirm", pattern="^(to_confirm|paid)$"),
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkspaceOrder]:
    """Ventes de tous les evenements geres : a confirmer (toutes), ou payees
    sur les `days` derniers jours."""
    await expire_stale_orders(db)
    if view == "to_confirm":
        return await _orders(db, current_user, [OrderStatus.AWAITING_CONFIRMATION], None, 200)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return await _orders(db, current_user, [OrderStatus.SUCCESS], since, 200)


@router.get("/activity", response_model=list[ActivityItem])
async def list_activity(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ActivityItem]:
    """Fil des notifications : ventes, packs, suppressions a venir et, pour
    l'equipe MYFACE, packs a valider et nouveaux photographes. Calcule a la
    volee depuis les donnees (rien de plus a stocker) ; « lu » est garde
    par l'appareil."""
    now = datetime.now(timezone.utc)
    since = now - ACTIVITY_WINDOW
    items: list[ActivityItem] = []

    for order in await _orders(
        db, current_user, [OrderStatus.AWAITING_CONFIRMATION, OrderStatus.SUCCESS], since, 40
    ):
        waiting = order.status == OrderStatus.AWAITING_CONFIRMATION
        items.append(
            ActivityItem(
                id=f"order-{order.id}-{order.status.value}",
                kind="order_waiting" if waiting else "order_paid",
                title="Paiement à confirmer" if waiting else "Commande payée",
                body=f"{_fmt(order.total_amount)} {order.currency}, {order.event_name}",
                href="/admin/ventes" if waiting else f"/admin/events/{order.event_id}?onglet=ventes",
                at=order.created_at,
            )
        )

    purchases_query = (
        select(PackPurchase, Event.name)
        .join(Event, Event.id == PackPurchase.event_id)
        .where(PackPurchase.created_at >= since)
        .order_by(PackPurchase.created_at.desc())
        .limit(20)
    )
    if current_user.role != UserRole.ADMIN:
        purchases_query = purchases_query.where(Event.organizer_id == current_user.id)
    for purchase, event_name in (await db.execute(purchases_query)).all():
        pack_name = get_pack(purchase.pack).name
        if purchase.status == PackPurchaseStatus.PAID:
            title, kind = f"Pack {pack_name} activé", "pack_paid"
        elif purchase.status == PackPurchaseStatus.REJECTED:
            title, kind = f"Paiement du pack {pack_name} refusé", "pack_rejected"
        elif purchase.status == PackPurchaseStatus.PENDING and current_user.role == UserRole.ADMIN:
            title, kind = f"Pack {pack_name} à valider", "pack_pending"
        else:
            continue
        items.append(
            ActivityItem(
                id=f"pack-{purchase.id}-{purchase.status.value}",
                kind=kind,
                title=title,
                body=event_name,
                href="/admin/packs" if kind == "pack_pending" else f"/admin/events/{purchase.event_id}?onglet=reglages",
                at=purchase.decided_at or purchase.created_at,
            )
        )

    for event, _, _ in await _scope_events(db, current_user):
        deadline = photos_deadline(event)
        if (
            event.organizer_id == current_user.id
            and deadline
            and event.photos_purged_at is None
            and now < deadline <= now + DEADLINE_WARNING
        ):
            items.append(
                ActivityItem(
                    id=f"deadline-{event.id}",
                    kind="deadline",
                    title=event.name,
                    body=f"Photos supprimées le {deadline.strftime('%d/%m/%Y')}. Prévenez vos clients.",
                    href=f"/admin/events/{event.id}",
                    at=deadline - DEADLINE_WARNING,
                )
            )

    if current_user.role == UserRole.ADMIN:
        newcomers = (
            await db.execute(
                select(User)
                .where(User.role == UserRole.PHOTOGRAPHE, User.created_at >= since)
                .order_by(User.created_at.desc())
                .limit(10)
            )
        ).scalars()
        for user in newcomers:
            items.append(
                ActivityItem(
                    id=f"user-{user.id}",
                    kind="new_photographer",
                    title="Nouveau photographe inscrit",
                    body=user.public_name or user.email,
                    href="/admin/users",
                    at=user.created_at,
                )
            )

    items.sort(key=lambda item: item.at, reverse=True)
    return items[:50]
