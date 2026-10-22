"""Packs du service photographe : liste publique des packs, etat du pack d'un
evenement, achat (declare par le photographe, valide par un admin) et
reglages admin (numeros Mobile Money de MYFACE). Voir services/packs.py."""

import json
import logging
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.deps import get_current_user, require_admin, require_verified_user
from app.models.app_setting import AppSetting
from app.models.event import Event
from app.models.order import Order
from app.models.pack_purchase import PackPurchase, PackPurchaseStatus
from app.models.user import User, UserRole
from app.schemas.pack import (
    AdminSetPackRequest,
    EventPackRead,
    PackPaymentInfo,
    PackPaymentInfoUpdate,
    PackPurchaseAdminRead,
    PackPurchaseCreate,
    PackPurchaseRead,
    PackRead,
    PackRejectRequest,
    PackUpgradeOption,
    PaystackCheckout,
    PaystackPurchaseCreate,
)
from app.services.activity import log_activity
from app.services import paystack
from app.services.access import can_manage_event, get_manageable_event
from app.services.packs import (
    PACK_ORDER,
    PACKS,
    Pack,
    amount_due,
    amount_paid_for_event,
    count_event_photos,
    effective_photo_limit,
    get_owner,
    get_pack,
    is_unlimited_owner,
    pack_rank,
)
from app.services.push_notifications import send_push_to_user

logger = logging.getLogger("myface.packs")

router = APIRouter(tags=["packs"])

PAYMENT_SETTING_KEY = "pack_payment"


def _pack_read(pack: Pack) -> PackRead:
    return PackRead(
        key=pack.key,
        name=pack.name,
        price=pack.price,
        photo_limit=pack.photo_limit,
        tagline=pack.tagline,
        highlights=list(pack.highlights),
        features=sorted(pack.features),
        purchasable=pack.purchasable,
    )


async def _payment_info(db: AsyncSession) -> PackPaymentInfo:
    setting = await db.get(AppSetting, PAYMENT_SETTING_KEY)
    return PackPaymentInfo(**(setting.value if setting else {}))


async def _notify_admins(db: AsyncSession, title: str, body: str, url: str) -> None:
    result = await db.execute(select(User.id).where(User.role == UserRole.ADMIN, User.is_active.is_(True)))
    for admin_id in result.scalars().all():
        try:
            await send_push_to_user(admin_id, db, title=title, body=body, url=url)
        except Exception:
            logger.exception("Notification admin (pack) : echec")


# --------------------------------------------------------------------------
# Public / photographe
# --------------------------------------------------------------------------
@router.get("/packs", response_model=list[PackRead])
async def list_packs() -> list[PackRead]:
    """Les packs et leurs prix (page tarifs, inscription, choix du pack)."""
    return [_pack_read(PACKS[key]) for key in PACK_ORDER]


@router.get("/packs/payment-info", response_model=PackPaymentInfo)
async def get_pack_payment_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PackPaymentInfo:
    """Numeros Mobile Money de MYFACE ou envoyer le paiement d'un pack."""
    return await _payment_info(db)


