import io

from PIL import Image, UnidentifiedImageError

THUMBNAIL_MAX_SIZE = (400, 400)
THUMBNAIL_QUALITY = 80

# Format intermediaire pour la vue plein ecran/zoom (voir Photo.preview_key) :
# largement plus net que la miniature de grille, mais toujours pas
# l'original (reserve au post-achat) et assez leger pour charger vite meme
# en arriere-plan pendant que la miniature s'affiche deja.
PREVIEW_MAX_SIZE = (1600, 1600)
PREVIEW_QUALITY = 88


class InvalidImageError(Exception):
    pass


def _resize_jpeg(image_bytes: bytes, max_size: tuple[int, int], quality: int) -> bytes:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            img.thumbnail(max_size)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality)
            return buffer.getvalue()
    except UnidentifiedImageError as exc:
        raise InvalidImageError("Fichier image illisible ou format non supporte") from exc


def generate_thumbnail(image_bytes: bytes) -> bytes:
    return _resize_jpeg(image_bytes, THUMBNAIL_MAX_SIZE, THUMBNAIL_QUALITY)


def generate_preview(image_bytes: bytes) -> bytes:
    return _resize_jpeg(image_bytes, PREVIEW_MAX_SIZE, PREVIEW_QUALITY)
