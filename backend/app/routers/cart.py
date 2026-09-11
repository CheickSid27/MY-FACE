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
from app.schemas.cart import (
    CartAddBulkRequest,
    CartAddRequest,
    CartItemRead,
    CartItemUpdateRequest,
    CartRead,
    PricingBreakdownRead,
)
from app.services.access import is_kiosk_request
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
    print_count = sum(1 for item in cart.items if item.print_requested)
    pricing = calculate_total(event.pricing, len(cart.items), print_count)

    items = [
        CartItemRead(
            id=item.id,
            photo=await to_photo_read(photos_by_id[item.photo_id], storage),
            print_requested=item.print_requested,
        )
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


async def _resolve_cart_session(session_id: uuid.UUID | None, event_id: uuid.UUID, db: AsyncSession) -> CartSession:
    """Retrouve le panier existant (s'il est encore valide) ou en cree un
    nouveau. Factorise entre l'ajout simple et l'ajout en masse : meme regle
    partout pour decider quand un nouveau panier doit demarrer."""
    cart: CartSession | None = None
    if session_id is not None:
        result = await db.execute(
            select(CartSession).where(CartSession.id == session_id).options(selectinload(CartSession.items))
        )
        cart = result.scalar_one_or_none()
        if cart is not None and cart.expires_at < datetime.now(timezone.utc):
            cart = None

    if cart is None:
        cart = CartSession(
            event_id=event_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.cart_session_ttl_hours),
        )
        db.add(cart)
        await db.flush()
    elif cart.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce panier appartient a un autre evenement",
        )

    return cart


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

    cart = await _resolve_cart_session(payload.session_id, payload.event_id, db)
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


@router.post("/add-bulk", response_model=CartRead, status_code=status.HTTP_201_CREATED)
async def add_to_cart_bulk(
    payload: CartAddBulkRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> CartRead:
    """Ajoute plusieurs photos au panier en UNE requete : utilise pour une
    selection rapide de plusieurs photos et pour "tout selectionner" sur un
    cluster de visages/des resultats de scan. Les photo_ids qui n'existent
    pas ou n'appartiennent pas a cet evenement sont ignores silencieusement
    plutot que de faire echouer tout le lot (ex: une photo supprimee entre
    l'affichage cote client et le clic)."""
    event = await db.get(Event, payload.event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evenement introuvable")

    valid_photo_ids = set(
        (
            await db.execute(
                select(Photo.id).where(Photo.id.in_(payload.photo_ids), Photo.event_id == payload.event_id)
            )
        )
        .scalars()
        .all()
    )
    if not valid_photo_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucune photo valide pour cet evenement")

    cart = await _resolve_cart_session(payload.session_id, payload.event_id, db)
    cart_id = cart.id

    already_in_cart = set(
        (
            await db.execute(
                select(CartItem.photo_id).where(
                    CartItem.cart_session_id == cart_id, CartItem.photo_id.in_(valid_photo_ids)
                )
            )
        )
        .scalars()
        .all()
    )

    for photo_id in valid_photo_ids - already_in_cart:
        db.add(CartItem(cart_session_id=cart_id, photo_id=photo_id))

    await db.commit()
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


@router.patch("/{item_id}", response_model=CartRead)
async def update_cart_item(
    item_id: uuid.UUID,
    payload: CartItemUpdateRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> CartRead:
    """Bascule le tirage papier pour UNE photo du panier (voir
    CartItem.print_requested) — utilise par la case a cocher "+ Imprimer" du
    panier, uniquement a la borne : cocher un tirage exige le kiosk_token de
    l'evenement (verifie serveur, pas seulement masque cote frontend).
    Decocher reste toujours possible."""
    item = await db.get(CartItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")

    cart_session_id = item.cart_session_id
    if payload.print_requested:
        cart_session = await db.get(CartSession, cart_session_id)
        event = await db.get(Event, cart_session.event_id) if cart_session is not None else None
        if event is None or not is_kiosk_request(event, payload.kiosk_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le tirage papier se commande uniquement a la borne de l'evenement",
            )
    item.print_requested = payload.print_requested
    await db.commit()
    # Meme piege que add_to_cart : sans expire, la relation `items` du panier
    # rechargee juste apres pourrait encore refleter l'ancienne valeur.
    db.expire_all()

    cart = await _get_cart_or_404(cart_session_id, db)
    return await _build_cart_read(cart, db, storage)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_cart_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    item = await db.get(CartItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    await db.delete(item)
    await db.commit()
