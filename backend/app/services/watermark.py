"""Filigrane des apercus grand format servis au telephone d'un invite.

L'apercu 1600px (Photo.preview_key) est assez net pour etre capture et
utilise sans jamais acheter la photo. Sur le telephone d'un invite, on sert
donc une copie filigranee (Photo.preview_watermarked_key) ; l'apercu net
reste reserve a la borne (verifiee cote serveur par le kiosk_token) et a
l'organisateur. Voir services/photo_urls.py pour le choix de la version.

Le filigrane est un motif diagonal repete, semi-transparent : visible sur
toute la surface (impossible a recadrer), mais assez discret pour que
l'invite juge encore la photo avant de l'acheter.
"""

import asyncio
import io
import logging
import math
from collections.abc import Callable
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo import Photo
from app.services.storage import StorageService
from app.services.thumbnails import generate_preview, open_oriented

logger = logging.getLogger("myface.watermark")

WATERMARK_TEXT = "MYFACE"
WATERMARK_QUALITY = 85
# Opacite (0-255) du texte blanc et de son contour sombre : le contour garde
# le motif lisible sur les zones claires (robe blanche, ciel...).
_TEXT_ALPHA = 70
_STROKE_ALPHA = 40
_ANGLE_DEGREES = 30
BACKFILL_CONCURRENCY = 4


def watermarked_preview_key(event_id, photo_id) -> str:
    return f"events/{event_id}/previews-wm/{photo_id}.jpg"


@lru_cache(maxsize=16)
def _font(size: int) -> ImageFont.FreeTypeFont:
    # Police vectorielle embarquee par Pillow (>= 10.1, FreeType) : aucune
    # police systeme n'est installee dans l'image Docker du backend.
    return ImageFont.load_default(size=size)


def apply_watermark(image_bytes: bytes, text: str = WATERMARK_TEXT) -> bytes:
    """Renvoie une copie JPEG de l'image avec le filigrane incruste."""
    base = open_oriented(image_bytes).convert("RGBA")
    width, height = base.size

    font_size = max(14, int(min(width, height) * 0.07))
    font = _font(font_size)
    label = text
    left, top, right, bottom = font.getbbox(label)
    # Espacement genereux entre les repetitions : le motif doit empecher la
    # reutilisation de la photo, pas empecher l'invite de se reconnaitre.
    step_x = max(1, int((right - left) * 1.9))
    step_y = max(1, int((bottom - top) * 4.6))

    # Motif dessine sur un calque carre couvrant la diagonale, puis tourne et
    # recadre aux dimensions de la photo : aucune zone n'echappe au motif,
    # quel que soit le format (portrait/paysage).
    diagonal = int(math.hypot(width, height)) + step_x
    layer = Image.new("RGBA", (diagonal, diagonal), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    stroke = max(1, font_size // 16)
    for row, y in enumerate(range(0, diagonal, step_y)):
        offset = (row % 2) * (step_x // 2)
        for x in range(-step_x, diagonal, step_x):
            draw.text(
                (x + offset, y),
                label,
                font=font,
                fill=(255, 255, 255, _TEXT_ALPHA),
                stroke_width=stroke,
                stroke_fill=(0, 0, 0, _STROKE_ALPHA),
            )

    layer = layer.rotate(_ANGLE_DEGREES, resample=Image.BICUBIC)
    crop_left = (diagonal - width) // 2
    crop_top = (diagonal - height) // 2
    layer = layer.crop((crop_left, crop_top, crop_left + width, crop_top + height))

    out = Image.alpha_composite(base, layer).convert("RGB")
    buffer = io.BytesIO()
    out.save(buffer, format="JPEG", quality=WATERMARK_QUALITY)
    return buffer.getvalue()


async def backfill_watermarks(
    storage: StorageService,
    session_factory: Callable[[], AsyncSession],
    on_event_updated: Callable[[object], None] | None = None,
) -> int:
    """Genere en tache de fond l'apercu filigrane (et l'apercu net s'il
    manque) des photos ingerees avant l'ajout de cette fonctionnalite. Tant
    qu'une photo n'a pas sa version filigranee, le telephone recoit la
    miniature 400px a la place (jamais l'apercu net, voir photo_urls.py).

    `on_event_updated(event_id)` est appele pour chaque evenement touche
    (invalidation du cache des groupes de visages, qui memorise les cles)."""
    async with session_factory() as db:
        result = await db.execute(
            select(Photo.id).where(or_(Photo.preview_watermarked_key.is_(None), Photo.preview_key.is_(None)))
        )
        photo_ids = [row[0] for row in result.all()]

    if not photo_ids:
        return 0
    logger.info("Filigrane : rattrapage de %d photo(s)", len(photo_ids))

    semaphore = asyncio.Semaphore(BACKFILL_CONCURRENCY)
    touched_events: set = set()
    done = 0

    async def _one(photo_id) -> None:
        nonlocal done
        async with semaphore:
            try:
                async with session_factory() as db:
                    photo = await db.get(Photo, photo_id)
                    if photo is None:
                        return
                    if photo.preview_key is None:
                        # Photos anterieures a l'ajout de preview_key : on
                        # genere l'apercu net depuis l'original au passage.
                        original = await storage.download(photo.original_key)
                        preview_bytes = await asyncio.to_thread(generate_preview, original)
                        preview_key = f"events/{photo.event_id}/previews/{photo.id}.jpg"
                        await storage.upload(preview_key, preview_bytes, "image/jpeg")
                        photo.preview_key = preview_key
                    else:
                        preview_bytes = await storage.download(photo.preview_key)

                    watermarked = await asyncio.to_thread(apply_watermark, preview_bytes)
                    wm_key = watermarked_preview_key(photo.event_id, photo.id)
                    await storage.upload(wm_key, watermarked, "image/jpeg")
                    photo.preview_watermarked_key = wm_key
                    await db.commit()
                    touched_events.add(photo.event_id)
                    done += 1
            except Exception:
                logger.exception("Filigrane : echec pour la photo %s", photo_id)

    await asyncio.gather(*(_one(pid) for pid in photo_ids))

    if on_event_updated is not None:
        for event_id in touched_events:
            on_event_updated(event_id)
    logger.info("Filigrane : %d/%d photo(s) rattrapee(s)", done, len(photo_ids))
    return done
