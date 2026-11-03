# -*- coding: utf-8 -*-
"""Affiche MYFACE au format paysage (1600x925) pour la carte du portfolio.

Meme charte que les affiches (generer_affiches.py) : fond encre a points,
coins orange et vert, titres Arial Black. A droite, une photo de groupe de la
demonstration avec les vrais cadres de l'IA (visages_demo.json), et deux
telephones : le selfie, puis les photos retrouvees.

    python marketing/affiches/affiche_portfolio.py <sortie.webp>
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

INK = (14, 36, 41)
SAND = (244, 239, 230)
ORANGE = (242, 106, 27)
GREEN = (0, 133, 75)
WHITE = (255, 255, 255)
F_DISPLAY = "C:/Windows/Fonts/ariblk.ttf"
F_BODY = "C:/Windows/Fonts/segoeui.ttf"
F_BODY_B = "C:/Windows/Fonts/segoeuib.ttf"

ROOT = Path(__file__).resolve().parents[2]
PHOTO = ROOT / "watched-photos/6b3391d9-e2eb-4942-990b-ac1353cd170e/pexels-joshua-j-lewis-1577020288-27333356.jpg"
FACES = ROOT / "marketing/motion-design/v6/visages_demo.json"
LOGO = ROOT / "marketing/marque/myface-avatar-512.png"
SCREEN_SELFIE = ROOT / "marketing/captures/iphone/08-scan-camera.png"
SCREEN_RESULTS = ROOT / "marketing/captures/iphone/10-scan-resultats.png"

W, H = 1600, 925


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def corners(d: ImageDraw.ImageDraw, box, color, length, width, which="tl tr bl br"):
    x1, y1, x2, y2 = box
    if "tl" in which:
        d.line([(x1, y1 + length), (x1, y1), (x1 + length, y1)], fill=color, width=width)
    if "tr" in which:
        d.line([(x2 - length, y1), (x2, y1), (x2, y1 + length)], fill=color, width=width)
    if "bl" in which:
        d.line([(x1, y2 - length), (x1, y2), (x1 + length, y2)], fill=color, width=width)
    if "br" in which:
        d.line([(x2 - length, y2), (x2, y2), (x2, y2 - length)], fill=color, width=width)


def rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def phone(path: Path, height: int) -> Image.Image:
    shot = Image.open(path).convert("RGB")
    w = int(shot.width * height / shot.height)
    shot = rounded(shot.resize((w, height), Image.LANCZOS), height // 15)
    border = 9
    frame = Image.new("RGBA", (w + 2 * border, height + 2 * border), (0, 0, 0, 0))
    ImageDraw.Draw(frame).rounded_rectangle(
        (0, 0, frame.width - 1, frame.height - 1), radius=height // 15 + border, fill=(8, 12, 16, 255),
        outline=(70, 82, 88, 255), width=2,
    )
    frame.alpha_composite(shot, (border, border))
    return frame


def drop_shadow(canvas: Image.Image, img: Image.Image, pos, blur=26, offset=22, alpha=170):
    pad = blur * 3
    sh = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    sh.paste((0, 0, 0, alpha), (pad, pad), img.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(sh, (pos[0] - pad, pos[1] - pad + offset))
    canvas.alpha_composite(img, pos)


def main(out: str) -> None:
    canvas = Image.new("RGBA", (W, H), INK + (255,))
    d = ImageDraw.Draw(canvas)
    # trame de points, comme les affiches
    for y in range(18, H, 34):
        for x in range(18, W, 34):
            d.ellipse((x - 1.2, y - 1.2, x + 1.2, y + 1.2), fill=(32, 58, 63))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((880, 120, 1700, 900), fill=(242, 106, 27, 38))
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(140)))
    d = ImageDraw.Draw(canvas)
    corners(d, (34, 34, W - 34, H - 34), ORANGE, 70, 7, "tl tr bl")
    corners(d, (34, 34, W - 34, H - 34), GREEN, 70, 7, "br")

    # --- colonne de texte ---------------------------------------------------
    logo = Image.open(LOGO).convert("RGBA").resize((70, 70), Image.LANCZOS)
    canvas.alpha_composite(rounded(logo, 16), (86, 84))
    d.text((172, 92), "MY", font=font(F_DISPLAY, 40), fill=WHITE)
    d.text((172 + d.textlength("MY", font=font(F_DISPLAY, 40)), 92), "FACE", font=font(F_DISPLAY, 40), fill=ORANGE)

    title = font(F_DISPLAY, 86)
    y = 230
    for line in ("Ton visage", "suffit."):
        d.text((86, y), line, font=title, fill=WHITE)
        y += 104
    body = font(F_BODY, 29)
    y += 26
    for line in (
        "Notre IA de reconnaissance faciale retrouve",
        "chaque invité parmi des centaines de photos",
        "d'événement. Un selfie, et toutes les photos",
        "où il apparaît s'affichent en quelques secondes.",
    ):
        d.text((88, y), line, font=body, fill=SAND)
        y += 42
    y += 34
    chip_f = font(F_BODY_B, 24)
    x = 88
    for label in ("Mariages", "Remises de diplômes", "Soirées"):
        w = int(d.textlength(label, font=chip_f)) + 36
        d.rounded_rectangle((x, y, x + w, y + 46), radius=23, outline=(242, 106, 27), width=2)
        d.text((x + 18, y + 8), label, font=chip_f, fill=WHITE)
        x += w + 12
    d.text((88, H - 112), "Abidjan, Côte d'Ivoire  ·  myfaceci.online", font=font(F_BODY_B, 24), fill=(170, 190, 192))

    # --- photo de groupe avec les cadres de l'IA ------------------------------
    photo = Image.open(PHOTO).convert("RGB")
    faces = json.loads(FACES.read_text(encoding="utf-8"))[PHOTO.name]["visages"]
    pw, ph = 720, 480
    scale = max(pw / photo.width, ph / photo.height)
    small = photo.resize((int(photo.width * scale), int(photo.height * scale)), Image.LANCZOS)
    ox = (small.width - pw) // 2
    oy = int((small.height - ph) * 0.25)
    crop = small.crop((ox, oy, ox + pw, oy + ph)).convert("RGBA")
    cd = ImageDraw.Draw(crop)
    tag = font(F_BODY_B, 17)
    for face in faces:
        x1, y1 = face["x1"] * scale - ox, face["y1"] * scale - oy
        x2, y2 = face["x2"] * scale - ox, face["y2"] * scale - oy
        if x2 < 0 or x1 > pw or y2 < 0 or y1 > ph:
            continue
        corners(cd, (x1, y1, x2, y2), ORANGE, max(10, int((x2 - x1) * 0.28)), 4)
        label = f"{face['score']:.2f}"
        lw = cd.textlength(label, font=tag) + 12
        cd.rectangle((x1, y1 - 26, x1 + lw, y1 - 3), fill=ORANGE)
        cd.text((x1 + 6, y1 - 25), label, font=tag, fill=WHITE)
    photo_pos = (W - pw - 96, 92)
    drop_shadow(canvas, rounded(crop.convert("RGB"), 24), photo_pos)

    # --- deux telephones : le selfie, puis les photos retrouvees ---------------
    p1 = phone(SCREEN_SELFIE, 450).rotate(5, resample=Image.BICUBIC, expand=True)
    p2 = phone(SCREEN_RESULTS, 540).rotate(-4, resample=Image.BICUBIC, expand=True)
    drop_shadow(canvas, p1, (photo_pos[0] - 60, H - p1.height - 70))
    drop_shadow(canvas, p2, (photo_pos[0] + 260, H - p2.height - 52))

    canvas.convert("RGB").save(out, "WEBP", quality=88, method=6)
    print("ok", out)


if __name__ == "__main__":
    main(sys.argv[1])
