import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.photo import IndexingStatus


class PhotoRead(BaseModel):
    """Vue publique/galerie : jamais d'URL vers l'original (reserve au
    telechargement post-achat, voir routers/download.py)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    thumbnail_url: str
    preview_url: str
    original_filename: str
    indexing_status: IndexingStatus
    uploaded_at: datetime


class PhotoUploadError(BaseModel):
    filename: str
    error: str


class PhotoUploadResult(BaseModel):
    uploaded: list[PhotoRead]
    errors: list[PhotoUploadError]


class PhotoBulkDelete(BaseModel):
    """Suppression de plusieurs photos d'un evenement d'un coup (selection, ou
    toutes les photos d'une personne qui demande leur retrait)."""

    event_id: uuid.UUID
    photo_ids: list[uuid.UUID] = Field(min_length=1, max_length=2000)


class PhotoBulkDeleteResult(BaseModel):
    deleted: int
    # Photos deja vendues : gardees, pour ne pas casser le telechargement du
    # client qui les a payees (meme regle que la suppression d'une photo).
    kept_sold: list[str]


class PhotoListResponse(BaseModel):
    items: list[PhotoRead]
    total: int
    page: int
    page_size: int
