import io
import os
import uuid
import zipfile

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.order import Order, OrderItem, OrderStatus
from app.models.photo import Photo
from app.schemas.download import DownloadPhoto, DownloadResponse
from app.services.qr import generate_qr_png
from app.services.storage import StorageService, get_storage_service

router = APIRouter(prefix="/download", tags=["download"])

settings = get_settings()


@router.get("/{order_id}", response_model=DownloadResponse)
async def get_download_links(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> DownloadResponse:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    if order.status != OrderStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telechargement indisponible : le paiement n'est pas confirme",
        )

    result = await db.execute(
        select(Photo)
        .join(OrderItem, OrderItem.photo_id == Photo.id)
        .where(OrderItem.order_id == order_id)
    )
    photos = result.scalars().all()

    ttl = settings.download_url_ttl_seconds
    download_photos = [
        DownloadPhoto(
            photo_id=photo.id,
            filename=photo.original_filename,
            url=await storage.get_presigned_url(photo.original_key, expires_in=ttl),
        )
        for photo in photos
    ]

    return DownloadResponse(order_id=order.id, event_id=order.event_id, photos=download_photos, expires_in=ttl)


@router.get("/{order_id}/zip")
async def get_download_zip(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> StreamingResponse:
    """Bundle toutes les photos payees de la commande dans un seul .zip, pour
    que le client telecharge tout en un clic au lieu de fichier par fichier."""
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    if order.status != OrderStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telechargement indisponible : le paiement n'est pas confirme",
        )

    result = await db.execute(
        select(Photo)
        .join(OrderItem, OrderItem.photo_id == Photo.id)
        .where(OrderItem.order_id == order_id)
    )
    photos = result.scalars().all()
    if not photos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune photo pour cette commande")

    buffer = io.BytesIO()
    used_names: dict[str, int] = {}
    # Photos deja compressees (JPEG) : ZIP_STORED evite de perdre du temps a
    # re-compresser pour rien.
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zf:
        for photo in photos:
            data = await storage.download(photo.original_key)
            name = photo.original_filename or f"{photo.id}.jpg"
            if name in used_names:
                used_names[name] += 1
                base, ext = os.path.splitext(name)
                name = f"{base}_{used_names[name]}{ext}"
            else:
                used_names[name] = 0
            zf.writestr(name, data)

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="myface-{order_id}.zip"'},
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
