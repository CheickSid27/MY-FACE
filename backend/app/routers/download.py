import asyncio
import os
import uuid
import zipfile
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.deps import get_optional_user
from app.models.event import Event
from app.models.order import Order, OrderItem, OrderStatus
from app.models.photo import Photo
from app.models.user import User
from app.schemas.download import DownloadPhoto, DownloadResponse, PrintedResponse
from app.services.access import can_manage_event, is_kiosk_request
from app.services.qr import generate_qr_png
from app.services.storage import StorageService, content_disposition_attachment, get_storage_service

router = APIRouter(prefix="/download", tags=["download"])

settings = get_settings()


async def _get_paid_order(order_id: uuid.UUID, db: AsyncSession) -> Order:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    if order.status != OrderStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telechargement indisponible : le paiement n'est pas confirme",
        )
    return order


@router.get("/{order_id}", response_model=DownloadResponse)
async def get_download_links(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> DownloadResponse:
    """Liens d'une commande payee. L'acces est permanent (aucune limite de
    visites) : seules les URLs signees renvoyees expirent, et la page les
    redemande a chaque ouverture/rafraichissement."""
    order = await _get_paid_order(order_id, db)

    result = await db.execute(
        select(Photo, OrderItem.print_requested)
        .join(OrderItem, OrderItem.photo_id == Photo.id)
        .where(OrderItem.order_id == order_id)
    )
    rows = result.all()

    ttl = settings.download_url_ttl_seconds
    download_photos = [
        DownloadPhoto(
            photo_id=photo.id,
            filename=photo.original_filename,
            url=await storage.get_presigned_url(
                photo.original_key, expires_in=ttl, download_filename=photo.original_filename
            ),
            thumbnail_url=await storage.get_presigned_url(photo.thumbnail_key, expires_in=ttl),
            print_requested=print_requested,
        )
        for photo, print_requested in rows
    ]

    return DownloadResponse(
        order_id=order.id,
        event_id=order.event_id,
        photos=download_photos,
        expires_in=ttl,
        printed_at=order.printed_at,
    )


@router.post("/{order_id}/printed", response_model=PrintedResponse)
async def mark_order_printed(
    order_id: uuid.UUID,
    kiosk_token: str | None = Query(default=None),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> PrintedResponse:
    """Enregistre l'impression des tirages papier de la commande (appele par
    la page d'impression une fois l'impression lancee). Reserve a la borne de
    l'evenement (kiosk_token) ou a son organisateur : c'est ce qui fait
    sortir la commande de la file "Tirages a imprimer"."""
    order = await _get_paid_order(order_id, db)
    event = await db.get(Event, order.event_id)
    allowed = is_kiosk_request(event, kiosk_token) or (
        current_user is not None and can_manage_event(event, current_user)
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impression reservee a la borne de l'evenement ou a l'organisateur",
        )

    has_prints = await db.execute(
        select(OrderItem.id).where(OrderItem.order_id == order_id, OrderItem.print_requested.is_(True)).limit(1)
    )
    if has_prints.first() is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun tirage papier dans cette commande")

    order.printed_at = datetime.now(timezone.utc)
    await db.commit()
    return PrintedResponse(printed_at=order.printed_at)


class _ChunkSink:
    """Destination d'ecriture non-seekable pour zipfile : accumule les octets
    ecrits, que le generateur vide et envoie au client apres chaque photo.
    zipfile gere nativement ce cas (flux non-seekable)."""

    def __init__(self) -> None:
        self._chunks: list[bytes] = []

    def write(self, data: bytes) -> int:
        self._chunks.append(bytes(data))
        return len(data)

    def flush(self) -> None:
        pass

    def drain(self) -> bytes:
        data = b"".join(self._chunks)
        self._chunks.clear()
        return data


def _unique_name(name: str, used: dict[str, int]) -> str:
    if name not in used:
        used[name] = 0
        return name
    used[name] += 1
    base, ext = os.path.splitext(name)
    return f"{base}_{used[name]}{ext}"


async def _zip_stream(photos: list[Photo], storage: StorageService) -> AsyncIterator[bytes]:
    """Zip genere et envoye photo par photo : la memoire ne contient jamais
    plus d'une photo a la fois (auparavant, toute la commande etait
    assemblee en RAM avant l'envoi du premier octet, plusieurs centaines de
    Mo pour une grosse commande d'originaux)."""
    sink = _ChunkSink()
    used_names: dict[str, int] = {}
    # Photos deja compressees (JPEG) : ZIP_STORED evite de perdre du temps a
    # re-compresser pour rien.
    zf = zipfile.ZipFile(sink, "w", zipfile.ZIP_STORED)  # type: ignore[arg-type]
    try:
        for photo in photos:
            data = await storage.download(photo.original_key)
            name = _unique_name(photo.original_filename or f"{photo.id}.jpg", used_names)
            await asyncio.to_thread(zf.writestr, name, data)
            del data
            yield sink.drain()
    finally:
        zf.close()
    tail = sink.drain()
    if tail:
        yield tail


@router.get("/{order_id}/zip")
async def get_download_zip(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> StreamingResponse:
    """Bundle toutes les photos payees de la commande dans un seul .zip, pour
    que le client telecharge tout en un clic au lieu de fichier par fichier."""
    await _get_paid_order(order_id, db)

    result = await db.execute(
        select(Photo)
        .join(OrderItem, OrderItem.photo_id == Photo.id)
        .where(OrderItem.order_id == order_id)
    )
    photos = list(result.scalars().all())
    if not photos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune photo pour cette commande")

    return StreamingResponse(
        _zip_stream(photos, storage),
        media_type="application/zip",
        headers={"Content-Disposition": content_disposition_attachment(f"myface-{order_id}.zip")},
    )


@router.get("/{order_id}/qr.png")
async def get_download_qr(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Response:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    if order.status != OrderStatus.SUCCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Commande non payee")

    download_page_url = f"{settings.app_base_url}/order/{order.id}/download"
    png_bytes = generate_qr_png(download_page_url)
    return Response(content=png_bytes, media_type="image/png")
