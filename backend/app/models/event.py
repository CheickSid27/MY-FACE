import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.photo import Photo
    from app.models.user import User


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    kiosk_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    pricing: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Texte affiche dans le cadre decoratif (borne d'accueil + visionneuse
    # plein ecran), style photobooth : ex "LE FABULEUX MARIAGE D'ANTHONY &
    # SOPHIA". Nullable et distinct de `name` (le nom interne peut rester
    # simple) : si vide, aucun cadre n'est affiche pour cet evenement
    # (comportement opt-in, voir components/photo/FramedPhoto.tsx).
    frame_caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Paiement en especes autorise pour cet evenement : uniquement propose au
    # client sur la borne physique (jamais sur son propre telephone, voir
    # frontend/lib/kiosk.ts), le client remet l'argent a un membre de
    # l'equipe qui confirme ensuite manuellement (comme le flux QR).
    cash_enabled: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    organizer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    organizer: Mapped["User"] = relationship("User")
    # passive_deletes : la base supprime deja photos/embeddings en cascade
    # (ON DELETE CASCADE), inutile de tout charger en memoire pour supprimer
    # un evenement de plusieurs milliers de photos.
    photos: Mapped[list["Photo"]] = relationship(
        "Photo", back_populates="event", cascade="all, delete-orphan", passive_deletes=True
    )
