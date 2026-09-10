import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.photo import Photo

EMBEDDING_DIM = 512


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vector: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # Nettete du visage (variance du Laplacien sur le crop, voir
    # face_recognition.py) : le score de confiance de detection (confidence)
    # ne dit rien sur le flou (un visage flou en mode portrait/bokeh peut
    # avoir un det_score eleve) — utilise pour rejeter les visages trop flous
    # avant meme de creer leur embedding (peu fiable pour le matching et
    # perturbe le clustering). Nullable : NULL pour les lignes creees avant
    # cette colonne.
    sharpness: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    photo: Mapped["Photo"] = relationship("Photo", back_populates="face_embeddings")
