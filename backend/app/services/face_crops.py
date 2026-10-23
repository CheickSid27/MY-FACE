"""Genere une vignette recadree sur un visage (pas la photo entiere), pour
qu'on identifie qui est qui d'un coup d'oeil dans la vue "personnes
detectees" (groupage par similarite). Generee une seule fois, puis sa cle
est memorisee sur le FaceEmbedding (colonne crop_key) : les affichages
suivants signent directement l'URL, sans redemander au stockage si le
fichier existe (un aller-retour R2 par groupe, qui rendait la vue tres lente)."""

import asyncio
import io
import uuid

from app.services.storage import StorageService
from app.services.thumbnails import open_oriented

CROP_SIZE = (320, 320)
CROP_QUALITY = 85
# Marge autour de la boite de detection (trop serree sur InsightFace, qui
# cadre au ras des traits) pour obtenir un cadrage "portrait" plus naturel.
PADDING_RATIO = 0.6


def face_crop_key(event_id: uuid.UUID, face_embedding_id: uuid.UUID) -> str:
    return f"events/{event_id}/face-crops/{face_embedding_id}.jpg"


def _crop_bytes(image_bytes: bytes, bbox: dict) -> bytes:
    # Orientation EXIF appliquee comme le fait OpenCV cote detection : sans
    # ca, sur une photo portrait de telephone, la boite du visage (calculee
    # sur l'image redressee) etait appliquee a l'image couchee.
    img = open_oriented(image_bytes).convert("RGB")
    width, height = img.size

    x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
    box_w, box_h = x2 - x1, y2 - y1
    cx, cy = x1 + box_w / 2, y1 + box_h / 2

    # Crop carre centre sur le visage, cote = plus grand cote de la boite
    # + marge, pour un cadrage coherent quelle que soit l'inclinaison de
    # la tete detectee.
    side = max(box_w, box_h) * (1 + PADDING_RATIO)
    left = max(0, cx - side / 2)
    top = max(0, cy - side / 2)
    right = min(width, cx + side / 2)
    bottom = min(height, cy + side / 2)

    cropped = img.crop((int(left), int(top), int(right), int(bottom)))
    cropped.thumbnail(CROP_SIZE)
    buffer = io.BytesIO()
    cropped.save(buffer, format="JPEG", quality=CROP_QUALITY)
    return buffer.getvalue()


async def ensure_photo_face_crops(
    event_id: uuid.UUID,
    original_key: str,
    faces: list[tuple[uuid.UUID, dict, str | None]],
    storage: StorageService,
) -> dict[uuid.UUID, str]:
    """Vignettes de tous les visages d'une photo (bulles de la visionneuse) :
    celles qui manquent sont fabriquees en une fois (un seul telechargement de
    l'original). Renvoie {id du visage: cle} ; l'appelant memorise les cles
    nouvelles (FaceEmbedding.crop_key)."""
    keys = {face_id: key for face_id, _, key in faces if key}
    missing = [(face_id, bbox) for face_id, bbox, key in faces if not key]
    if not missing:
        return keys
    original = await storage.download(original_key)

    def _all() -> list[bytes]:
        return [_crop_bytes(original, bbox) for _, bbox in missing]

    crops = await asyncio.to_thread(_all)
    new_keys = [face_crop_key(event_id, face_id) for face_id, _ in missing]
    await asyncio.gather(*(storage.upload(k, c, "image/jpeg") for k, c in zip(new_keys, crops)))
    for (face_id, _), key in zip(missing, new_keys):
        keys[face_id] = key
    return keys


async def ensure_face_crop(
    face_embedding_id: uuid.UUID,
    event_id: uuid.UUID,
    original_key: str,
    bounding_box: dict,
    known_crop_key: str | None,
    storage: StorageService,
) -> str:
    """Renvoie la cle de la vignette du visage, en la generant si besoin.

    L'appelant memorise la cle renvoyee (FaceEmbedding.crop_key) quand elle
    n'etait pas encore connue."""
    if known_crop_key:
        return known_crop_key

    key = face_crop_key(event_id, face_embedding_id)
    # Vignettes generees avant l'ajout de crop_key : deja presentes dans le
    # stockage, il suffit de retrouver leur cle (une seule fois).
    if await storage.exists(key):
        return key

    original_bytes = await storage.download(original_key)
    crop_bytes = await asyncio.to_thread(_crop_bytes, original_bytes, bounding_box)
    await storage.upload(key, crop_bytes, "image/jpeg")
    return key