@router.get("/events/{event_id}/pack", response_model=EventPackRead)
async def get_event_pack(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventPackRead:
    event = await get_manageable_event(event_id, current_user, db)
    return await _event_pack_read(event, db)


async def _event_pack_read(event: Event, db: AsyncSession) -> EventPackRead:
    owner = await get_owner(db, event)
    unlimited = is_unlimited_owner(owner)
    limit = effective_photo_limit(event, owner)
    photo_count = await count_event_photos(db, event.id)
    paid = await amount_paid_for_event(db, event.id)
    pack = get_pack(event.pack)

    purchases_result = await db.execute(
        select(PackPurchase).where(PackPurchase.event_id == event.id).order_by(PackPurchase.created_at.desc())
    )
    purchases = list(purchases_result.scalars().all())
    pending = next((p for p in purchases if p.status == PackPurchaseStatus.PENDING), None)

    upgrades: list[PackUpgradeOption] = []
    if not unlimited:
        for key in PACK_ORDER[pack_rank(event.pack) + 1:]:
            candidate = PACKS[key]
            if candidate.purchasable and candidate.price is not None:
                upgrades.append(
                    PackUpgradeOption(
                        key=candidate.key,
                        name=candidate.name,
                        price=candidate.price,
                        photo_limit=candidate.photo_limit,
                        amount_due=amount_due(candidate.key, paid),
                    )
                )

    return EventPackRead(
        event_id=event.id,
        pack=_pack_read(pack),
        unlimited=unlimited,
        photo_limit=limit,
        photo_count=photo_count,
        remaining=None if limit is None else max(0, limit - photo_count),
        amount_paid=paid,
        features=sorted(pack.features) if not unlimited else sorted(PACKS["sur_mesure"].features),
        upgrades=upgrades,
        pending_purchase=PackPurchaseRead.model_validate(pending) if pending else None,
        purchases=[PackPurchaseRead.model_validate(p) for p in purchases],
    )


@router.post(
    "/events/{event_id}/pack-purchases",
    response_model=PackPurchaseRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_pack_purchase(
    event_id: uuid.UUID,
    payload: PackPurchaseCreate,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> PackPurchase:
    """Le photographe declare avoir paye un pack (Mobile Money vers MYFACE) :
    l'achat reste « en attente » jusqu'a la verification par un admin, qui
    recoit une notification. Passer d'Evenement a Pro ne coute que la
    difference."""
    event, owner, target, due = await _check_new_purchase(event_id, payload.pack, current_user, db)

    purchase = PackPurchase(
        event_id=event_id,
        user_id=event.organizer_id,
        pack=target.key,
        amount=due,
        currency="XOF",
        status=PackPurchaseStatus.PENDING,
        payment_method=payload.payment_method,
        payer_phone=payload.payer_phone,
        transaction_ref=payload.transaction_ref,
    )
    db.add(purchase)
    await db.commit()
    await db.refresh(purchase)

    await log_activity(
        db, "pack_declare", actor=current_user, event=event,
        details={"pack": target.name, "montant": due, "moyen": payload.payment_method},
    )
    await db.refresh(purchase)
    who = (owner.public_name or owner.email) if owner else "Un photographe"
    montant = f"{due:,}".replace(",", " ")
    await _notify_admins(
        db,
        title=f"Pack {target.name} à vérifier",
        body=f"{who} : {montant} F par {payload.payment_method}, ref {payload.transaction_ref}",
        url="/admin/packs",
    )
    return purchase


async def _check_new_purchase(event_id: uuid.UUID, pack_key: str, current_user: User, db: AsyncSession):
    """Controles communs a la declaration manuelle et au paiement Paystack.
    Un paiement Paystack jamais termine (page fermee) ne bloque pas : il est
    annule au profit du nouvel essai. Renvoie (evenement, proprietaire,
    pack vise, montant du)."""
    event = await get_manageable_event(event_id, current_user, db)
    owner = await get_owner(db, event)
    if is_unlimited_owner(owner):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Les événements MYFACE n'ont pas de pack à acheter",
        )

    target = PACKS[pack_key]
    if not target.purchasable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce pack ne s'achète pas en ligne : contactez MYFACE sur WhatsApp",
        )
    if pack_rank(target.key) <= pack_rank(event.pack):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"L'événement a déjà le pack {get_pack(event.pack).name} ou supérieur",
        )

    pending_result = await db.execute(
        select(PackPurchase).where(
            PackPurchase.event_id == event_id, PackPurchase.status == PackPurchaseStatus.PENDING
        )
    )
    for pending in pending_result.scalars().all():
        if pending.payment_method != PAYSTACK_METHOD:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un paiement est déjà en cours de vérification pour cet événement",
            )
        pending.status = PackPurchaseStatus.CANCELLED
        pending.decided_at = datetime.now(timezone.utc)

    paid = await amount_paid_for_event(db, event_id)
    due = amount_due(target.key, paid)
    if due <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Rien à payer pour ce pack")
    return event, owner, target, due


