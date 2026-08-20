import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password
from app.deps import get_current_user, require_admin
from app.models.event import Event
from app.models.order import Order, OrderItem, OrderStatus
from app.models.photo import IndexingStatus, Photo
from app.models.user import User
from app.routers.events import _get_owned_event
from app.routers.payments import _apply_webhook_result
from app.schemas.order import OrderConfirmRequest, OrderRead
from app.schemas.stats import DailySales, EventStats
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/events/{event_id}/stats", response_model=EventStats)
async def get_event_stats(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventStats:
    event = await _get_owned_event(event_id, current_user, db)

    photo_counts = await db.execute(
        select(
            func.count(Photo.id),
            func.count(case((Photo.indexing_status == IndexingStatus.DONE, 1))),
            func.count(
                case((Photo.indexing_status.in_([IndexingStatus.PENDING, IndexingStatus.PROCESSING]), 1))
            ),
        ).where(Photo.event_id == event_id)
    )
    photo_count, photos_indexed, photos_pending = photo_counts.one()

    order_counts = await db.execute(
        select(Order.status, func.count(Order.id)).where(Order.event_id == event_id).group_by(Order.status)
    )
    counts_by_status = {status: 0 for status in OrderStatus}
    for order_status, count in order_counts.all():
        counts_by_status[order_status] = count

    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0.0)).where(
            Order.event_id == event_id, Order.status == OrderStatus.SUCCESS
        )
    )
    total_revenue = revenue_result.scalar_one()

    photos_sold_result = await db.execute(
        select(func.count(OrderItem.id))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.event_id == event_id, Order.status == OrderStatus.SUCCESS)
    )
    photos_sold = photos_sold_result.scalar_one()

    sales_by_day_result = await db.execute(
        select(
            func.date_trunc("day", Order.created_at).label("day"),
            func.sum(Order.total_amount),
            func.count(Order.id),
        )
        .where(Order.event_id == event_id, Order.status == OrderStatus.SUCCESS)
        .group_by("day")
        .order_by("day")
    )
    sales_by_day = [
        DailySales(date=day.date(), revenue=revenue, order_count=count)
        for day, revenue, count in sales_by_day_result.all()
    ]

    currency = event.pricing.get("currency", "XOF") if isinstance(event.pricing, dict) else "XOF"

    return EventStats(
        event_id=str(event_id),
        photo_count=photo_count,
        photos_indexed=photos_indexed,
        photos_pending=photos_pending,
        orders_pending=counts_by_status[OrderStatus.PENDING],
        orders_processing=counts_by_status[OrderStatus.PROCESSING],
        orders_awaiting_confirmation=counts_by_status[OrderStatus.AWAITING_CONFIRMATION],
        orders_success=counts_by_status[OrderStatus.SUCCESS],
        orders_failed=counts_by_status[OrderStatus.FAILED],
        total_revenue=total_revenue,
        currency=currency,
        photos_sold=photos_sold,
        sales_by_day=sales_by_day,
    )


@router.get("/events/{event_id}/orders", response_model=list[OrderRead])
async def list_event_orders(
    event_id: uuid.UUID,
    order_status: OrderStatus | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrderRead]:
    await _get_owned_event(event_id, current_user, db)

    query = (
        select(Order, func.count(OrderItem.id).label("photo_count"))
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(Order.event_id == event_id)
        .group_by(Order.id)
        .order_by(Order.created_at.desc())
    )
    if order_status is not None:
        query = query.where(Order.status == order_status)

    result = await db.execute(query)
    return [
        OrderRead(
            id=order.id,
            contact_phone=order.contact_phone,
            total_amount=order.total_amount,
            currency=order.currency,
            status=order.status,
            payment_method=order.payment_method,
            payment_reference=order.payment_reference,
            photo_count=photo_count,
            created_at=order.created_at,
        )
        for order, photo_count in result.all()
    ]


async def _get_owned_order(order_id: uuid.UUID, current_user: User, db: AsyncSession) -> Order:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    event = await db.get(Event, order.event_id)
    if event is None or event.organizer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse")
    return order


@router.post("/orders/{order_id}/confirm", status_code=status.HTTP_200_OK)
async def confirm_order(
    order_id: uuid.UUID,
    payload: OrderConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Confirme ou rejette une commande en attente apres verification manuelle
    par l'organisateur (paiement Mobile Money hors-app via QR, aucune API
    reelle branchee, voir services/payments.py). Reserve au proprietaire de
    l'evenement."""
    order = await _get_owned_order(order_id, current_user, db)
    if order.status != OrderStatus.AWAITING_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Commande au statut '{order.status.value}', rien a confirmer",
        )

    new_status = OrderStatus.SUCCESS if payload.approved else OrderStatus.FAILED
    await _apply_webhook_result(order.payment_reference, new_status, db)
    return {"status": new_status.value}


@router.get("/users", response_model=list[UserRead])
async def list_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet email est deja utilise")

    user = User(email=payload.email, hashed_password=hash_password(payload.password), role=payload.role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de supprimer votre propre compte")

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    owned_events = await db.execute(select(func.count(Event.id)).where(Event.organizer_id == user_id))
    if owned_events.scalar_one() > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de supprimer un utilisateur organisateur d'evenements existants",
        )

    await db.delete(user)
    await db.commit()
