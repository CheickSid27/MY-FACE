import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ActivityLog(Base):
    """Journal des actions realisees sur MYFACE (volet Statistiques) :
    inscriptions, connexions, evenements, photos, selfies des invites,
    telechargements, packs... Les paiements des invites n'y sont pas : ils
    sont deja dans les Ventes.

    Le nom de l'acteur et de l'evenement sont copies au moment de l'action :
    la ligne reste lisible meme si le compte ou l'evenement est supprime."""

    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_label: Mapped[str] = mapped_column(String(160), nullable=False)
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Organisateur de l'evenement concerne (filtre « mes evenements » des photographes)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
