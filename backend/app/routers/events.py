import asyncio
import logging
import secrets
import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, get_session_factory
from app.core.security import hash_password, verify_password
from app.deps import get_current_user, get_optional_user, require_verified_user
from app.models.event import Event
from app.models.event_payment_method import EventPaymentMethod
from app.models.face_embedding import FaceEmbedding
from app.models.order import Order, OrderStatus, PaymentMethod
from app.models.pack_purchase import PackPurchase, PackPurchaseStatus
from app.models.photo import IndexingStatus, Photo
from app.models.user import User, UserRole
from app.schemas.event import (
    EventCreate,
    EventIndexingSummary,
    EventListItem,
    EventPublicRead,
    EventRead,
    EventUpdate,
    GalleryUnlockRequest,
    GalleryUnlockResponse,
    ReindexResponse,
)
from app.schemas.face import ClusterListResponse
from app.schemas.payment_method import EventPaymentMethodRead
from app.schemas.watched_folder import WatchedFileRead, WatchedFolderRead
from app.services import paystack
from app.services.access import get_manageable_event, is_kiosk_request
from app.services.face_clusters import build_cluster_response, face_cluster_cache
from app.services.face_indexing import index_photos_faces, is_scheduled
from app.services.folder_watcher import folder_watcher
from app.services.gallery_access import has_gallery_access, issue_gallery_token, require_gallery_access
from app.services.packs import (
    DEFAULT_PACK,
    FEATURE_CUSTOM_WATERMARK,
    FEATURE_GALLERY_PASSWORD,
    UNLIMITED_PACK,
    effective_photo_limit,
    event_has_feature,
    get_owner,
    next_pack,
    watermark_text_for,
)
from app.services.phone import normalize_phone_or_ci
from app.services.rate_limit import client_ip, limiter
from app.services.retention import photos_deadline
from app.services.qr import generate_qr_png
from app.services.thumbnails import is_valid_image
from app.services.storage import StorageService, get_storage_service
from app.services.watermark import regenerate_event_watermarks

logger = logging.getLogger("myface.events")
settings = get_settings()

router = APIRouter(prefix="/events", tags=["events"])

QR_ALLOWED_CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
QR_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
REINDEXABLE_STATUSES = (IndexingStatus.FAILED, IndexingStatus.PENDING, IndexingStatus.PROCESSING)


