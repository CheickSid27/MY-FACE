import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.models.cart import CartSession
from app.models.event import Event
from app.models.event_payment_method import EventPaymentMethod
from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.schemas.payment import (
    PaymentInitRequest,
    PaymentInitResponse,
    PaymentStatusResponse,
)
from app.services.access import is_kiosk_request
from app.services.orders import expire_order_if_stale, set_order_status
from app.services.payments import PaymentProvider, get_payment_provider
from app.services.pricing import calculate_total
from app.services.push_notifications import send_push_to_user
from app.services.storage import StorageService, get_storage_service

router = APIRouter(prefix="/payments", tags=["payments"])

settings = get_settings()

# Moyens qui ne passent pas par /payments/init : "manual" n'est plus qu'un
# verificateur de signature webhook (voir services/payments.py), GeniusPay a
# son propre parcours isole (routers/geniuspay.py).
_NOT_INITIABLE_HERE = {
    PaymentMethod.MANUAL: "Choisissez un moyen de paiement propose par l'organisateur",
    PaymentMethod.GENIUSPAY: "GeniusPay se lance via /payments/geniuspay/init",
}


def _create_order_from_cart(
    cart: CartSession,
    event: Event,
    payload: PaymentInitRequest,
    order_status: OrderStatus,
    payment_reference: str,
) -> Order:
    """Commande + snapshot des photos du panier (prix unitaire et tirage
    papier au moment de l'achat : un changement de tarif ulterieur ne modifie
    jamais une commande deja passee). Ajoutee a la session, non commitee."""
    print_count = sum(1 for item in cart.items if item.print_requested)
    breakdown = calculate_total(event.pricing, len(cart.items), print_count)
    unit_price = float(event.pricing["unit_price"])
    print_unit_price = float(event.pricing.get("print_unit_price") or 0)

    order = Order(
        event_id=cart.event_id,
        contact_phone=payload.contact_phone,
        total_amount=breakdown.total,
        currency=breakdown.currency,
        status=order_status,
        payment_method=payload.payment_method,
        payment_reference=payment_reference,
    )
    order.items = [
        OrderItem(
            photo_id=item.photo_id,
            unit_price=unit_price,
            print_requested=item.print_requested,
            print_price=print_unit_price if item.print_requested else None,
        )
        for item in cart.items
    ]
    return order


@router.post("/init", response_model=PaymentInitResponse, status_code=status.HTTP_201_CREATED)
async def init_payment(
    payload: PaymentInitRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> PaymentInitResponse:
    if payload.payment_method in _NOT_INITIABLE_HERE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=_NOT_INITIABLE_HERE[payload.payment_method]
        )

    result = await db.execute(
        select(CartSession)
        .where(CartSession.id == payload.session_id)
        .options(selectinload(CartSession.items))
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Panier introuvable")
    if cart.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Panier expire")
    if not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Panier vide")

    event = await db.get(Event, cart.event_id)

    if payload.payment_method == PaymentMethod.CASH:
        # Especes remises en main propre au staff a cote de la borne : pas de
        # QR/numero a configurer, et pas d'etape "j'ai paye" cote client
        # (c'est le staff qui sait en temps reel que l'argent a ete recu) —
        # la commande part directement en attente de confirmation, comme
        # apres un mark-paid QR classique.
        if not event.cash_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le paiement en especes n'est pas active pour cet evenement",
            )
        # Verifie serveur (et pas seulement masque cote frontend) : une
        # commande "especes" creee depuis un telephone attendrait un paiement
        # que personne ne peut recevoir, et declencherait une notification.
        if not is_kiosk_request(event, payload.kiosk_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le paiement en especes est disponible uniquement a la borne de l'evenement",
            )

        order = _create_order_from_cart(
            cart, event, payload, OrderStatus.AWAITING_CONFIRMATION, f"CASH-{secrets.token_hex(8)}"
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        await send_push_to_user(
            event.organizer_id,
            db,
            title="Nouvelle commande a confirmer (especes)",
            body=f"{order.total_amount:.0f} {order.currency} — {order.contact_phone}",
            url=f"{settings.app_base_url}/admin/events/{event.id}/payments",
        )

        return PaymentInitResponse(
            order_id=order.id,
            status=order.status,
            payment_method=order.payment_method,
            total_amount=order.total_amount,
            currency=order.currency,
            instructions=(
                "Rendez-vous au comptoir avec le montant en especes. "
                "Un membre de l'equipe va valider votre commande."
            ),
        )

    # Flux QR + confirmation manuelle organisateur (aucune API operateur
    # reelle branchee, voir services/payments.py) : le moyen choisi doit
    # avoir ete configure par l'organisateur pour cet evenement.
    pm_result = await db.execute(
        select(EventPaymentMethod).where(
            EventPaymentMethod.event_id == cart.event_id,
            EventPaymentMethod.method == payload.payment_method,
        )
    )
    event_payment_method = pm_result.scalar_one_or_none()
    if event_payment_method is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce moyen de paiement n'est pas configure pour cet evenement",
        )

    order = _create_order_from_cart(cart, event, payload, OrderStatus.PENDING, f"QR-{secrets.token_hex(8)}")
    db.add(order)
    await db.commit()
    await db.refresh(order)

    return PaymentInitResponse(
        order_id=order.id,
        status=order.status,
        payment_method=order.payment_method,
        total_amount=order.total_amount,
        currency=order.currency,
        instructions=(
            "Scannez ce QR code dans votre application, payez le montant indique, "
            "puis cliquez sur \"J'ai paye\"."
        ),
        qr_image_url=await storage.get_presigned_url(event_payment_method.qr_image_key, expires_in=3600),
        merchant_phone=event_payment_method.phone_number,
    )


