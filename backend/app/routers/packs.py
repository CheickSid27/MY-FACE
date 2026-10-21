"""Packs du service photographe : liste publique des packs, etat du pack d'un
evenement, achat (declare par le photographe, valide par un admin) et
reglages admin (numeros Mobile Money de MYFACE). Voir services/packs.py."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user, require_admin
from app.models.app_setting import AppSetting
from app.models.event import Event
from app.models.pack_purchase import PackPurchase, PackPurchaseStatus
from app.models.user import User, UserRole
from app.schemas.pack import (
    AdminSetPackRequest,
    EventPackRead,
    PackPaymentInfo,
    PackPurchaseAdminRead,
    PackPurchaseCreate,
    PackPurchaseRead,
    PackRead,
    PackRejectRequest,
    PackUpgradeOption,
)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PackPurchase:
    """Le photographe declare avoir paye un pack (Mobile Money vers MYFACE) :
    l'achat reste « en attente » jusqu'a la verification par un admin, qui
    recoit une notification. Passer d'Evenement a Pro ne coute que la
    difference."""
    event = await get_manageable_event(event_id, current_user, db)
    owner = await get_owner(db, event)
    if is_unlimited_owner(owner):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Les evenements MYFACE n'ont pas de pack a acheter",
        )

    target = PACKS[payload.pack]
    if not target.purchasable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce pack ne s'achete pas en ligne : contactez MYFACE sur WhatsApp",
        )
    if pack_rank(target.key) <= pack_rank(event.pack):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"L'evenement a deja le pack {get_pack(event.pack).name} ou superieur",
        )

    existing = await db.execute(
        select(PackPurchase.id).where(
            PackPurchase.event_id == event_id, PackPurchase.status == PackPurchaseStatus.PENDING
        )
    )
    if existing.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un paiement est deja en cours de verification pour cet evenement",
        )

    paid = await amount_paid_for_event(db, event_id)
    due = amount_due(target.key, paid)
    if due <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Rien a payer pour ce pack")

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

    who = (owner.public_name or owner.email) if owner else "Un photographe"
    montant = f"{due:,}".replace(",", " ")
    await _notify_admins(
        db,
        title=f"Pack {target.name} a verifier",
        body=f"{who} : {montant} F par {payload.payment_method}, ref {payload.transaction_ref}",
        url="/admin/packs",
    )
    return purchase


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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse")
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
            detail=f"Achat deja traite (statut : {purchase.status.value})",
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
    event = await db.get(Event, purchase.event_id)
    purchase.status = PackPurchaseStatus.PAID
    purchase.decided_at = datetime.now(timezone.utc)
    purchase.decided_by = current_user.id
    if event is not None and pack_rank(purchase.pack) > pack_rank(event.pack):
        event.pack = purchase.pack
    await db.commit()
    await db.refresh(purchase)

    if event is not None:
        await send_push_to_user(
            purchase.user_id,
            db,
            title=f"Pack {get_pack(purchase.pack).name} active",
            body=f"{event.name} : vous pouvez ajouter vos photos.",
            url=f"/admin/events/{event.id}",
        )
    return purchase


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evenement introuvable")
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
    payload: PackPaymentInfo,
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
