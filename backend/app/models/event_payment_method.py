import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.order import PaymentMethod

if TYPE_CHECKING:
    from app.models.event import Event


class EventPaymentMethod(Base):
    """Moyen de paiement mobile money configure par l'organisateur pour un
    evenement : QR code marchand + numero a afficher au client au moment de
    payer. Aucune integration API reelle (voir services/payments.py) : le
    client paie hors-app en scannant ce QR, puis declare avoir paye ; c'est
    l'organisateur qui confirme manuellement apres verification sur son
    compte Wave/Orange/MTN/Moov (voir routers/admin.py, confirm_order)."""

    __tablename__ = "event_payment_methods"
    __table_args__ = (UniqueConstraint("event_id", "method", name="uq_event_payment_method"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    qr_image_key: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    event: Mapped["Event"] = relationship("Event")
