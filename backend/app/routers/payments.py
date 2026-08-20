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
    PaymentSimulateRequest,
    PaymentStatusResponse,
)
from app.services.payments import PaymentProvider, get_payment_provider
from app.services.pricing import calculate_total
from app.services.sms import get_sms_service
from app.services.storage import StorageService, get_storage_service

router = APIRouter(prefix="/payments", tags=["payments"])

settings = get_settings()


@router.post("/init", response_model=PaymentInitResponse, status_code=status.HTTP_201_CREATED)
async def init_payment(
    payload: PaymentInitRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> PaymentInitResponse:
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
    breakdown = calculate_total(event.pricing, len(cart.items))

    if payload.payment_method is not None:
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

        order = Order(
            event_id=cart.event_id,
            contact_phone=payload.contact_phone,
            total_amount=breakdown.total,
            currency=breakdown.currency,
            status=OrderStatus.PENDING,
            payment_method=payload.payment_method,
            payment_reference=f"QR-{secrets.token_hex(8)}",
        )
        db.add(order)
        await db.flush()

        unit_price = float(event.pricing["unit_price"])
        for item in cart.items:
            db.add(OrderItem(order_id=order.id, photo_id=item.photo_id, unit_price=unit_price))

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

    # Ancien comportement (provider global PAYMENT_PROVIDER) : utilise par le
    # mode test "manual" tant qu'aucun moyen de paiement n'est configure par
    # evenement.
    provider = get_payment_provider()

    order = Order(
        event_id=cart.event_id,
        contact_phone=payload.contact_phone,
        total_amount=breakdown.total,
        currency=breakdown.currency,
        status=OrderStatus.PENDING,
        payment_method=PaymentMethod(settings.payment_provider),
    )
    db.add(order)
    await db.flush()

    unit_price = float(event.pricing["unit_price"])
    for item in cart.items:
        db.add(OrderItem(order_id=order.id, photo_id=item.photo_id, unit_price=unit_price))

    try:
        init_result = await provider.init_payment(order)
    except NotImplementedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    order.payment_reference = init_result.reference
    order.status = OrderStatus.PROCESSING
    await db.commit()
    await db.refresh(order)

    return PaymentInitResponse(
        order_id=order.id,
        status=order.status,
        payment_method=order.payment_method,
        total_amount=order.total_amount,
        currency=order.currency,
        redirect_url=init_result.redirect_url,
        instructions=init_result.instructions,
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
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Commande au statut '{order.status.value}', impossible de la marquer payee",
        )

    order.status = OrderStatus.AWAITING_CONFIRMATION
    await db.commit()
    await db.refresh(order)

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
    return await _build_status_response(order, db, storage)


async def _apply_webhook_result(reference: str, new_status: OrderStatus, db: AsyncSession) -> None:
    result = await db.execute(select(Order).where(Order.payment_reference == reference))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable pour cette reference")

    order.status = new_status
    await db.commit()

    if new_status == OrderStatus.SUCCESS:
        sms = get_sms_service()
        download_url = f"{settings.app_base_url}/order/{order.id}/download"
        await sms.send_sms(
            order.contact_phone,
            f"MYFACE: votre paiement est confirme. Telechargez vos photos ici : {download_url}",
        )


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


@router.post("/{order_id}/simulate", status_code=status.HTTP_200_OK)
async def simulate_payment(
    order_id: uuid.UUID,
    payload: PaymentSimulateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Confirme/echoue une commande SANS passer par un vrai operateur.

    Reserve au mode PAYMENT_PROVIDER=manual (dev/test) : refuse (403) des que
    l'app est configuree avec un vrai operateur, pour qu'il soit impossible
    d'utiliser ce raccourci comme substitut a un vrai paiement en production.
    """
    if settings.payment_provider != "manual":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation disponible uniquement en PAYMENT_PROVIDER=manual",
        )
    if payload.status not in (OrderStatus.SUCCESS, OrderStatus.FAILED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status doit etre success ou failed")

    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")

    await _apply_webhook_result(order.payment_reference, payload.status, db)
    return {"status": "ok"}
