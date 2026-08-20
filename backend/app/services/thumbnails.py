import io

from PIL import Image, UnidentifiedImageError

THUMBNAIL_MAX_SIZE = (400, 400)
THUMBNAIL_QUALITY = 80


class InvalidImageError(Exception):
    pass


def generate_thumbnail(image_bytes: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            img.thumbnail(THUMBNAIL_MAX_SIZE)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=THUMBNAIL_QUALITY)
            return buffer.getvalue()
    except UnidentifiedImageError as exc:
        raise InvalidImageError("Fichier image illisible ou format non supporte") from exc