def _generate_kiosk_token() -> str:
    return secrets.token_urlsafe(24)


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> Event:
    if current_user.role != UserRole.ADMIN:
        # Pack Decouverte = 10 photos gratuites par evenement : sans limite du
        # nombre d'evenements gratuits, il suffirait d'en creer plusieurs.
        free_events = await db.execute(
            select(func.count(Event.id)).where(Event.organizer_id == current_user.id, Event.pack == DEFAULT_PACK)
        )
        max_free = settings.free_events_per_account
        if free_events.scalar_one() >= max_free:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Vous avez déjà un événement gratuit (pack Découverte) : passez-le au pack "
                    "Événement pour créer un autre événement"
                    if max_free == 1
                    else f"Vous avez déjà {max_free} événements gratuits : passez l'un d'eux au pack "
                    "Événement ou supprimez-en un pour en créer un autre"
                ),
            )

    event = Event(
        name=payload.name,
        date=payload.date,
        location=payload.location,
        pricing=payload.pricing.model_dump(),
        frame_caption=payload.frame_caption,
        organizer_id=current_user.id,
        kiosk_token=_generate_kiosk_token(),
        # Service photographe : un photographe commence au pack Decouverte
        # (10 photos gratuites) ; les evenements MYFACE ne sont pas limites.
        pack=UNLIMITED_PACK if current_user.role == UserRole.ADMIN else DEFAULT_PACK,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    # Le chemin du dossier surveille est affiche a l'organisateur des la
    # creation : il doit exister pour qu'il puisse y deposer ses photos.
    folder_watcher.ensure_event_folder(event.id)
    return event


@router.get("", response_model=list[EventListItem])
async def list_events(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EventListItem]:
    """Evenements de l'organisateur connecte ; TOUS les evenements pour un
    admin (avec l'email de l'organisateur de chacun)."""
    is_admin = current_user.role == UserRole.ADMIN
    query = (
        select(Event, func.count(Photo.id).label("photo_count"), User)
        .outerjoin(Photo, Photo.event_id == Event.id)
        .join(User, User.id == Event.organizer_id)
        .group_by(Event.id, User.id)
        .order_by(Event.date.desc())
    )
    if not is_admin:
        query = query.where(Event.organizer_id == current_user.id)

    rows = (await db.execute(query)).all()
    pending_ids: set[uuid.UUID] = set()
    if rows:
        pending = await db.execute(
            select(PackPurchase.event_id)
            .where(
                PackPurchase.status == PackPurchaseStatus.PENDING,
                PackPurchase.event_id.in_([event.id for event, _, _ in rows]),
            )
            .distinct()
        )
        pending_ids = set(pending.scalars().all())

    return [
        EventListItem(
            id=event.id,
            name=event.name,
            date=event.date,
            location=event.location,
            photo_count=photo_count,
            organizer_email=organizer.email if is_admin else None,
            pack=event.pack,
            photo_limit=effective_photo_limit(event, organizer),
            pack_pending=event.id in pending_ids,
        )
        for event, photo_count, organizer in rows
    ]


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Event:
    return await get_manageable_event(event_id, current_user, db)


@router.get("/{event_id}/public", response_model=EventPublicRead)
async def get_event_public(
    event_id: uuid.UUID,
    kiosk_token: str | None = Query(default=None),
    access: str | None = Query(default=None),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> EventPublicRead:
    """Vue publique pour l'ecran Accueil borne/invite : pas d'authentification.

    `kiosk_token` (optionnel) est compare cote serveur au token reel de
    l'evenement pour determiner `is_kiosk`, jamais le vrai token n'est
    renvoye ici (voir EventPublicRead), donc un client ne peut pas le
    deviner en inspectant les reponses reseau. Sans ce param ou avec un token
    invalide, `is_kiosk` vaut simplement False (comportement invite normal)."""
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    owner = await get_owner(db, event)
    photographer_name = owner.public_name if owner is not None and owner.role == UserRole.PHOTOGRAPHE else None
    return EventPublicRead(
        id=event.id,
        name=event.name,
        date=event.date,
        location=event.location,
        pricing=event.pricing,
        frame_caption=event.frame_caption,
        cash_enabled=event.cash_enabled,
        is_kiosk=is_kiosk_request(event, kiosk_token),
        online_payment=paystack.online_payment_available(owner),
        photographer_name=photographer_name,
        photographer_id=owner.id if photographer_name and owner is not None else None,
        photographer_avatar_version=owner.avatar_version if photographer_name and owner is not None else None,
        password_required=event.has_gallery_password,
        gallery_access=has_gallery_access(event, kiosk_token=kiosk_token, access_token=access, user=current_user),
        photos_available_until=photos_deadline(event),
        photos_purged=event.photos_purged_at is not None,
    )


@router.post("/{event_id}/unlock", response_model=GalleryUnlockResponse)
async def unlock_gallery(
    event_id: uuid.UUID,
    payload: GalleryUnlockRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GalleryUnlockResponse:
    """Mot de passe de la galerie (packs Evenement et Pro) : renvoie un jeton
    d'acces valable 7 jours, a passer en parametre `access` aux routes qui
    montrent des photos. Tentatives limitees par adresse et par evenement."""
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    limiter.check("gallery-unlock", f"{client_ip(request)}:{event_id}", 10, 600)
    if not event.gallery_password_hash:
        return GalleryUnlockResponse(access_token=issue_gallery_token(event))
    if not verify_password(payload.password.strip(), event.gallery_password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe incorrect")
    return GalleryUnlockResponse(access_token=issue_gallery_token(event))


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: uuid.UUID,
    payload: EventUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    session_factory=Depends(get_session_factory),
) -> Event:
    event = await get_manageable_event(event_id, current_user, db)
    owner = await get_owner(db, event)

    update_data = payload.model_dump(exclude_unset=True)
    if "pricing" in update_data:
        if payload.pricing is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tarifs manquants")
        # La grille tarifaire est remplacee en entier (prix, lots, remises) :
        # le frontend renvoie toujours la grille complete.
        update_data["pricing"] = payload.pricing.model_dump()

    # Options des packs payants (voir services/packs.py)
    upgrade = next_pack(event.pack)
    upgrade_hint = f" : disponible à partir du pack {upgrade.name}" if upgrade else ""
    old_watermark = watermark_text_for(event, owner)
    if "watermark_text" in update_data:
        text = (update_data.pop("watermark_text") or "").strip() or None
        if text and not event_has_feature(event, owner, FEATURE_CUSTOM_WATERMARK):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Filigrane personnalisé{upgrade_hint}",
            )
        event.watermark_text = text
    if "gallery_password" in update_data:
        password = (update_data.pop("gallery_password") or "").strip()
        if password and not event_has_feature(event, owner, FEATURE_GALLERY_PASSWORD):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Mot de passe de galerie{upgrade_hint}",
            )
        event.gallery_password_hash = hash_password(password) if password else None

    for field, value in update_data.items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)

    new_watermark = watermark_text_for(event, owner)
    if new_watermark != old_watermark:
        background_tasks.add_task(
            regenerate_event_watermarks,
            event.id,
            new_watermark,
            storage,
            session_factory,
            face_cluster_cache.invalidate,
        )
    return event


