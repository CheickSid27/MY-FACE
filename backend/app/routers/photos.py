import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_session_factory
from app.deps import get_current_user
from app.models.event import Event
from app.models.face_embedding import FaceEmbedding
from app.models.order import Order, OrderItem, OrderStatus
from app.models.photo import Photo
from app.models.user import User
from app.schemas.photo import PhotoListResponse, PhotoUploadError, PhotoUploadResult
from app.services.face_indexing import index_photos_faces
from app.services.ingestion import InvalidImageError, ingest_photo
from app.services.photo_urls import to_photo_reads
from app.services.storage import StorageService, get_storage_service

router = APIRouter(tags=["photos"])


async def _get_owned_event(event_id: uuid.UUID, current_user: User, db: AsyncSession) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evenement introuvable")
    if event.organizer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse")
    return event


@router.post(
    "/photos/upload",
    response_model=PhotoUploadResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_photos(
    event_id: uuid.UUID,
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    session_factory=Depends(get_session_factory),
) -> PhotoUploadResult:
    await _get_owned_event(event_id, current_user, db)

    uploaded: list[Photo] = []
    errors: list[PhotoUploadError] = []

    for file in files:
        try:
            data = await file.read()
            photo = await ingest_photo(
                event_id, file.filename or "photo.jpg", file.content_type or "", data, db, storage
            )
            uploaded.append(photo)
        except (ValueError, InvalidImageError) as exc:
            errors.append(PhotoUploadError(filename=file.filename or "unknown", error=str(exc)))

    if uploaded:
        await db.commit()
        for photo in uploaded:
            await db.refresh(photo)
        # Un seul background task pour tout le lot, avec parallelisme borne
        # en interne (voir index_photos_faces) : BackgroundTasks execute ses
        # taches une par une, donc en programmer une par photo serialiserait
        # completement l'indexation d'un gros lot au lieu de recouvrir les
        # I/O reseau (storage, DB) entre photos.
        background_tasks.add_task(index_photos_faces, [p.id for p in uploaded], storage, session_factory)

    return PhotoUploadResult(uploaded=await to_photo_reads(uploaded, storage), errors=errors)


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> None:
    photo = await db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable")
    await _get_owned_event(photo.event_id, current_user, db)

    # Une photo deja livree dans une commande payee ne doit pas disparaitre
    # sous les pieds d'un client qui voudrait retelecharger : on bloque la
    # suppression plutot que de casser silencieusement son acces post-achat.
    sold_result = await db.execute(
        select(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(OrderItem.photo_id == photo_id, Order.status == OrderStatus.SUCCESS)
    )
    if sold_result.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette photo fait partie d'une commande deja payee, suppression impossible",
        )

    # Cles des vignettes de visage (voir services/face_crops.py) : generees a
    # la demande, pas stockees sur FaceEmbedding, donc a reconstruire ici
    # avant que la suppression en cascade des embeddings ne fasse perdre
    # leurs ids.
    embeddings_result = await db.execute(select(FaceEmbedding.id).where(FaceEmbedding.photo_id == photo_id))
    face_crop_keys = [f"events/{photo.event_id}/face-crops/{eid}.jpg" for (eid,) in embeddings_result.all()]

    for key in [photo.original_key, photo.thumbnail_key, photo.preview_key, *face_crop_keys]:
        if key:
            await storage.delete(key)

    # order_items/cart_items/face_embeddings d'orders non payes partent en
    # cascade DB (ON DELETE CASCADE, voir models/order.py, models/cart.py,
    # models/face_embedding.py).
    await db.delete(photo)
    await db.commit()


@router.get("/events/{event_id}/photos", response_model=PhotoListResponse)
async def list_event_photos(
    event_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> PhotoListResponse:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evenement introuvable")

    total_result = await db.execute(select(func.count(Photo.id)).where(Photo.event_id == event_id))
    total = total_result.scalar_one()

    result = await db.execute(
        select(Photo)
        .where(Photo.event_id == event_id)
        .order_by(Photo.uploaded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    photos = list(result.scalars().all())

    return PhotoListResponse(
        items=await to_photo_reads(photos, storage),
        total=total,
        page=page,
        page_size=page_size,
    )
