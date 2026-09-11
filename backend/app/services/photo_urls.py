"""Construit les schemas PhotoRead avec des URLs signees, generees a la
demande (bucket prive, voir services/storage.py).

Choix de l'apercu grand format (`preview_url`) :
- borne (kiosk_token valide) et organisateur : apercu net (`preview_key`) ;
- telephone d'un invite : apercu filigrane (`preview_watermarked_key`),
  jamais l'apercu net, qui serait capturable et reutilisable sans achat
  (voir services/watermark.py). Tant qu'une ancienne photo n'a pas encore sa
  version filigranee (rattrapage en tache de fond), on sert la miniature
  400px a la place : moins nette, mais sans rien laisser fuiter."""

import datetime as dt
import uuid
from typing import Protocol

from app.models.photo import IndexingStatus
from app.schemas.photo import PhotoRead
from app.services.storage import StorageService

THUMBNAIL_URL_TTL_SECONDS = 3600


class PhotoLike(Protocol):
    """Champs lus ici : satisfait par le modele Photo comme par les
    instantanes memorises dans le cache des groupes de visages."""

    id: uuid.UUID
    event_id: uuid.UUID
    thumbnail_key: str
    preview_key: str | None
    preview_watermarked_key: str | None
    original_filename: str
    indexing_status: IndexingStatus
    uploaded_at: dt.datetime


def preview_key_for(photo: PhotoLike, clean_preview: bool) -> str:
    if clean_preview:
        # Photos anterieures a preview_key : miniature plutot que rien.
        return photo.preview_key or photo.thumbnail_key
    return photo.preview_watermarked_key or photo.thumbnail_key


async def to_photo_read(photo: PhotoLike, storage: StorageService, *, clean_preview: bool = False) -> PhotoRead:
    thumbnail_url = await storage.get_presigned_url(photo.thumbnail_key, expires_in=THUMBNAIL_URL_TTL_SECONDS)
    preview_url = await storage.get_presigned_url(
        preview_key_for(photo, clean_preview), expires_in=THUMBNAIL_URL_TTL_SECONDS
    )
    return PhotoRead(
        id=photo.id,
        event_id=photo.event_id,
        thumbnail_url=thumbnail_url,
        preview_url=preview_url,
        original_filename=photo.original_filename,
        indexing_status=photo.indexing_status,
        uploaded_at=photo.uploaded_at,
    )


async def to_photo_reads(
    photos: list[PhotoLike], storage: StorageService, *, clean_preview: bool = False
) -> list[PhotoRead]:
    return [await to_photo_read(photo, storage, clean_preview=clean_preview) for photo in photos]
