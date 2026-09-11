"""Pipeline d'indexation faciale execute en arriere-plan apres l'upload.

Choix d'architecture : FastAPI BackgroundTasks / taches asyncio (pas de file
de messages separee type Celery/Redis) pour rester dans le stack defini au
cahier des charges pour cette phase. Consequence assumee : une indexation en
cours est perdue si le backend redemarre. D'ou `recover_unfinished_indexing`,
lance a chaque demarrage, qui reprend toute photo restee "pending" ou
"processing" (avant ce correctif, 5 photos de l'evenement IIT etaient restees
bloquees des semaines, invisibles pour la recherche faciale).
"""

import asyncio
import logging
import uuid
from collections.abc import Callable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.face_embedding import FaceEmbedding
from app.models.photo import IndexingStatus, Photo
from app.services.face_clusters import face_cluster_cache
from app.services.face_crops import face_crop_key
from app.services.face_recognition import ImageDecodeError, detect_faces_async
from app.services.storage import StorageService, get_storage_service

logger = logging.getLogger("myface.face_indexing")

# Nombre de photos traitees en parallele par index_photos_faces. Seule la
# vraie inference GPU est serialisee (voir _inference_lock dans
# face_recognition.py) ; tout le reste (telechargement storage, ecritures DB)
# peut se chevaucher entre photos. Sans ca, FastAPI BackgroundTasks execute
# les taches une par une, strictement sequentiellement : un lot de 100+
# photos multiplie chaque aller-retour reseau (R2, Neon) par le nombre de
# photos au lieu de les recouvrir, observe en usage comme un ralentissement
# tres visible de l'indexation apres upload d'un gros lot.
INDEXING_CONCURRENCY = 4

UNFINISHED_STATUSES = (IndexingStatus.PENDING, IndexingStatus.PROCESSING)

# Photos deja programmees (en file ou en cours) dans ce process : une
# relance manuelle ("Relancer l'indexation") ou la reprise au demarrage ne
# doivent pas programmer une deuxieme fois une photo deja prise en charge.
_scheduled: set[uuid.UUID] = set()


def _as_uuid(value: uuid.UUID | str) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def is_scheduled(photo_id: uuid.UUID) -> bool:
    return photo_id in _scheduled


async def index_photo_faces(
    photo_id: uuid.UUID | str,
    storage: StorageService | None = None,
    session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
) -> None:
    """Traite une photo : detection de visages + embeddings + ecriture DB.

    Idempotent : les embeddings existants de la photo (re-indexation) sont
    remplaces, jamais dupliques.

    `storage` et `session_factory` sont injectables (au lieu d'etre codes en
    dur) pour que cette fonction reste testable directement, sans dependre
    des overrides FastAPI qui ne s'appliquent qu'aux requetes HTTP.
    """
    # Toute la fonction est protegee : une exception non rattrapee ici
    # remonterait dans le mecanisme BackgroundTasks de Starlette et casserait
    # la reponse HTTP deja envoyee au client (observe en test).
    try:
        storage = storage or get_storage_service()
        replaced_crop_keys: list[str] = []
        event_id: uuid.UUID | None = None

        async with session_factory() as db:
            photo = await db.get(Photo, photo_id)
            if photo is None:
                logger.error("Indexation faciale: photo %s introuvable", photo_id)
                return
            event_id = photo.event_id

            photo.indexing_status = IndexingStatus.PROCESSING
            await db.commit()

            try:
                image_bytes = await storage.download(photo.original_key)

                faces = await detect_faces_async(image_bytes)

                previous = (
                    await db.execute(
                        select(FaceEmbedding.id, FaceEmbedding.crop_key).where(FaceEmbedding.photo_id == photo.id)
                    )
                ).all()
                if previous:
                    await db.execute(delete(FaceEmbedding).where(FaceEmbedding.photo_id == photo.id))
                    replaced_crop_keys = [crop_key or face_crop_key(event_id, fid) for fid, crop_key in previous]

                for face in faces:
                    db.add(
                        FaceEmbedding(
                            photo_id=photo.id,
                            vector=face.embedding,
                            bounding_box={
                                "x1": face.bounding_box[0],
                                "y1": face.bounding_box[1],
                                "x2": face.bounding_box[2],
                                "y2": face.bounding_box[3],
                            },
                            confidence=face.confidence,
                            sharpness=face.sharpness,
                        )
                    )

                photo.indexing_status = IndexingStatus.DONE
                await db.commit()
                logger.info("Photo %s indexee : %d visage(s) detecte(s)", photo_id, len(faces))
            except ImageDecodeError as exc:
                await db.rollback()
                photo.indexing_status = IndexingStatus.FAILED
                await db.commit()
                logger.warning("Photo %s: echec indexation (%s)", photo_id, exc)
                return
            except Exception:
                await db.rollback()
                photo.indexing_status = IndexingStatus.FAILED
                await db.commit()
                logger.exception("Photo %s: erreur inattendue pendant l'indexation faciale", photo_id)
                return

        # Les groupes de visages de l'evenement ont change.
        face_cluster_cache.invalidate(event_id)

        # Vignettes des anciens visages (re-indexation) : devenues orphelines.
        for key in replaced_crop_keys:
            try:
                await storage.delete(key)
            except Exception:
                logger.warning("Vignette orpheline non supprimee : %s", key)
    except Exception:
        logger.exception("Photo %s: echec critique du pipeline d'indexation", photo_id)


async def index_photos_faces(
    photo_ids: list[uuid.UUID],
    storage: StorageService | None = None,
    session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    max_concurrency: int = INDEXING_CONCURRENCY,
) -> int:
    """Indexe plusieurs photos avec un parallelisme borne (voir
    INDEXING_CONCURRENCY) : a utiliser pour un lot d'upload plutot qu'un
    background_tasks.add_task par photo, qui serialiserait tout via
    BackgroundTasks (execution une par une, pas concurrente).

    Les photos deja programmees dans ce process sont ignorees. Renvoie le
    nombre de photos effectivement traitees par cet appel."""
    to_index: list[uuid.UUID] = []
    for raw_id in photo_ids:
        photo_id = _as_uuid(raw_id)
        if photo_id in _scheduled:
            continue
        _scheduled.add(photo_id)
        to_index.append(photo_id)

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _bounded(photo_id: uuid.UUID) -> None:
        try:
            async with semaphore:
                await index_photo_faces(photo_id, storage, session_factory)
        finally:
            _scheduled.discard(photo_id)

    await asyncio.gather(*(_bounded(photo_id) for photo_id in to_index))
    return len(to_index)


async def recover_unfinished_indexing(
    storage: StorageService | None = None,
    session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
) -> int:
    """Reprend au demarrage toute photo restee "pending"/"processing" : dans
    un process qui demarre, aucune n'est reellement en cours de traitement,
    elles ont forcement ete interrompues (redemarrage, crash)."""
    async with session_factory() as db:
        result = await db.execute(select(Photo.id).where(Photo.indexing_status.in_(UNFINISHED_STATUSES)))
        photo_ids = [row[0] for row in result.all()]

    if not photo_ids:
        return 0
    logger.info("Reprise de l'indexation de %d photo(s) interrompue(s)", len(photo_ids))
    return await index_photos_faces(photo_ids, storage, session_factory)