# --------------------------------------------------------------------------
# Paiement en ligne par Paystack (Wave, Orange Money, MTN, carte)
# --------------------------------------------------------------------------
PAYSTACK_METHOD = "paystack"


@router.post(
    "/events/{event_id}/pack-purchases/paystack",
    response_model=PaystackCheckout,
    status_code=status.HTTP_201_CREATED,
)
async def start_paystack_purchase(
    event_id: uuid.UUID,
    payload: PaystackPurchaseCreate,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> PaystackCheckout:
    """Ouvre un paiement Paystack pour un pack : renvoie le lien de la page
    de paiement. Le pack s'active seul quand Paystack confirme le paiement
    (webhook ou retour sur l'application), sans validation par un admin."""
    if not paystack.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le paiement en ligne n'est pas disponible : utilisez la déclaration de paiement",
        )
    event, owner, target, due = await _check_new_purchase(event_id, payload.pack, current_user, db)

    purchase = PackPurchase(
        event_id=event_id,
        user_id=event.organizer_id,
        pack=target.key,
        amount=due,
        currency="XOF",
        status=PackPurchaseStatus.PENDING,
        payment_method=PAYSTACK_METHOD,
        transaction_ref=f"myface-{uuid.uuid4().hex}",
    )
    db.add(purchase)
    await db.flush()

    settings = get_settings()
    callback_url = f"{settings.app_base_url}/admin/events/{event_id}?paystack={purchase.id}"
    try:
        url = await paystack.initialize_transaction(
            email=(owner.email if owner else current_user.email),
            amount=due,
            reference=purchase.transaction_ref,
            callback_url=callback_url,
            metadata={"pack_purchase_id": str(purchase.id), "event_id": str(event_id), "pack": target.key},
        )
    except (paystack.PaystackError, httpx.HTTPError) as exc:
        await db.rollback()
        logger.warning("Paystack initialize a echoue : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Paystack ne répond pas pour le moment, réessayez dans un instant",
        ) from exc
    await db.commit()
    return PaystackCheckout(purchase_id=purchase.id, authorization_url=url)


async def _settle_paystack_purchase(purchase: PackPurchase, db: AsyncSession) -> None:
    """Redemande l'etat a Paystack et active le pack si le paiement est
    reussi, au bon montant et en francs CFA. Sans effet si deja traite."""
    if purchase.status != PackPurchaseStatus.PENDING or purchase.payment_method != PAYSTACK_METHOD:
        return
    tx = await paystack.verify_transaction(purchase.transaction_ref)
    if tx.status == "success" and tx.currency == "XOF" and tx.amount >= purchase.amount:
        await _activate_purchase(purchase, db, decided_by=None)
        await log_activity(
            db, "pack_paye", actor_id=purchase.user_id, actor_label="Paiement Paystack",
            event=await db.get(Event, purchase.event_id),
            details={"pack": get_pack(purchase.pack).name, "montant": purchase.amount},
        )
        await db.refresh(purchase)
        montant = f"{purchase.amount:,}".replace(",", " ")
        await _notify_admins(
            db,
            title=f"Pack {get_pack(purchase.pack).name} payé : {montant} F",
            body="Paiement en ligne Paystack, pack déjà activé.",
            url="/admin/packs",
        )
    elif tx.status in ("failed", "reversed"):
        purchase.status = PackPurchaseStatus.REJECTED
        purchase.decided_at = datetime.now(timezone.utc)
        purchase.admin_note = "Paiement Paystack refusé"
        await db.commit()
        await db.refresh(purchase)


