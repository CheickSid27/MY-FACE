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
from app.services.access import get_manageable_event, is_kiosk_request
from app.services.face_clusters import face_cluster_cache
from app.services.face_crops import face_crop_key
from app.services.face_indexing import index_photos_faces
from app.services.ingestion import InvalidImageError, ingest_photo
from app.services.photo_urls import to_photo_reads
from app.services.storage import StorageService, get_storage_service

router = APIRouter(tags=["photos"])


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
    await get_manageable_event(event_id, current_user, db)

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

    return PhotoUploadResult(uploaded=await to_photo_reads(uploaded, storage, clean_preview=True), errors=errors)


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
    await get_manageable_event(photo.event_id, current_user, db)

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

    # Vignettes des visages (voir services/face_crops.py) : a recuperer avant
    # que la suppression en cascade des embeddings ne fasse perdre leurs cles.
    embeddings_result = await db.execute(
        select(FaceEmbedding.id, FaceEmbedding.crop_key).where(FaceEmbedding.photo_id == photo_id)
    )
    face_crop_keys = [
        crop_key or face_crop_key(photo.event_id, embedding_id)
        for embedding_id, crop_key in embeddings_result.all()
    ]
    event_id = photo.event_id
    file_keys = [
        photo.original_key,
        photo.thumbnail_key,
        photo.preview_key,
        photo.preview_watermarked_key,
        *face_crop_keys,
    ]

    # order_items/cart_items/face_embeddings d'orders non payes partent en
    # cascade DB (ON DELETE CASCADE, voir models/order.py, models/cart.py,
    # models/face_embedding.py).
    await db.delete(photo)
    await db.commit()
    # Retrait immediat : une photo supprimee ne doit plus apparaitre, meme
    # le temps d'un recalcul (mode tolerant des invites).
    face_cluster_cache.invalidate(event_id, drop=True)

    # Fichiers supprimes apres le commit : si la base refuse la suppression,
    # aucun fichier n'a ete perdu.
    for key in file_keys:
        if key:
            await storage.delete(key)


@router.get("/events/{event_id}/photos", response_model=PhotoListResponse)
async def list_event_photos(
    event_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    kiosk_token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> PhotoListResponse:
    """Galerie publique. Apercus grand format filigranes, sauf a la borne
    (kiosk_token valide) : voir services/photo_urls.py."""
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evenement introuvable")

    # Compte total + page de resultats en UNE requete (window function) plutot
    # que deux allers-retours separes (COUNT puis SELECT) : chaque
    # aller-retour vers la base geree (Neon, distante) coute significativement
    # plus cher que la complexite de la requete elle-meme, observe en usage
    # comme une latence perceptible a chaque changement de page de galerie.
    result = await db.execute(
        select(Photo, func.count(Photo.id).over().label("total_count"))
        .where(Photo.event_id == event_id)
        .order_by(Photo.uploaded_at.desc(), Photo.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.all()
    photos = [row.Photo for row in rows]
    total = rows[0].total_count if rows else 0

    if total == 0 and page > 1:
        # La window function ne compte que les lignes de CETTE page : sur une
        # page vide (au-dela du total reel), on doit re-interroger le compte
        # separement pour ne pas renvoyer total=0 a tort.
        total_result = await db.execute(select(func.count(Photo.id)).where(Photo.event_id == event_id))
        total = total_result.scalar_one()

    return PhotoListResponse(
        items=await to_photo_reads(photos, storage, clean_preview=is_kiosk_request(event, kiosk_token)),
        total=total,
        page=page,
        page_size=page_size,
    )
