"""Pipeline d'indexation faciale execute en arriere-plan apres l'upload.

Choix d'architecture : FastAPI BackgroundTasks (pas de file de messages
separee type Celery/Redis) pour rester dans le stack defini au cahier des
charges pour cette phase. A revisiter en Phase 5 si le volume l'exige.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.face_embedding import FaceEmbedding
from app.models.photo import IndexingStatus, Photo
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


async def index_photo_faces(
    photo_id: uuid.UUID,
    storage: StorageService | None = None,
    session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
) -> None:
    """Traite une photo : detection de visages + embeddings + ecriture DB.

    `storage` et `session_factory` sont injectables (au lieu d'etre codes en
    dur) pour que cette fonction reste testable directement, sans dependre
    des overrides FastAPI qui ne s'appliquent qu'aux requetes HTTP.
    """
    # Toute la fonction est protegee : une exception non rattrapee ici
    # remonterait dans le mecanisme BackgroundTasks de Starlette et casserait
    # la reponse HTTP deja envoyee au client (observe en test).
    try:
        storage = storage or get_storage_service()
        async with session_factory() as db:
            photo = await db.get(Photo, photo_id)
            if photo is None:
                logger.error("Indexation faciale: photo %s introuvable", photo_id)
                return

            photo.indexing_status = IndexingStatus.PROCESSING
            await db.commit()

            try:
                image_bytes = await storage.download(photo.original_key)

                faces = await detect_faces_async(image_bytes)

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
            except Exception:
                await db.rollback()
                photo.indexing_status = IndexingStatus.FAILED
                await db.commit()
                logger.exception("Photo %s: erreur inattendue pendant l'indexation faciale", photo_id)
    except Exception:
        logger.exception("Photo %s: echec critique du pipeline d'indexation", photo_id)


async def index_photos_faces(
    photo_ids: list[uuid.UUID],
    storage: StorageService | None = None,
    session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    max_concurrency: int = INDEXING_CONCURRENCY,
) -> None:
    """Indexe plusieurs photos avec un parallelisme borne (voir
    INDEXING_CONCURRENCY) : a utiliser pour un lot d'upload plutot qu'un
    background_tasks.add_task par photo, qui serialiserait tout via
    BackgroundTasks (execution une par une, pas concurrente)."""
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _bounded(photo_id: uuid.UUID) -> None:
        async with semaphore:
            await index_photo_faces(photo_id, storage, session_factory)

    await asyncio.gather(*(_bounded(photo_id) for photo_id in photo_ids))
