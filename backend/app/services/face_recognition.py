"""Detection de visages et generation d'embeddings via InsightFace (buffalo_l).

Tente GPU (CUDAExecutionProvider) en priorite, bascule automatiquement sur
CPU si aucun GPU n'est disponible dans le conteneur (onnxruntime choisit le
premier provider fonctionnel dans la liste). Le provider effectivement
utilise est logue au demarrage pour ne jamais masquer un repli silencieux.
"""

import asyncio
import logging
from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.core.config import get_settings

logger = logging.getLogger("myface.face_recognition")

settings = get_settings()

# InsightFace/onnxruntime n'est pas garanti thread-safe pour des appels
# concurrents sur la meme session partagee (observe : blocage du process en
# cas de scan + indexation en arriere-plan simultanes). On serialise donc
# tous les appels d'inference avec ce verrou plutot que de risquer un deadlock.
_inference_lock = asyncio.Lock()


class ImageDecodeError(Exception):
    pass


@dataclass
class DetectedFace:
    embedding: list[float]
    bounding_box: list[float]
    confidence: float


@lru_cache
def _get_face_analysis() -> FaceAnalysis:
    app = FaceAnalysis(name="buffalo_l", providers=settings.face_recognition_providers_list)
    # det_size=(640,640) : teste avec 1024/1280 sur des photos reelles
    # (voir historique) sans gain mesurable sur des groupes de 2-6 personnes
    # normales, et avec une regression nette sur les images tres chargees
    # (davantage de detections a faible confiance ecartees a plus haute
    # resolution). On garde donc la valeur par defaut InsightFace.
    app.prepare(ctx_id=0, det_size=(640, 640))

    active_providers = set()
    for model in app.models.values():
        session = getattr(model, "session", None)
        if session is not None:
            active_providers.update(session.get_providers())

    if "CUDAExecutionProvider" in active_providers:
        logger.info("InsightFace: inference GPU active (CUDAExecutionProvider)")
    else:
        logger.warning(
            "InsightFace: GPU indisponible, repli sur CPU (providers actifs: %s)",
            active_providers or "inconnu",
        )

    return app


def detect_faces(image_bytes: bytes) -> list[DetectedFace]:
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ImageDecodeError("Image illisible ou format non supporte")

    app = _get_face_analysis()
    faces = app.get(image)

    results = []
    for face in faces:
        if float(face.det_score) < settings.face_detection_min_confidence:
            continue
        results.append(
            DetectedFace(
                embedding=face.normed_embedding.tolist(),
                bounding_box=[float(x) for x in face.bbox.tolist()],
                confidence=float(face.det_score),
            )
        )
    return results


async def detect_faces_async(image_bytes: bytes) -> list[DetectedFace]:
    """Point d'entree a utiliser depuis le code async : execute `detect_faces`
    dans un thread, sous un verrou global pour eviter tout appel concurrent
    a l'instance InsightFace partagee."""
    async with _inference_lock:
        return await asyncio.to_thread(detect_faces, image_bytes)
