import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

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


class PhotoListResponse(BaseModel):
    items: list[PhotoRead]
    total: int
    page: int
    page_size: int
