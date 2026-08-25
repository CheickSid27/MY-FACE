import secrets
import uuid

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sklearn.cluster import DBSCAN
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.deps import get_current_user
from app.models.event import Event
from app.models.event_payment_method import EventPaymentMethod
from app.models.face_embedding import FaceEmbedding
from app.models.order import PaymentMethod
from app.models.photo import Photo
from app.models.user import User
from app.schemas.event import EventCreate, EventListItem, EventPublicRead, EventRead, EventUpdate
from app.schemas.face import ClusterListResponse, FaceCluster
from app.schemas.payment_method import EventPaymentMethodRead
from app.schemas.watched_folder import WatchedFileRead, WatchedFolderRead
from app.services.face_crops import get_or_create_face_crop_url
from app.services.folder_watcher import folder_watcher
from app.services.photo_urls import to_photo_read
from app.services.storage import StorageService, get_storage_service

settings = get_settings()

router = APIRouter(prefix="/events", tags=["events"])

QR_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
QR_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


def _generate_kiosk_token() -> str:
    return secrets.token_urlsafe(24)


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Event:
    event = Event(
        name=payload.name,
        date=payload.date,
        location=payload.location,
        pricing=payload.pricing.model_dump(),
        organizer_id=current_user.id,
        kiosk_token=_generate_kiosk_token(),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("", response_model=list[EventListItem])
async def list_events(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EventListItem]:
    result = await db.execute(
        select(Event, func.count(Photo.id).label("photo_count"))
        .outerjoin(Photo, Photo.event_id == Event.id)
        .where(Event.organizer_id == current_user.id)
        .group_by(Event.id)
        .order_by(Event.date.desc())
    )
    return [
        EventListItem(
            id=event.id,
            name=event.name,
            date=event.date,
            location=event.location,
            photo_count=photo_count,
        )
        for event, photo_count in result.all()
    ]


async def _get_owned_event(event_id: uuid.UUID, current_user: User, db: AsyncSession) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evenement introuvable")
    if event.organizer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse")
    return event


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Event:
    return await _get_owned_event(event_id, current_user, db)


@router.get("/{event_id}/public", response_model=EventPublicRead)
async def get_event_public(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Event:
    """Vue publique pour l'ecran Accueil borne/invite : pas d'authentification."""
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evenement introuvable")
    return event


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: uuid.UUID,
    payload: EventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Event:
    event = await _get_owned_event(event_id, current_user, db)

    update_data = payload.model_dump(exclude_unset=True)
    if "pricing" in update_data and update_data["pricing"] is not None:
        update_data["pricing"] = payload.pricing.model_dump()

    for field, value in update_data.items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    return event


async def _compute_face_clusters(
    event_id: uuid.UUID, db: AsyncSession, storage: StorageService
) -> ClusterListResponse:
    result = await db.execute(
        select(FaceEmbedding, Photo)
        .join(Photo, Photo.id == FaceEmbedding.photo_id)
        .where(Photo.event_id == event_id)
    )
    rows = result.all()

    if not rows:
        return ClusterListResponse(clusters=[], unclustered_count=0)

    vectors = np.array([row.FaceEmbedding.vector for row in rows], dtype=np.float32)
    # metric="cosine" : eps est alors une distance cosinus (1 - similarite),
    # coherent avec face_cluster_eps et avec le seuil utilise pour le scan
    # visiteur (face_match_similarity_threshold). Voir core/config.py.
    labels = DBSCAN(
        eps=settings.face_cluster_eps,
        min_samples=settings.face_cluster_min_samples,
        metric="cosine",
    ).fit_predict(vectors)

    clusters: dict[int, dict] = {}
    # Un visage "bruit" pour DBSCAN (aucun voisin a moins de eps) reste une
    # personne a part entiere, meme photographiee une seule fois : on lui
    # cree son propre cluster a une photo plutot que de le rejeter dans
    # unclustered_count, pour que le client puisse quand meme le retrouver
    # dans la vue "personnes detectees".
    next_singleton_id = -1

    for label, row in zip(labels, rows):
        if label == -1:
            cluster_id = next_singleton_id
            next_singleton_id -= 1
        else:
            cluster_id = int(label)
        cluster = clusters.setdefault(
            cluster_id,
            {"photos": {}, "best_confidence": -1.0, "representative": None, "representative_face": None},
        )
        cluster["photos"][row.Photo.id] = row.Photo
        if row.FaceEmbedding.confidence > cluster["best_confidence"]:
            cluster["best_confidence"] = row.FaceEmbedding.confidence
            cluster["representative"] = row.Photo
            cluster["representative_face"] = row.FaceEmbedding

    face_clusters = [
        FaceCluster(
            cluster_id=cluster_id,
            photo_count=len(data["photos"]),
            representative_photo=await to_photo_read(data["representative"], storage),
            representative_face_url=await get_or_create_face_crop_url(
                data["representative_face"], data["representative"], storage
            ),
            photo_ids=list(data["photos"].keys()),
        )
        for cluster_id, data in sorted(clusters.items(), key=lambda kv: -len(kv[1]["photos"]))
    ]

    return ClusterListResponse(clusters=face_clusters, unclustered_count=0)


@router.get("/{event_id}/clusters", response_model=ClusterListResponse)
async def get_event_face_clusters(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> ClusterListResponse:
    """Pre-groupage des visages inconnus (DBSCAN) pour la vue admin
    "personnes detectees". Regroupe par similarite, pas par identite verifiee."""
    await _get_owned_event(event_id, current_user, db)
    return await _compute_face_clusters(event_id, db, storage)


@router.get("/{event_id}/clusters/public", response_model=ClusterListResponse)
async def get_event_face_clusters_public(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> ClusterListResponse:
    """Meme pre-groupage, expose sans authentification pour le bouton visiteur
    "Trouver mon visage" (parcourir les visages detectes et cliquer sur le
    sien) : aucune identite n'est revelee, uniquement des vignettes groupees
    par similarite."""
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evenement introuvable")
    return await _compute_face_clusters(event_id, db, storage)


@router.get("/{event_id}/watched-folder", response_model=WatchedFolderRead)
async def get_watched_folder(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchedFolderRead:
    """Etat du dossier surveille pour cet evenement (voir
    services/folder_watcher.py) : chemin a utiliser cote PC hote + statut des
    derniers fichiers vus (en cours de copie / ingere / erreur)."""
    await _get_owned_event(event_id, current_user, db)
    folder_path = f"{settings.watched_folder_host_display_path}/{event_id}/"
    files = [
        WatchedFileRead(filename=f.filename, status=f.status, detail=f.detail)
        for f in folder_watcher.status_for_event(event_id)
    ]
    return WatchedFolderRead(folder_path=folder_path, files=files)


@router.get("/{event_id}/payment-methods", response_model=list[EventPaymentMethodRead])
async def list_event_payment_methods(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> list[EventPaymentMethodRead]:
    """Moyens de paiement configures par l'organisateur pour cet evenement,
    utilise par le panier cote visiteur (pas d'authentification)."""
    result = await db.execute(
        select(EventPaymentMethod).where(EventPaymentMethod.event_id == event_id)
    )
    methods = result.scalars().all()
    return [
        EventPaymentMethodRead(
            id=m.id,
            method=m.method,
            phone_number=m.phone_number,
            qr_image_url=await storage.get_presigned_url(m.qr_image_key, expires_in=3600),
        )
        for m in methods
    ]


@router.put("/{event_id}/payment-methods/{method}", response_model=EventPaymentMethodRead)
async def upsert_event_payment_method(
    event_id: uuid.UUID,
    method: PaymentMethod,
    phone_number: str = Form(min_length=6, max_length=32),
    qr_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> EventPaymentMethodRead:
    """Cree ou remplace la config (QR marchand + numero) d'un moyen de
    paiement pour cet evenement. Reserve a l'organisateur proprietaire."""
    if method == PaymentMethod.MANUAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'manual' est reserve au mode test interne, pas configurable ici",
        )
    await _get_owned_event(event_id, current_user, db)

    if qr_image.content_type not in QR_ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type d'image non supporte")
    data = await qr_image.read()
    if len(data) > QR_MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image trop volumineuse (max 5 Mo)")
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image vide")

    result = await db.execute(
        select(EventPaymentMethod).where(
            EventPaymentMethod.event_id == event_id, EventPaymentMethod.method == method
        )
    )
    existing = result.scalar_one_or_none()

    extension = (qr_image.filename or "qr.jpg").rsplit(".", 1)[-1].lower()
    qr_key = f"events/{event_id}/payment_qr/{method.value}.{extension}"
    await storage.upload(qr_key, data, qr_image.content_type)

    if existing is None:
        existing = EventPaymentMethod(event_id=event_id, method=method, phone_number=phone_number, qr_image_key=qr_key)
        db.add(existing)
    else:
        existing.phone_number = phone_number
        existing.qr_image_key = qr_key

    await db.commit()
    await db.refresh(existing)

    return EventPaymentMethodRead(
        id=existing.id,
        method=existing.method,
        phone_number=existing.phone_number,
        qr_image_url=await storage.get_presigned_url(existing.qr_image_key, expires_in=3600),
    )


@router.delete("/{event_id}/payment-methods/{method}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_payment_method(
    event_id: uuid.UUID,
    method: PaymentMethod,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_owned_event(event_id, current_user, db)
    result = await db.execute(
        select(EventPaymentMethod).where(
            EventPaymentMethod.event_id == event_id, EventPaymentMethod.method == method
        )
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Moyen de paiement non configure")
    await db.delete(existing)
    await db.commit()


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    event = await _get_owned_event(event_id, current_user, db)
    await db.delete(event)
    await db.commit()
