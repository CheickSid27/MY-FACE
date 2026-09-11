"""Traitements d'image purs (sans base ni HTTP) : orientation, filigrane,
vignettes de visage."""

import io

from PIL import Image

from app.services.face_crops import _crop_bytes
from app.services.thumbnails import generate_preview, generate_thumbnail
from app.services.watermark import apply_watermark


def _portrait_phone_jpeg() -> bytes:
    """Pixels "couches" (paysage 1200x800) + tag EXIF Orientation=6 : une
    photo portrait, telle que l'enregistre un telephone tenu verticalement."""
    img = Image.new("RGB", (1200, 800), color=(200, 50, 50))
    # Marqueur dans le coin haut-gauche des pixels bruts : apres rotation
    # (Orientation=6, 90 degres horaire), il doit se retrouver en haut a droite.
    img.paste((0, 255, 0), (0, 0, 100, 100))
    exif = img.getexif()
    exif[274] = 6
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


def test_thumbnail_and_preview_apply_exif_orientation():
    for generate in (generate_thumbnail, generate_preview):
        width, height = Image.open(io.BytesIO(generate(_portrait_phone_jpeg()))).size
        assert height > width


def test_face_crop_uses_oriented_coordinates():
    # Boite exprimee dans le repere redresse (800x1200), comme la renvoie
    # InsightFace (OpenCV applique l'orientation EXIF) : zone du marqueur vert.
    crop = Image.open(io.BytesIO(_crop_bytes(_portrait_phone_jpeg(), {"x1": 710, "y1": 10, "x2": 790, "y2": 90})))
    r, g, _b = crop.convert("RGB").getpixel((crop.width // 2, crop.height // 2))
    assert g > 200 and r < 80


def test_watermark_keeps_size_and_changes_pixels():
    buffer = io.BytesIO()
    Image.new("RGB", (1600, 1067), color=(30, 60, 120)).save(buffer, format="JPEG", quality=95)
    original = buffer.getvalue()

    marked = Image.open(io.BytesIO(apply_watermark(original)))
    assert marked.size == (1600, 1067)
    # Le motif doit couvrir toute l'image, y compris les bords (impossible a
    # recadrer) : chaque quart contient des pixels eclaircis par le texte.
    base_lum = 30 * 0.299 + 60 * 0.587 + 120 * 0.114
    gray = marked.convert("L")
    for box in ((0, 0, 800, 533), (800, 0, 1600, 533), (0, 533, 800, 1067), (800, 533, 1600, 1067)):
        assert gray.crop(box).getextrema()[1] > base_lum + 25


def test_watermark_small_image():
    buffer = io.BytesIO()
    Image.new("RGB", (120, 80), color=(250, 250, 250)).save(buffer, format="JPEG")
    assert Image.open(io.BytesIO(apply_watermark(buffer.getvalue()))).size == (120, 80)
