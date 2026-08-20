import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
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

    return DownloadResponse(order_id=order.id, photos=download_photos, expires_in=ttl)


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