async def _build_status_response(
    order: Order, db: AsyncSession, storage: StorageService
) -> PaymentStatusResponse:
    qr_image_url: str | None = None
    merchant_phone: str | None = None
    pm_result = await db.execute(
        select(EventPaymentMethod).where(
            EventPaymentMethod.event_id == order.event_id, EventPaymentMethod.method == order.payment_method
        )
    )
    event_payment_method = pm_result.scalar_one_or_none()
    if event_payment_method is not None:
        qr_image_url = await storage.get_presigned_url(event_payment_method.qr_image_key, expires_in=3600)
        merchant_phone = event_payment_method.phone_number

    return PaymentStatusResponse(
        order_id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        currency=order.currency,
        payment_method=order.payment_method,
        qr_image_url=qr_image_url,
        merchant_phone=merchant_phone,
    )


@router.post("/{order_id}/mark-paid", response_model=PaymentStatusResponse)
async def mark_paid(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> PaymentStatusResponse:
    """Declare cote client "j'ai paye" apres avoir scanne le QR marchand et
    paye hors-app. Ne confirme PAS la commande : passe juste en attente de
    verification par l'organisateur (voir routers/admin.py, confirm_order)."""
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    if await expire_order_if_stale(order, db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cette commande a expire. Si vous avez deja paye, presentez-vous a "
                "l'organisateur avec votre numero de telephone : il peut la valider."
            ),
        )
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Commande au statut '{order.status.value}', impossible de la marquer payee",
        )

    order.status = OrderStatus.AWAITING_CONFIRMATION
    await db.commit()
    await db.refresh(order)

    event = await db.get(Event, order.event_id)
    if event is not None:
        await send_push_to_user(
            event.organizer_id,
            db,
            title="Nouvelle commande a confirmer",
            body=f"{order.total_amount:.0f} {order.currency} — {order.contact_phone}",
            url=f"{settings.app_base_url}/admin/events/{event.id}/payments",
        )

    return await _build_status_response(order, db, storage)


@router.get("/status/{order_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> PaymentStatusResponse:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    await expire_order_if_stale(order, db)
    return await _build_status_response(order, db, storage)


async def _apply_webhook_result(reference: str, new_status: OrderStatus, db: AsyncSession) -> None:
    result = await db.execute(select(Order).where(Order.payment_reference == reference))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable pour cette reference")
    await set_order_status(order, new_status, db)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    provider: PaymentProvider = Depends(get_payment_provider),
) -> dict[str, str]:
    raw_body = await request.body()
    signature = request.headers.get("X-Signature")

    if not provider.verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature webhook invalide")

    payload = await request.json()
    reference = payload.get("reference")
    status_value = payload.get("status")
    if not reference or status_value not in (OrderStatus.SUCCESS.value, OrderStatus.FAILED.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload webhook invalide")

    await _apply_webhook_result(reference, OrderStatus(status_value), db)
    return {"status": "ok"}
