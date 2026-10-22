"""Photo de profil des comptes (photographes, equipe MYFACE).

Recadree au centre en carre de 512 px et reenregistree en JPEG : quelle que
soit la photo envoyee (grande, verticale, PNG...), le fichier garde est
leger et ne contient plus les donnees EXIF (lieu de prise de vue, appareil).
"""

import io
import secrets
import uuid

from PIL import Image

from app.services.thumbnails import InvalidImageError, open_oriented

AVATAR_SIZE = 512
AVATAR_MAX_BYTES = 8 * 1024 * 1024
AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def avatar_key(user_id: uuid.UUID) -> str:
    # Partie aleatoire : chaque nouvelle photo a une adresse differente, le
    # navigateur peut garder l'ancienne en cache sans jamais la remontrer.
    return f"users/{user_id}/avatar-{secrets.token_hex(6)}.jpg"


def make_avatar(image_bytes: bytes) -> bytes:
    """Carre 512 x 512 recadre au centre, en JPEG. Calcul CPU : dans un thread."""
    try:
        img = open_oriented(image_bytes).convert("RGB")
    except InvalidImageError:
        raise
    except Exception as exc:  # noqa: BLE001 - Pillow leve des erreurs variees
        raise InvalidImageError("Image illisible") from exc
    side = min(img.size)
    left = (img.width - side) // 2
    top = (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=88, optimize=True)
    return buffer.getvalue()
