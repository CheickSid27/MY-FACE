"""Logique d'ingestion d'une photo (validation, generation thumbnail/preview,
upload storage, creation de la ligne Photo), partagee entre l'upload manuel
(routers/photos.py) et le dossier surveille (services/folder_watcher.py)."""

import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo import IndexingStatus, Photo
from app.services.storage import StorageService
from app.services.thumbnails import InvalidImageError, generate_preview, generate_thumbnail
from app.services.watermark import apply_watermark, watermarked_preview_key

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024


@dataclass
class _Derivatives:
    thumbnail: bytes
    preview: bytes
    preview_watermarked: bytes


def _build_derivatives(data: bytes) -> _Derivatives:
    # Calculs Pillow purement CPU (plusieurs centaines de ms sur un original
    # de 25 Mo) : executes dans un thread par l'appelant, jamais dans la
    # boucle d'evenements.
    preview = generate_preview(data)
    return _Derivatives(
        thumbnail=generate_thumbnail(data),
        preview=preview,
        preview_watermarked=apply_watermark(preview),
    )


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

    derivatives = await asyncio.to_thread(_build_derivatives, data)

    photo_id = uuid.uuid4()
    extension = (filename or "photo.jpg").rsplit(".", 1)[-1].lower()
    original_key = f"events/{event_id}/originals/{photo_id}.{extension}"
    thumbnail_key = f"events/{event_id}/thumbnails/{photo_id}.jpg"
    preview_key = f"events/{event_id}/previews/{photo_id}.jpg"
    preview_wm_key = watermarked_preview_key(event_id, photo_id)

    # Les 4 envois sont independants : en parallele, le temps d'ingestion
    # d'une photo n'est plus la somme de 4 allers-retours vers le stockage.
    await asyncio.gather(
        storage.upload(original_key, data, content_type),
        storage.upload(thumbnail_key, derivatives.thumbnail, "image/jpeg"),
        storage.upload(preview_key, derivatives.preview, "image/jpeg"),
        storage.upload(preview_wm_key, derivatives.preview_watermarked, "image/jpeg"),
    )

    photo = Photo(
        id=photo_id,
        event_id=event_id,
        original_key=original_key,
        thumbnail_key=thumbnail_key,
        preview_key=preview_key,
        preview_watermarked_key=preview_wm_key,
        original_filename=filename or f"{photo_id}.{extension}",
        indexing_status=IndexingStatus.PENDING,
    )
    db.add(photo)
    return photo


__all__ = ["ingest_photo", "InvalidImageError", "ALLOWED_CONTENT_TYPES", "MAX_FILE_SIZE_BYTES"]
