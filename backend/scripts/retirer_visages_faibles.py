"""Applique aux visages deja enregistres la regle de detection du 03/11 :
retire les « visages » trop incertains (confiance < FACE_DETECTION_MIN_CONFIDENCE :
voiles, mains, visages coupes, motifs) et les visages minuscules (largeur <
FACE_MIN_WIDTH_PX : personnes tout au fond, floues). Les PHOTOS ne sont pas
touchees : seule la case « visage » mal detectee (et sa vignette) est retiree.

Sans option : compte seulement, par evenement. Avec --appliquer : supprime.
Ensuite, redemarrer le backend (les groupes de « Trouver mon visage » sont
recalcules au demarrage et a chaque changement).

    docker exec -w /app -e PYTHONPATH=/app myface-backend-1 python3 scripts/retirer_visages_faibles.py
"""

import asyncio
import sys

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.event import Event
from app.models.face_embedding import FaceEmbedding
from app.models.photo import Photo
from app.services.face_crops import face_crop_key
from app.services.storage import get_storage_service

settings = get_settings()


def is_weak(confidence: float, box: dict) -> bool:
    width = float(box["x2"]) - float(box["x1"])
    return confidence < settings.face_detection_min_confidence or width < settings.face_min_width_px


async def main(apply: bool) -> None:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(FaceEmbedding.id, FaceEmbedding.confidence, FaceEmbedding.bounding_box, FaceEmbedding.crop_key,
                       Photo.event_id, Event.name)
                .join(Photo, Photo.id == FaceEmbedding.photo_id)
                .join(Event, Event.id == Photo.event_id)
            )
        ).all()
    weak = [r for r in rows if is_weak(r.confidence, r.bounding_box)]
    per_event: dict[str, int] = {}
    for r in weak:
        per_event[r.name] = per_event.get(r.name, 0) + 1
    print(f"Regle : confiance < {settings.face_detection_min_confidence} ou largeur < {settings.face_min_width_px} px")
    print(f"Visages a retirer : {len(weak)} sur {len(rows)}")
    for name, count in sorted(per_event.items(), key=lambda kv: -kv[1]):
        print(f"  {count:5d}  {name}")
    if not apply or not weak:
        return

    storage = get_storage_service()
    ids = [r.id for r in weak]
    async with AsyncSessionLocal() as db:
        for i in range(0, len(ids), 500):
            await db.execute(delete(FaceEmbedding).where(FaceEmbedding.id.in_(ids[i:i + 500])))
        await db.commit()
    limit = asyncio.Semaphore(16)

    async def drop(key: str) -> None:
        async with limit:
            try:
                await storage.delete(key)
            except Exception:  # noqa: BLE001
                pass

    await asyncio.gather(*(drop(r.crop_key or face_crop_key(r.event_id, r.id)) for r in weak))
    print(f"Supprimes : {len(weak)} visages et leurs vignettes")


if __name__ == "__main__":
    asyncio.run(main("--appliquer" in sys.argv))
