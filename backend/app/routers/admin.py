import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password
from app.deps import get_current_user, require_admin
from app.models.event import Event
from app.models.order import Order, OrderItem, OrderStatus
from app.models.photo import IndexingStatus, Photo
from app.models.user import User
from app.schemas.order import OrderConfirmRequest, OrderDetailRead, OrderItemRead, OrderRead
from app.schemas.stats import DailySales, EventStats
from app.schemas.user import UserCreate, UserRead
from app.services.access import can_manage_event, get_manageable_event
from app.services.orders import EXPIRABLE_STATUSES, expire_stale_orders, set_order_status
from app.services.photo_urls import to_photo_read
from app.services.storage import StorageService, get_storage_service

router = APIRouter(prefix="/admin", tags=["admin"])

settings = get_settings()

# Rejeter = le paiement annonce n'est pas arrive. Possible tant que la
# commande n'est ni payee ni deja close.
_REJECTABLE = (OrderStatus.AWAITING_CONFIRMATION, *EXPIRABLE_STATUSES)


@router.get("/events/{event_id}/stats", response_model=EventStats)
async def get_event_stats(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventStats:
    event = await get_manageable_event(event_id, current_user, db)
    await expire_stale_orders(db, event_id)

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
        orders_cancelled=counts_by_status[OrderStatus.CANCELLED],
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
    await get_manageable_event(event_id, current_user, db)
    await expire_stale_orders(db, event_id)

    query = (
        select(
            Order,
            func.count(OrderItem.id).label("photo_count"),
            func.count(case((OrderItem.print_requested.is_(True), 1))).label("print_count"),
        )
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
            print_count=print_count,
            printed_at=order.printed_at,
            created_at=order.created_at,
        )
        for order, photo_count, print_count in result.all()
    ]


async def _get_owned_order(order_id: uuid.UUID, current_user: User, db: AsyncSession) -> Order:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    event = await db.get(Event, order.event_id)
    if event is None or not can_manage_event(event, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse")
    return order


@router.get("/orders/{order_id}", response_model=OrderDetailRead)
async def get_order_detail(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> OrderDetailRead:
    """Fiche d'une commande (sert de recu) : liste nominative des photos
    achetees, tirages papier demandes, detail du prix et lien de
    telechargement du client, pour savoir ce qu'on valide, quoi imprimer, et
    repondre a un client qui revient avec un probleme."""
    order = await _get_owned_order(order_id, current_user, db)
    event = await db.get(Event, order.event_id)
    result = await db.execute(
        select(OrderItem)
        .where(OrderItem.order_id == order.id)
        .options(selectinload(OrderItem.photo))
    )
    items = sorted(result.scalars().all(), key=lambda item: item.photo.original_filename.lower())

    photos_subtotal = round(sum(item.unit_price for item in items), 2)
    prints_total = round(sum(item.print_price or 0 for item in items if item.print_requested), 2)
    # Lots et remises ne sont pas detailles ligne par ligne a l'achat : leur
    # effet est la difference entre le prix plein et le total effectivement du.
    discount_amount = round(max(0.0, photos_subtotal + prints_total - order.total_amount), 2)

    return OrderDetailRead(
        id=order.id,
        event_id=order.event_id,
        event_name=event.name,
        event_date=event.date,
        contact_phone=order.contact_phone,
        total_amount=order.total_amount,
        currency=order.currency,
        status=order.status,
        payment_method=order.payment_method,
        payment_reference=order.payment_reference,
        photo_count=len(items),
        print_count=sum(1 for item in items if item.print_requested),
        printed_at=order.printed_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
        photos_subtotal=photos_subtotal,
        prints_total=prints_total,
        discount_amount=discount_amount,
        download_url=f"{settings.app_base_url}/order/{order.id}/download",
        items=[
            OrderItemRead(
                photo=await to_photo_read(item.photo, storage, clean_preview=True),
                unit_price=item.unit_price,
                print_requested=item.print_requested,
                print_price=item.print_price,
            )
            for item in items
        ],
    )


@router.post("/orders/{order_id}/confirm", status_code=status.HTTP_200_OK)
async def confirm_order(
    order_id: uuid.UUID,
    payload: OrderConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Valide ou rejette une commande apres verification manuelle par
    l'organisateur (paiement Mobile Money hors-app via QR ou especes).

    - Valider : possible depuis tout statut non paye, y compris une commande
      expiree/annulee ou rejetee, cas reel d'un client qui a bien paye mais
      n'a jamais clique "J'ai paye", ou trop tard. L'organisateur, qui voit
      le transfert arriver sur son compte, doit pouvoir la valider.
    - Rejeter : le paiement annonce n'est jamais arrive."""
    order = await _get_owned_order(order_id, current_user, db)
    if payload.approved:
        if order.status == OrderStatus.SUCCESS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Commande deja payee")
        new_status = OrderStatus.SUCCESS
    else:
        if order.status not in _REJECTABLE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Commande au statut '{order.status.value}', rien a rejeter",
            )
        new_status = OrderStatus.FAILED

    await set_order_status(order, new_status, db)
    return {"status": new_status.value}


@router.post("/orders/{order_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Annule une commande jamais payee (client parti sans payer), sans
    attendre son expiration automatique."""
    order = await _get_owned_order(order_id, current_user, db)
    if order.status not in EXPIRABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Commande au statut '{order.status.value}', impossible de l'annuler",
        )
    await set_order_status(order, OrderStatus.CANCELLED, db)
    return {"status": OrderStatus.CANCELLED.value}


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
