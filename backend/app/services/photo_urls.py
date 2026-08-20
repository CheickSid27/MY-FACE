"""Construit les schemas PhotoRead avec des URLs de miniature signees,
generees a la demande (bucket prive, voir services/storage.py)."""

from app.models.photo import Photo
from app.schemas.photo import PhotoRead
from app.services.storage import StorageService

THUMBNAIL_URL_TTL_SECONDS = 3600


async def to_photo_read(photo: Photo, storage: StorageService) -> PhotoRead:
    thumbnail_url = await storage.get_presigned_url(photo.thumbnail_key, expires_in=THUMBNAIL_URL_TTL_SECONDS)
    return PhotoRead(
        id=photo.id,
        event_id=photo.event_id,
        thumbnail_url=thumbnail_url,
        original_filename=photo.original_filename,
        indexing_status=photo.indexing_status,
        uploaded_at=photo.uploaded_at,
    )


async def to_photo_reads(photos: list[Photo], storage: StorageService) -> list[PhotoRead]:
    return [await to_photo_read(photo, storage) for photo in photos]
