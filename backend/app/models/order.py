import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.photo import Photo


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    # Le client a clique "J'ai paye" apres avoir scanne le QR marchand
    # (paiement mobile money hors-app, aucune API reelle branchee) ; en
    # attente de verification/confirmation manuelle par l'organisateur.
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SUCCESS = "success"
    FAILED = "failed"


class PaymentMethod(str, enum.Enum):
    WAVE = "wave"
    ORANGE_MONEY = "orange_money"
    MTN_MONEY = "mtn_money"
    MOOV_MONEY = "moov_money"
    # Adaptateur de secours SANS AUCUN mouvement d'argent reel, utilise
    # uniquement quand aucun operateur n'est configure (voir services/payments.py).
    # Jamais utilise silencieusement : le mode doit etre choisi explicitement
    # par PAYMENT_PROVIDER dans .env.
    MANUAL = "manual"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="XOF")
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=OrderStatus.PENDING,
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    payment_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    event: Mapped["Event"] = relationship("Event")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    photo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False
    )
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    photo: Mapped["Photo"] = relationship("Photo")
