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
    sharpness: float


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


def _crop_sharpness(image: np.ndarray, bbox: list[float]) -> float:
    """Variance du Laplacien sur le crop du visage : mesure la quantite de
    details/contours nets dans la zone, faible pour un visage flou (mise au
    point sur autre chose, mouvement) meme si InsightFace le detecte avec une
    confidence elevee (det_score mesure la presence d'un visage, pas sa nettete)."""
    h, w = image.shape[:2]
    x1, y1, x2, y2 = (int(round(v)) for v in bbox)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    crop = image[y1:y2, x1:x2]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


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
        bbox = [float(x) for x in face.bbox.tolist()]
        sharpness = _crop_sharpness(image, bbox)
        if sharpness < settings.face_min_sharpness:
            continue
        results.append(
            DetectedFace(
                embedding=face.normed_embedding.tolist(),
                bounding_box=bbox,
                confidence=float(face.det_score),
                sharpness=sharpness,
            )
        )
    return results


async def detect_faces_async(image_bytes: bytes) -> list[DetectedFace]:
    """Point d'entree a utiliser depuis le code async : execute `detect_faces`
    dans un thread, sous un verrou global pour eviter tout appel concurrent
    a l'instance InsightFace partagee."""
    async with _inference_lock:
        return await asyncio.to_thread(detect_faces, image_bytes)


async def preload_face_analysis() -> None:
    """Charge le modele (disque + GPU) au demarrage du serveur plutot qu'au
    premier /faces/scan ou upload reel : sans ca, le tout premier appel apres
    chaque redemarrage du conteneur paie ce cout (plusieurs secondes) au lieu
    du serveur, et un probleme GPU/fichiers modele ne se decouvre qu'au
    premier vrai client plutot qu'au demarrage. Echec non bloquant : logue et
    on laisse le premier appel reel reessayer (meme comportement qu'avant)."""
    try:
        await asyncio.to_thread(_get_face_analysis)
    except Exception:
        logger.exception("InsightFace: echec du prechargement au demarrage")
