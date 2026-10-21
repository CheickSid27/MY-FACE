import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.user import User


class PackPurchaseStatus(str, enum.Enum):
    # Le photographe declare avoir paye (Mobile Money vers le numero MYFACE) :
    # un admin verifie la reception puis valide ou rejette.
    PENDING = "pending"
    PAID = "paid"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PackPurchase(Base):
    """Achat d'un pack pour un evenement (service photographe, voir
    services/packs.py). Paiement unique par evenement, pas d'abonnement.

    Aucune passerelle de paiement : le photographe envoie le montant au
    numero Mobile Money de MYFACE (voir routers/packs.py, payment-info) et
    saisit la reference de la transaction ; un admin confirme la reception.
    Un admin peut aussi attribuer un pack directement (offert, sur mesure) :
    la ligne est alors creee deja payee, moyen « admin »."""

    __tablename__ = "pack_purchases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pack: Mapped[str] = mapped_column(String(20), nullable=False)
    # Montant du (FCFA) : prix du pack moins ce qui a deja ete paye pour cet
    # evenement (passer d'Evenement a Pro ne coute que la difference).
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="XOF", server_default="XOF")
    status: Mapped[PackPurchaseStatus] = mapped_column(
        Enum(
            PackPurchaseStatus,
            name="pack_purchase_status",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=PackPurchaseStatus.PENDING,
        server_default=PackPurchaseStatus.PENDING.value,
        index=True,
    )
    # wave / orange / mtn / moov / djamo, ou « admin » (attribue par MYFACE)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    payer_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transaction_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    admin_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    event: Mapped["Event"] = relationship("Event")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
