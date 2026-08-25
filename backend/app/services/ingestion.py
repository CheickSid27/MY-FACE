"""Logique d'ingestion d'une photo (validation, generation thumbnail/preview,
upload storage, creation de la ligne Photo), partagee entre l'upload manuel
(routers/photos.py) et le dossier surveille (services/folder_watcher.py)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo import IndexingStatus, Photo
from app.services.storage import StorageService
from app.services.thumbnails import InvalidImageError, generate_preview, generate_thumbnail

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024


async def ingest_photo(
    event_id: uuid.UUID,
    filename: str,
    content_type: str,
    data: bytes,
    db: AsyncSession,
    storage: StorageService,
) -> Photo:
    """Valide et importe une photo, l'ajoute a la session `db` (non commit).

    Leve ValueError / InvalidImageError si le fichier est invalide — a
    l'appelant de decider comment reporter l'erreur (reponse HTTP, log, ...)."""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Type de fichier non supporte: {content_type}")
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise ValueError("Fichier trop volumineux (max 25 Mo)")
    if not data:
        raise ValueError("Fichier vide")

    thumbnail_bytes = generate_thumbnail(data)
    preview_bytes = generate_preview(data)

    photo_id = uuid.uuid4()
    extension = (filename or "photo.jpg").rsplit(".", 1)[-1].lower()
    original_key = f"events/{event_id}/originals/{photo_id}.{extension}"
    thumbnail_key = f"events/{event_id}/thumbnails/{photo_id}.jpg"
    preview_key = f"events/{event_id}/previews/{photo_id}.jpg"

    await storage.upload(original_key, data, content_type)
    await storage.upload(thumbnail_key, thumbnail_bytes, "image/jpeg")
    await storage.upload(preview_key, preview_bytes, "image/jpeg")

    photo = Photo(
        id=photo_id,
        event_id=event_id,
        original_key=original_key,
        thumbnail_key=thumbnail_key,
        preview_key=preview_key,
        original_filename=filename or f"{photo_id}.{extension}",
        indexing_status=IndexingStatus.PENDING,
    )
    db.add(photo)
    return photo


__all__ = ["ingest_photo", "InvalidImageError", "ALLOWED_CONTENT_TYPES", "MAX_FILE_SIZE_BYTES"]
