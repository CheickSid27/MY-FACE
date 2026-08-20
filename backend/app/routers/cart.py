import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.models.cart import CartItem, CartSession
from app.models.event import Event
from app.models.photo import Photo
from app.schemas.cart import CartAddRequest, CartItemRead, CartRead, PricingBreakdownRead
from app.services.photo_urls import to_photo_read
from app.services.pricing import calculate_total
from app.services.storage import StorageService, get_storage_service

router = APIRouter(prefix="/cart", tags=["cart"])

settings = get_settings()


async def _get_cart_or_404(session_id: uuid.UUID, db: AsyncSession) -> CartSession:
    result = await db.execute(
        select(CartSession).where(CartSession.id == session_id).options(selectinload(CartSession.items))
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Panier introuvable ou expire")
    if cart.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Panier expire")
    return cart


async def _build_cart_read(cart: CartSession, db: AsyncSession, storage: StorageService) -> CartRead:
    result = await db.execute(select(Photo).where(Photo.id.in_([item.photo_id for item in cart.items])))
    photos_by_id = {photo.id: photo for photo in result.scalars().all()}

    event = await db.get(Event, cart.event_id)
    pricing = calculate_total(event.pricing, len(cart.items))

    items = [
        CartItemRead(id=item.id, photo=await to_photo_read(photos_by_id[item.photo_id], storage))
        for item in cart.items
        if item.photo_id in photos_by_id
    ]

    return CartRead(
        session_id=cart.id,
        event_id=cart.event_id,
        items=items,
        pricing=PricingBreakdownRead(**pricing.__dict__),
        expires_at=cart.expires_at,
    )


@router.post("/add", response_model=CartRead, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    payload: CartAddRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> CartRead:
    event = await db.get(Event, payload.event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evenement introuvable")

    photo = await db.get(Photo, payload.photo_id)
    if photo is None or photo.event_id != payload.event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable pour cet evenement")

    cart: CartSession | None = None
    if payload.session_id is not None:
        result = await db.execute(
            select(CartSession)
            .where(CartSession.id == payload.session_id)
            .options(selectinload(CartSession.items))
        )
        cart = result.scalar_one_or_none()
        if cart is not None and cart.expires_at < datetime.now(timezone.utc):
            cart = None

    if cart is None:
        cart = CartSession(
            event_id=payload.event_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.cart_session_ttl_hours),
        )
        db.add(cart)
        await db.flush()
    elif cart.event_id != payload.event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce panier appartient a un autre evenement",
        )

    cart_id = cart.id

    existing = await db.execute(
        select(CartItem).where(CartItem.cart_session_id == cart_id, CartItem.photo_id == payload.photo_id)
    )
    if existing.scalar_one_or_none() is None:
        db.add(CartItem(cart_session_id=cart_id, photo_id=payload.photo_id))

    await db.commit()
    # `cart` (recupere en debut de fonction si session_id fourni) peut deja
    # avoir sa relation `items` chargee dans l'identity map de la session ;
    # sans expire, la requete suivante renverrait cette collection perimee
    # (sans le CartItem qu'on vient d'ajouter), meme apres selectinload.
    # On capture cart_id AVANT d'expirer : lire un attribut expire hors
    # contexte greenlet casse en SQLAlchemy async (MissingGreenlet).
    db.expire_all()

    cart = await _get_cart_or_404(cart_id, db)
    return await _build_cart_read(cart, db, storage)


@router.get("/{session_id}", response_model=CartRead)
async def get_cart(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> CartRead:
    cart = await _get_cart_or_404(session_id, db)
    return await _build_cart_read(cart, db, storage)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_cart_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    item = await db.get(CartItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    await db.delete(item)
    await db.commit()
