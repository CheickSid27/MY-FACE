"""Fichiers RAW d'appareil photo (CR2, CR3, NEF, ARW, DNG...).

Un telephone ne sait pas ouvrir un RAW : MYFACE garde le fichier RAW tel
quel (raw_key) et fabrique a cote un JPEG pleine resolution de tres bonne
qualite, qui sert d'« original » pour tout le reste (apercus, analyse des
visages, telechargement des invites).

On prend de preference le JPEG pleine taille que la plupart des appareils
embarquent deja dans le RAW (c'est le rendu de l'appareil, et c'est
instantane). S'il manque ou s'il est petit (certains Sony), le RAW est
developpe par LibRaw (rawpy) avec la balance des blancs de l'appareil.
"""

import io
import os

from PIL import Image

from app.services.thumbnails import InvalidImageError

RAW_EXTENSIONS = frozenset(
    {
        ".3fr", ".arw", ".cr2", ".cr3", ".dng", ".erf", ".iiq", ".kdc", ".mef", ".mos", ".mrw",
        ".nef", ".nrw", ".orf", ".pef", ".raf", ".raw", ".rw2", ".rwl", ".sr2", ".srf", ".srw", ".x3f",
    }
)

# Le JPEG embarque doit couvrir presque toute la taille du capteur pour etre
# garde tel quel (sinon on developpe le RAW, plus lent mais complet).
_EMBEDDED_MIN_RATIO = 0.9
JPEG_QUALITY = 95


def is_raw_filename(filename: str | None) -> bool:
    return os.path.splitext(filename or "")[1].lower() in RAW_EXTENSIONS


def raw_to_jpeg(data: bytes) -> bytes:
    """JPEG pleine resolution a partir d'un RAW. Calcul CPU : a appeler dans
    un thread. Leve InvalidImageError si le fichier n'est pas un RAW lisible."""
    import rawpy  # import tardif : bibliotheque native lourde

    try:
        with rawpy.imread(io.BytesIO(data)) as raw:
            sensor_width = max(raw.sizes.width, raw.sizes.height)
            try:
                thumb = raw.extract_thumb()
            except (rawpy.LibRawNoThumbnailError, rawpy.LibRawUnsupportedThumbnailError):
                thumb = None
            if thumb is not None and thumb.format == rawpy.ThumbFormat.JPEG:
                with Image.open(io.BytesIO(thumb.data)) as embedded:
                    if max(embedded.size) >= _EMBEDDED_MIN_RATIO * sensor_width:
                        return bytes(thumb.data)
            rgb = raw.postprocess(use_camera_wb=True, output_bps=8)
    except InvalidImageError:
        raise
    except Exception as exc:  # noqa: BLE001 - LibRaw leve des erreurs de types varies
        raise InvalidImageError("Fichier RAW illisible ou format d'appareil non pris en charge") from exc

    buffer = io.BytesIO()
    Image.fromarray(rgb).save(buffer, format="JPEG", quality=JPEG_QUALITY, subsampling=0, optimize=True)
    return buffer.getvalue()
