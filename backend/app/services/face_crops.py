"""Genere une vignette recadree sur un visage (pas la photo entiere), pour
que l'admin identifie qui est qui d'un coup d'oeil dans la vue "personnes
detectees" (groupage par similarite). Le crop est mis en cache dans le
stockage (cle deterministe = id du FaceEmbedding) : calcule une seule fois,
reutilise ensuite meme si les clusters sont recalcules (DBSCAN n'est pas
persiste, seuls les embeddings le sont)."""

import io
import uuid

from PIL import Image

from app.models.face_embedding import FaceEmbedding
from app.models.photo import Photo
from app.services.storage import StorageService

CROP_SIZE = (320, 320)
CROP_QUALITY = 85
# Marge autour de la boite de detection (trop serree sur InsightFace, qui
# cadre au ras des traits) pour obtenir un cadrage "portrait" plus naturel.
PADDING_RATIO = 0.6


def _face_crop_key(event_id: uuid.UUID, face_embedding_id: uuid.UUID) -> str:
    return f"events/{event_id}/face-crops/{face_embedding_id}.jpg"


def _crop_bytes(image_bytes: bytes, bbox: dict) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
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


async def get_or_create_face_crop_url(
    face_embedding: FaceEmbedding, photo: Photo, storage: StorageService, expires_in: int = 3600
) -> str:
    key = _face_crop_key(photo.event_id, face_embedding.id)

    if not await storage.exists(key):
        original_bytes = await storage.download(photo.original_key)
        crop_bytes = _crop_bytes(original_bytes, face_embedding.bounding_box)
        await storage.upload(key, crop_bytes, "image/jpeg")

    return await storage.get_presigned_url(key, expires_in=expires_in)
