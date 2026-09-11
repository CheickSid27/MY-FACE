import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.face_embedding import FaceEmbedding


class IndexingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Cles de stockage uniquement : le bucket est prive, les URLs de lecture
    # sont toujours generees a la demande (presignees, expiration courte) via
    # `app.services.photo_urls`, jamais stockees en base (voir storage.py).
    original_key: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_key: Mapped[str] = mapped_column(String(512), nullable=False)
    # Version intermediaire (grand format, bonne qualite mais pas l'original)
    # pour l'apercu plein ecran/zoom avant achat : la miniature de grille
    # (400px) suffit pour parcourir vite, mais parait floue une fois
    # agrandie. Nullable : les photos deja en base avant l'ajout de ce champ
    # retombent sur la miniature (voir services/photo_urls.py).
    preview_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Meme apercu que preview_key, mais avec un filigrane incruste : c'est
    # la seule version grand format servie au telephone d'un invite (l'apercu
    # net n'est servi qu'a la borne et a l'organisateur, voir
    # services/photo_urls.py). Nullable : genere a l'ingestion pour les
    # nouvelles photos, rattrape en tache de fond pour les anciennes (voir
    # services/watermark.py, backfill_watermarks).
    preview_watermarked_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    indexing_status: Mapped[IndexingStatus] = mapped_column(
        Enum(
            IndexingStatus,
            name="indexing_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=IndexingStatus.PENDING,
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    event: Mapped["Event"] = relationship("Event", back_populates="photos")
    face_embeddings: Mapped[list["FaceEmbedding"]] = relationship(
        "FaceEmbedding", back_populates="photo", cascade="all, delete-orphan", passive_deletes=True
    )
