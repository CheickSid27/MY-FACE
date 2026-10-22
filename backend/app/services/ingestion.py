"""Logique d'ingestion d'une photo (validation, generation thumbnail/preview,
upload storage, creation de la ligne Photo), partagee entre l'upload manuel
(routers/photos.py) et le dossier surveille (services/folder_watcher.py)."""

import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo import IndexingStatus, Photo
from app.services.storage import StorageService
from app.services.raw_images import is_raw_filename, raw_to_jpeg
from app.services.thumbnails import InvalidImageError, generate_preview, generate_thumbnail
from app.services.watermark import WATERMARK_TEXT, apply_watermark, watermarked_preview_key

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
# 70 Mo : JPEG haute qualite des boitiers recents et fichiers RAW (22/10)
MAX_FILE_SIZE_BYTES = 70 * 1024 * 1024


@dataclass
class _Derivatives:
    thumbnail: bytes
    preview: bytes
    preview_watermarked: bytes


def _build_derivatives(data: bytes, watermark_text: str) -> _Derivatives:
    # Calculs Pillow purement CPU (plusieurs centaines de ms sur un original
    # de 25 Mo) : executes dans un thread par l'appelant, jamais dans la
    # boucle d'evenements.
    preview = generate_preview(data)
    return _Derivatives(
        thumbnail=generate_thumbnail(data),
        preview=preview,
        preview_watermarked=apply_watermark(preview, watermark_text),
    )


async def ingest_photo(
    event_id: uuid.UUID,
    filename: str,
    content_type: str,
    data: bytes,
    db: AsyncSession,
    storage: StorageService,
    watermark_text: str = WATERMARK_TEXT,
) -> Photo:
    """Valide et importe une photo, l'ajoute a la session `db` (non commit).

    `watermark_text` : texte incruste dans l'apercu servi aux invites (nom du
    photographe pour les packs payants, voir services/packs.py).

    Leve ValueError / InvalidImageError si le fichier est invalide, a
    l'appelant de decider comment reporter l'erreur (reponse HTTP, log, ...)."""
    raw_data: bytes | None = None
    if is_raw_filename(filename):
        # RAW : le navigateur annonce un type quelconque, seule l'extension
        # compte. Le RAW est garde, un JPEG pleine resolution sert d'original.
        if len(data) > MAX_FILE_SIZE_BYTES:
            raise ValueError("Fichier trop volumineux (max 70 Mo)")
        if not data:
            raise ValueError("Fichier vide")
        raw_data = data
        data = await asyncio.to_thread(raw_to_jpeg, raw_data)
        content_type = "image/jpeg"
    elif content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Type de fichier non pris en charge : {content_type}")
    if len(data) > MAX_FILE_SIZE_BYTES and raw_data is None:
        raise ValueError("Fichier trop volumineux (max 70 Mo)")
    if not data:
        raise ValueError("Fichier vide")

    derivatives = await asyncio.to_thread(_build_derivatives, data, watermark_text)

    photo_id = uuid.uuid4()
    raw_extension = (filename or "photo.raw").rsplit(".", 1)[-1].lower() if raw_data is not None else None
    if raw_data is not None:
        # Les invites recoivent le JPEG : meme nom, extension .jpg
        filename = f"{(filename or 'photo').rsplit('.', 1)[0]}.jpg"
    extension = (filename or "photo.jpg").rsplit(".", 1)[-1].lower()
    original_key = f"events/{event_id}/originals/{photo_id}.{extension}"
    thumbnail_key = f"events/{event_id}/thumbnails/{photo_id}.jpg"
    preview_key = f"events/{event_id}/previews/{photo_id}.jpg"
    preview_wm_key = watermarked_preview_key(event_id, photo_id)

    # Les 4 envois sont independants : en parallele, le temps d'ingestion
    # d'une photo n'est plus la somme de 4 allers-retours vers le stockage.
    raw_key = f"events/{event_id}/raw/{photo_id}.{raw_extension}" if raw_data is not None else None
    uploads = []
    if raw_data is not None and raw_key is not None:
        uploads.append(storage.upload(raw_key, raw_data, "application/octet-stream"))
    await asyncio.gather(
        *uploads,
        storage.upload(original_key, data, content_type),
        storage.upload(thumbnail_key, derivatives.thumbnail, "image/jpeg"),
        storage.upload(preview_key, derivatives.preview, "image/jpeg"),
        storage.upload(preview_wm_key, derivatives.preview_watermarked, "image/jpeg"),
    )

    photo = Photo(
        id=photo_id,
        event_id=event_id,
        original_key=original_key,
        raw_key=raw_key,
        thumbnail_key=thumbnail_key,
        preview_key=preview_key,
        preview_watermarked_key=preview_wm_key,
        original_filename=filename or f"{photo_id}.{extension}",
        indexing_status=IndexingStatus.PENDING,
    )
    db.add(photo)
    return photo


__all__ = ["ingest_photo", "InvalidImageError", "ALLOWED_CONTENT_TYPES", "MAX_FILE_SIZE_BYTES"]