@router.get("/{event_id}/qr.png")
async def get_event_share_qr(
    event_id: uuid.UUID,
    kind: Literal["guest", "kiosk"] = Query(default="guest"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """QR code du lien invite (a imprimer/afficher sur place) ou du lien borne
    (a scanner uniquement avec l'appareil de la borne). Reserve a
    l'organisateur : le lien borne contient le kiosk_token."""
    event = await get_manageable_event(event_id, current_user, db)
    read = EventRead.model_validate(event)
    url = read.kiosk_url if kind == "kiosk" else read.guest_url
    png_bytes = await asyncio.to_thread(generate_qr_png, url)
    return Response(content=png_bytes, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/{event_id}/indexing", response_model=EventIndexingSummary)
async def get_event_indexing_summary(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventIndexingSummary:
    """Etat de l'indexation faciale des photos de l'evenement (pour reperer
    les photos en echec ou bloquees, invisibles pour la recherche faciale)."""
    await get_manageable_event(event_id, current_user, db)
    by_status_result = await db.execute(
        select(Photo.indexing_status, func.count(Photo.id))
        .where(Photo.event_id == event_id)
        .group_by(Photo.indexing_status)
    )
    counts = {s: 0 for s in IndexingStatus}
    for indexing_status, count in by_status_result.all():
        counts[indexing_status] = count

    faces_result = await db.execute(
        select(func.count(FaceEmbedding.id))
        .join(Photo, Photo.id == FaceEmbedding.photo_id)
        .where(Photo.event_id == event_id)
    )
    return EventIndexingSummary(
        pending=counts[IndexingStatus.PENDING],
        processing=counts[IndexingStatus.PROCESSING],
        done=counts[IndexingStatus.DONE],
        failed=counts[IndexingStatus.FAILED],
        faces=faces_result.scalar_one(),
    )


@router.post("/{event_id}/reindex", response_model=ReindexResponse, status_code=status.HTTP_202_ACCEPTED)
async def reindex_event_photos(
    event_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    session_factory=Depends(get_session_factory),
) -> ReindexResponse:
    """Relance l'indexation des photos en echec ou non terminees. Les photos
    deja en cours de traitement dans ce process ne sont pas reprogrammees."""
    await get_manageable_event(event_id, current_user, db)
    result = await db.execute(
        select(Photo.id).where(Photo.event_id == event_id, Photo.indexing_status.in_(REINDEXABLE_STATUSES))
    )
    to_index = [photo_id for (photo_id,) in result.all() if not is_scheduled(photo_id)]
    if to_index:
        background_tasks.add_task(index_photos_faces, to_index, storage, session_factory)
    return ReindexResponse(queued=len(to_index))


@router.get("/{event_id}/clusters", response_model=ClusterListResponse)
async def get_event_face_clusters(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> ClusterListResponse:
    """Pre-groupage des visages inconnus (DBSCAN) pour la vue admin
    "personnes detectees". Regroupe par similarite, pas par identite verifiee."""
    await get_manageable_event(event_id, current_user, db)
    snapshot = await face_cluster_cache.get(event_id, db, storage)
    return await build_cluster_response(snapshot, storage, clean_preview=True)


@router.get("/{event_id}/clusters/public", response_model=ClusterListResponse)
async def get_event_face_clusters_public(
    event_id: uuid.UUID,
    kiosk_token: str | None = Query(default=None),
    access: str | None = Query(default=None),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    session_factory=Depends(get_session_factory),
) -> ClusterListResponse:
    """Meme pre-groupage, expose sans authentification pour le bouton visiteur
    "Trouver mon visage" (parcourir les visages detectes et cliquer sur le
    sien) : aucune identite n'est revelee, uniquement des vignettes groupees
    par similarite. Apercus filigranes, sauf a la borne (kiosk_token valide).

    Mode tolerant (voir FaceClusterCache) : pendant l'indexation d'un lot, le
    dernier resultat est servi immediatement et recalcule en arriere-plan."""
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    require_gallery_access(event, kiosk_token=kiosk_token, access_token=access, user=current_user)
    snapshot = await face_cluster_cache.get(
        event_id, db, storage, allow_stale=True, session_factory=session_factory
    )
    return await build_cluster_response(snapshot, storage, clean_preview=is_kiosk_request(event, kiosk_token))


@router.get("/{event_id}/watched-folder", response_model=WatchedFolderRead)
async def get_watched_folder(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchedFolderRead:
    """Etat du dossier surveille pour cet evenement (voir
    services/folder_watcher.py) : chemin a utiliser cote PC hote + statut des
    derniers fichiers vus (en cours de copie / ingere / erreur)."""
    await get_manageable_event(event_id, current_user, db)
    # Evenements crees avant la creation automatique du dossier.
    folder_watcher.ensure_event_folder(event_id)
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
    qr_image: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> EventPaymentMethodRead:
    """Cree ou remplace la config (QR marchand + numero) d'un moyen de
    paiement pour cet evenement. L'image QR est obligatoire a la creation,
    optionnelle ensuite (changer seulement le numero). Reserve a
    l'organisateur de l'evenement (ou a un admin)."""
    if method in (PaymentMethod.MANUAL, PaymentMethod.CASH, PaymentMethod.GENIUSPAY, PaymentMethod.OFFERT):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{method.value}' ne se configure pas avec un QR marchand",
        )
    await get_manageable_event(event_id, current_user, db)
    try:
        phone_number = normalize_phone_or_ci(phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    result = await db.execute(
        select(EventPaymentMethod).where(
            EventPaymentMethod.event_id == event_id, EventPaymentMethod.method == method
        )
    )
    existing = result.scalar_one_or_none()

    qr_key: str | None = None
    if qr_image is not None:
        if qr_image.content_type not in QR_ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type d'image non pris en charge")
        if qr_image.size is not None and qr_image.size > QR_MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image trop volumineuse (max 5 Mo)")
        data = await qr_image.read()
        if len(data) > QR_MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image trop volumineuse (max 5 Mo)")
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image vide")
        if not await asyncio.to_thread(is_valid_image, data):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce fichier n'est pas une image lisible")
        # Extension tiree du type verifie, jamais du nom de fichier envoye
        # (qui pourrait contenir « / » ou « .. »).
        extension = QR_ALLOWED_CONTENT_TYPES[qr_image.content_type]
        qr_key = f"events/{event_id}/payment_qr/{method.value}.{extension}"
        await storage.upload(qr_key, data, qr_image.content_type)
    elif existing is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image du QR code requise")

    if existing is None:
        existing = EventPaymentMethod(event_id=event_id, method=method, phone_number=phone_number, qr_image_key=qr_key)
        db.add(existing)
    else:
        existing.phone_number = phone_number
        if qr_key is not None:
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
    await get_manageable_event(event_id, current_user, db)
    result = await db.execute(
        select(EventPaymentMethod).where(
            EventPaymentMethod.event_id == event_id, EventPaymentMethod.method == method
        )
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Moyen de paiement non configuré")
    await db.delete(existing)
    await db.commit()


async def _delete_event_files(event_id: uuid.UUID, storage: StorageService) -> None:
    try:
        deleted = await storage.delete_prefix(f"events/{event_id}/")
        logger.info("Evenement %s supprime : %d fichier(s) retire(s) du stockage", event_id, deleted)
    except Exception:
        logger.exception("Evenement %s : echec du nettoyage du stockage", event_id)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> None:
    """Supprime l'evenement, ses photos, paniers et commandes non payees, puis
    tous ses fichiers du stockage (originaux, miniatures, apercus, QR...).

    Refuse si une commande est deja payee : la suppression effacerait aussi
    (cascade) la commande du client et son acces au telechargement, meme
    regle que pour la suppression d'une photo vendue (routers/photos.py)."""
    event = await get_manageable_event(event_id, current_user, db)

    paid = await db.execute(
        select(Order.id).where(Order.event_id == event_id, Order.status == OrderStatus.SUCCESS).limit(1)
    )
    if paid.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cet événement a des commandes payées : suppression impossible, les clients "
                "doivent pouvoir retélécharger leurs photos"
            ),
        )

    await db.delete(event)
    await db.commit()
    face_cluster_cache.invalidate(event_id, drop=True)
    # Apres le commit : si la base refuse la suppression, aucun fichier n'est perdu.
    background_tasks.add_task(_delete_event_files, event_id, storage)
