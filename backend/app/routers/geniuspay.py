"""Chemin de paiement GeniusPay, ISOLE du flux QR marchand + confirmation
manuelle (routers/payments.py). En test sandbox : rien ici ne modifie le
comportement existant, ces endpoints sont un ajout pur.

Reutilise la page de statut de paiement deja existante cote frontend
(/event/{event_id}/pay/{order_id}, qui poll GET /payments/status/{order_id})
comme success_url/error_url : cette page affiche deja le bon etat qu'il
s'agisse du flux QR ou d'ici, sans aucun changement frontend necessaire pour
ce premier test.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.deps import get_current_user
from app.models.cart import CartSession
from app.models.event import Event
from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.user import User
from app.routers.payments import _apply_webhook_result
from app.schemas.geniuspay import GeniusPayInitRequest, GeniusPayInitResponse
from app.services import geniuspay
from app.services.pricing import calculate_total

router = APIRouter(prefix="/payments/geniuspay", tags=["geniuspay"])

settings = get_settings()


@router.post("/init", response_model=GeniusPayInitResponse, status_code=status.HTTP_201_CREATED)
async def init_geniuspay_payment(
    payload: GeniusPayInitRequest,
    db: AsyncSession = Depends(get_db),
) -> GeniusPayInitResponse:
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
    print_count = sum(1 for item in cart.items if item.print_requested)
    breakdown = calculate_total(event.pricing, len(cart.items), print_count)
    print_unit_price = float(event.pricing.get("print_unit_price") or 0)

    order = Order(
        event_id=cart.event_id,
        contact_phone=payload.contact_phone,
        total_amount=breakdown.total,
        currency=breakdown.currency,
        status=OrderStatus.PENDING,
        payment_method=PaymentMethod.GENIUSPAY,
    )
    db.add(order)
    await db.flush()

    unit_price = float(event.pricing["unit_price"])
    for item in cart.items:
        db.add(
            OrderItem(
                order_id=order.id,
                photo_id=item.photo_id,
                unit_price=unit_price,
                print_requested=item.print_requested,
                print_price=print_unit_price if item.print_requested else None,
            )
        )

    return_url = f"{settings.app_base_url}/event/{cart.event_id}/pay/{order.id}"

    try:
        result = await geniuspay.init_payment(
            amount=breakdown.total,
            description=f"MYFACE, commande {order.id}",
            contact_phone=payload.contact_phone,
            order_id=str(order.id),
            success_url=return_url,
            error_url=return_url,
        )
    except geniuspay.GeniusPayError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    order.payment_reference = result.reference
    await db.commit()
    await db.refresh(order)

    return GeniusPayInitResponse(
        order_id=order.id,
        checkout_url=result.checkout_url,
        status=result.status,
        environment=result.environment,
    )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def geniuspay_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    raw_body = await request.body()
    signature = request.headers.get("X-Webhook-Signature")
    timestamp = request.headers.get("X-Webhook-Timestamp")
    event_type = request.headers.get("X-Webhook-Event")

    if not geniuspay.verify_webhook_signature(raw_body, signature, timestamp):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature webhook invalide")

    payload = geniuspay.parse_event(raw_body)
    event_type = event_type or payload.get("event")

    if event_type == "webhook.test":
        return {"status": "ok"}

    data = payload.get("data", {})
    reference = data.get("reference")
    if not reference:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload webhook invalide")

    if event_type == "payment.success":
        await _apply_webhook_result(reference, OrderStatus.SUCCESS, db)
    elif event_type in ("payment.failed", "payment.cancelled", "payment.expired"):
        await _apply_webhook_result(reference, OrderStatus.FAILED, db)
    # Autres evenements (payment.initiated, cashout.*...) : rien a faire cote MYFACE.

    return {"status": "ok"}


@router.get("/status/{order_id}")
async def geniuspay_debug_status(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Endpoint de test sandbox uniquement : renvoie l'etat brut de la
    commande pour verifier manuellement qu'un webhook a bien ete applique,
    sans dependre du polling frontend. Reserve a un utilisateur authentifie
    (pas de scoping par evenement : usage debug interne, pas une fonctionnalite
    produit) pour eviter qu'un order_id devine/observe expose le statut et le
    montant d'une commande a n'importe qui."""
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    return {
        "order_id": str(order.id),
        "status": order.status.value,
        "payment_reference": order.payment_reference,
        "total_amount": order.total_amount,
    }
