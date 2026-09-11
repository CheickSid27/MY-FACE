import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.event import Event
from app.models.face_embedding import FaceEmbedding
from app.models.photo import Photo
from app.schemas.face import FaceScanMatch, FaceScanResponse, PhotoIndexingStatus
from app.services.access import is_kiosk_request
from app.services.face_recognition import ImageDecodeError, detect_faces_async
from app.services.photo_urls import to_photo_read
from app.services.storage import StorageService, get_storage_service

router = APIRouter(prefix="/faces", tags=["faces"])

settings = get_settings()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SELFIE_SIZE_BYTES = 10 * 1024 * 1024
MAX_MATCHES = 300


@router.post("/scan", response_model=FaceScanResponse)
async def scan_face(
    event_id: uuid.UUID,
    consent: bool = Form(...),
    selfie: UploadFile = File(...),
    kiosk_token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> FaceScanResponse:
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consentement requis avant tout traitement de donnees biometriques",
        )

    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evenement introuvable")

    if selfie.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type de fichier non supporte: {selfie.content_type}",
        )

    data = await selfie.read()
    if not data or len(data) > MAX_SELFIE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier invalide ou trop volumineux")

    try:
        faces = await detect_faces_async(data)
    except ImageDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not faces:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun visage detecte dans la photo")

    def _bbox_area(face) -> float:
        x1, y1, x2, y2 = face.bounding_box
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)

    query_face = max(faces, key=_bbox_area)

    max_distance = 1 - settings.face_match_similarity_threshold
    distance_expr = FaceEmbedding.vector.cosine_distance(query_face.embedding)

    subquery = (
        select(
            FaceEmbedding.photo_id.label("photo_id"),
            func.min(distance_expr).label("min_distance"),
        )
        .join(Photo, Photo.id == FaceEmbedding.photo_id)
        .where(Photo.event_id == event_id, distance_expr <= max_distance)
        .group_by(FaceEmbedding.photo_id)
        .subquery()
    )

    stmt = (
        select(Photo, subquery.c.min_distance)
        .join(subquery, Photo.id == subquery.c.photo_id)
        .order_by(subquery.c.min_distance)
        .limit(MAX_MATCHES)
    )
    result = await db.execute(stmt)

    # Apercus filigranes sur le telephone d'un invite, nets a la borne.
    clean_preview = is_kiosk_request(event, kiosk_token)
    matches = [
        FaceScanMatch(
            photo=await to_photo_read(photo, storage, clean_preview=clean_preview),
            similarity=round(1 - distance, 4),
        )
        for photo, distance in result.all()
    ]

    return FaceScanResponse(matches=matches, faces_detected_in_selfie=len(faces))


@router.get("/status/{photo_id}", response_model=PhotoIndexingStatus)
async def get_photo_indexing_status(
    photo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PhotoIndexingStatus:
    photo = await db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable")
    return PhotoIndexingStatus(photo_id=photo.id, indexing_status=photo.indexing_status)
