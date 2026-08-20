import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_session_factory
from app.deps import get_current_user
from app.models.event import Event
from app.models.photo import IndexingStatus, Photo
from app.models.user import User
from app.schemas.photo import PhotoListResponse, PhotoUploadError, PhotoUploadResult
from app.services.face_indexing import index_photo_faces
from app.services.photo_urls import to_photo_reads
from app.services.storage import StorageService, get_storage_service
from app.services.thumbnails import InvalidImageError, generate_thumbnail

router = APIRouter(tags=["photos"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024


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
            if file.content_type not in ALLOWED_CONTENT_TYPES:
                raise ValueError(f"Type de fichier non supporte: {file.content_type}")

            data = await file.read()
            if len(data) > MAX_FILE_SIZE_BYTES:
                raise ValueError("Fichier trop volumineux (max 25 Mo)")
            if not data:
                raise ValueError("Fichier vide")

            thumbnail_bytes = generate_thumbnail(data)

            photo_id = uuid.uuid4()
            extension = (file.filename or "photo.jpg").rsplit(".", 1)[-1].lower()
            original_key = f"events/{event_id}/originals/{photo_id}.{extension}"
            thumbnail_key = f"events/{event_id}/thumbnails/{photo_id}.jpg"

            await storage.upload(original_key, data, file.content_type)
            await storage.upload(thumbnail_key, thumbnail_bytes, "image/jpeg")

            photo = Photo(
                id=photo_id,
                event_id=event_id,
                original_key=original_key,
                thumbnail_key=thumbnail_key,
                original_filename=file.filename or f"{photo_id}.{extension}",
                indexing_status=IndexingStatus.PENDING,
            )
            db.add(photo)
            uploaded.append(photo)
        except (ValueError, InvalidImageError) as exc:
            errors.append(PhotoUploadError(filename=file.filename or "unknown", error=str(exc)))

    if uploaded:
        await db.commit()
        for photo in uploaded:
            await db.refresh(photo)
            background_tasks.add_task(index_photo_faces, photo.id, storage, session_factory)

    return PhotoUploadResult(uploaded=await to_photo_reads(uploaded, storage), errors=errors)


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
