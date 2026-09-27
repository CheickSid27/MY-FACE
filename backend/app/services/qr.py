"""Generation de QR code (lien de telechargement), aucun credential requis."""

import io

import qrcode


def generate_qr_png(data: str) -> bytes:
    img = qrcode.make(data)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
