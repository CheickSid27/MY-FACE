import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.photo import Photo


class CartSession(Base):
    """Panier invite, identifie par un token opaque stocke cote client
    (localStorage) — pas de compte invite, conforme au parcours sans
    inscription decrit au cahier des charges."""

    __tablename__ = "cart_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    event: Mapped["Event"] = relationship("Event")
    items: Mapped[list["CartItem"]] = relationship(
        "CartItem", back_populates="cart_session", cascade="all, delete-orphan"
    )


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_session_id", "photo_id", name="uq_cart_item_photo"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cart_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cart_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    photo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Tirage papier en plus de l'acces numerique, choisi par photo (pas
    # globalement sur tout le panier) : un client peut acheter 20 photos et
    # n'en imprimer que 3. Prix additionnel calcule via
    # Event.pricing["print_unit_price"], voir services/pricing.py.
    print_requested: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cart_session: Mapped["CartSession"] = relationship("CartSession", back_populates="items")
    photo: Mapped["Photo"] = relationship("Photo")