@router.post("/pack-purchases/{purchase_id}/paystack/verify", response_model=PackPurchaseRead)
async def verify_paystack_purchase(
    purchase_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PackPurchase:
    """Appele au retour de la page Paystack : renvoie l'etat a jour."""
    purchase = await db.get(PackPurchase, purchase_id)
    if purchase is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achat introuvable")
    event = await db.get(Event, purchase.event_id)
    if event is None or not can_manage_event(event, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
    try:
        await _settle_paystack_purchase(purchase, db)
    except (paystack.PaystackError, httpx.HTTPError) as exc:
        logger.warning("Paystack verify a echoue pour %s : %s", purchase.id, exc)
    return purchase


@router.post("/payments/paystack/webhook", include_in_schema=False)
async def paystack_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Notification de Paystack, signee avec la cle secrete, pour un pack ou
    une commande de photos. On ne croit pas le contenu sur parole : l'etat
    est redemande a Paystack avant d'activer quoi que ce soit."""
    raw = await request.body()
    if not paystack.signature_is_valid(raw, request.headers.get("x-paystack-signature")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature invalide")
    try:
        body = json.loads(raw)
    except ValueError:
        return {"ok": True}
    if body.get("event") != "charge.success":
        return {"ok": True}
    reference = (body.get("data") or {}).get("reference")
    if not reference:
        return {"ok": True}
    result = await db.execute(select(PackPurchase).where(PackPurchase.transaction_ref == reference))
    purchase = result.scalar_one_or_none()
    try:
        if purchase is not None:
            await _settle_paystack_purchase(purchase, db)
        else:
            # Commande de photos d'un invite (evenements de MYFACE)
            order_result = await db.execute(select(Order).where(Order.payment_reference == reference))
            order = order_result.scalar_one_or_none()
            if order is not None:
                await paystack.settle_order(order, db)
    except (paystack.PaystackError, httpx.HTTPError) as exc:
        # Paystack renvoie le webhook en cas d'erreur : on le laisse reessayer.
        logger.warning("Paystack verify (webhook) a echoue pour %s : %s", reference, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Verification impossible") from exc
    return {"ok": True}


@router.post("/pack-purchases/{purchase_id}/cancel", response_model=PackPurchaseRead)
async def cancel_pack_purchase(
    purchase_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PackPurchase:
    """Le photographe annule une declaration de paiement (erreur de saisie)."""
    purchase = await db.get(PackPurchase, purchase_id)
    if purchase is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achat introuvable")
    event = await db.get(Event, purchase.event_id)
    if event is None or not can_manage_event(event, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
    if purchase.status != PackPurchaseStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet achat n'est plus en attente")
    purchase.status = PackPurchaseStatus.CANCELLED
    purchase.decided_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(purchase)
    return purchase


# --------------------------------------------------------------------------
# Admin MYFACE
# --------------------------------------------------------------------------
@router.get("/admin/pack-purchases", response_model=list[PackPurchaseAdminRead])
async def list_pack_purchases(
    purchase_status: PackPurchaseStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[PackPurchaseAdminRead]:
    query = (
        select(PackPurchase, Event, User)
        .join(Event, Event.id == PackPurchase.event_id)
        .join(User, User.id == PackPurchase.user_id)
        .order_by(PackPurchase.created_at.desc())
        .limit(300)
    )
    if purchase_status is not None:
        query = query.where(PackPurchase.status == purchase_status)
    rows = (await db.execute(query)).all()
    return [
        PackPurchaseAdminRead(
            **PackPurchaseRead.model_validate(purchase).model_dump(),
            event_name=event.name,
            event_date=event.date,
            current_pack=event.pack,
            photographer_email=user.email,
            photographer_name=user.public_name,
            photographer_phone=user.phone,
        )
        for purchase, event, user in rows
    ]


async def _get_purchase_for_decision(purchase_id: uuid.UUID, db: AsyncSession) -> PackPurchase:
    purchase = await db.get(PackPurchase, purchase_id)
    if purchase is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achat introuvable")
    if purchase.status != PackPurchaseStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Achat déjà traité (statut : {purchase.status.value})",
        )
    return purchase


@router.post("/admin/pack-purchases/{purchase_id}/approve", response_model=PackPurchaseRead)
async def approve_pack_purchase(
    purchase_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PackPurchase:
    """Paiement recu : le pack est active tout de suite sur l'evenement."""
    purchase = await _get_purchase_for_decision(purchase_id, db)
    await _activate_purchase(purchase, db, decided_by=current_user.id)
    await log_activity(
        db, "pack_valide", actor=current_user, event=await db.get(Event, purchase.event_id),
        details={"pack": get_pack(purchase.pack).name, "montant": purchase.amount},
    )
    await db.refresh(purchase)
    return purchase


async def _activate_purchase(purchase: PackPurchase, db: AsyncSession, decided_by: uuid.UUID | None) -> None:
    """Passe l'achat a « paye », active le pack sur l'evenement et previent
    le photographe. Commun a la validation admin et au paiement Paystack."""
    event = await db.get(Event, purchase.event_id)
    purchase.status = PackPurchaseStatus.PAID
    purchase.decided_at = datetime.now(timezone.utc)
    purchase.decided_by = decided_by
    if event is not None and pack_rank(purchase.pack) > pack_rank(event.pack):
        event.pack = purchase.pack
    await db.commit()
    await db.refresh(purchase)

    if event is not None:
        await send_push_to_user(
            purchase.user_id,
            db,
            title=f"Pack {get_pack(purchase.pack).name} activé",
            body=f"{event.name} : vous pouvez ajouter vos photos.",
            url=f"/admin/events/{event.id}",
        )


@router.post("/admin/pack-purchases/{purchase_id}/reject", response_model=PackPurchaseRead)
async def reject_pack_purchase(
    purchase_id: uuid.UUID,
    payload: PackRejectRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PackPurchase:
    """Paiement introuvable : l'achat est refuse, le pack ne change pas."""
    purchase = await _get_purchase_for_decision(purchase_id, db)
    purchase.status = PackPurchaseStatus.REJECTED
    purchase.decided_at = datetime.now(timezone.utc)
    purchase.decided_by = current_user.id
    purchase.admin_note = (payload.note or "").strip() or None
    await db.commit()
    await log_activity(
        db, "pack_refuse", actor=current_user, event=await db.get(Event, purchase.event_id),
        details={"pack": get_pack(purchase.pack).name, "note": purchase.admin_note},
    )
    await db.refresh(purchase)
    return purchase


@router.put("/admin/events/{event_id}/pack", response_model=EventPackRead)
async def admin_set_event_pack(
    event_id: uuid.UUID,
    payload: AdminSetPackRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> EventPackRead:
    """Attribue un pack sans paiement en ligne (pack offert, sur mesure
    negocie, geste commercial). Garde une trace dans l'historique des achats."""
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    event.pack = payload.pack
    event.photo_limit_override = payload.photo_limit_override
    db.add(
        PackPurchase(
            event_id=event.id,
            user_id=event.organizer_id,
            pack=payload.pack,
            amount=0,
            currency="XOF",
            status=PackPurchaseStatus.PAID,
            payment_method="admin",
            admin_note=(payload.note or "").strip() or "Attribue par MYFACE",
            decided_at=datetime.now(timezone.utc),
            decided_by=current_user.id,
        )
    )
    await db.commit()
    await db.refresh(event)
    return await _event_pack_read(event, db)


@router.get("/admin/settings/pack-payment", response_model=PackPaymentInfo)
async def admin_get_pack_payment(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PackPaymentInfo:
    return await _payment_info(db)


@router.put("/admin/settings/pack-payment", response_model=PackPaymentInfo)
async def admin_set_pack_payment(
    payload: PackPaymentInfoUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PackPaymentInfo:
    cleaned = {key: (value.strip() or None) if isinstance(value, str) else value for key, value in payload.model_dump().items()}
    setting = await db.get(AppSetting, PAYMENT_SETTING_KEY)
    if setting is None:
        db.add(AppSetting(key=PAYMENT_SETTING_KEY, value=cleaned))
    else:
        setting.value = cleaned
    await db.commit()
    return PackPaymentInfo(**cleaned)
