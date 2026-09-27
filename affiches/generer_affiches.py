# -*- coding: utf-8 -*-
"""Generateur des affiches MYFACE.

Un seul fichier, aucune dependance à installer a part Pillow. Chaque affiche
est decrite comme une pile de blocs (logo, titre, texte, etapes, prix,
téléphone, borne, imprimante, QR...) et le rendu la centre verticalement.
La meme description sort en trois formats : publication 1080x1350, story
1080x1920 et affiche A4 en 300 dpi.

    python generer_affiches.py

Pour modifier un texte : cherchez le nom de l'affiche plus bas (AFFICHES) et
changez la chaine. Les couleurs et les polices sont tout en haut.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --------------------------------------------------------------------------
# Marque
# --------------------------------------------------------------------------
INK = (14, 36, 41)
SAND = (244, 239, 230)
ORANGE = (242, 106, 27)
GREEN = (0, 133, 75)
WHITE = (255, 255, 255)

F_DISPLAY = "C:/Windows/Fonts/ariblk.ttf"   # titres (remplace Unbounded)
F_BODY = "C:/Windows/Fonts/segoeui.ttf"
F_BODY_B = "C:/Windows/Fonts/segoeuib.ttf"
F_NUM = "C:/Windows/Fonts/arialbd.ttf"

FORMATS = {
    "post": (1080, 1350),
    "story": (1080, 1920),
    "a4": (2480, 3508),
}

# Largeur du téléphone, en part de la largeur de l'affiche (iPhone 17 : 1179x2556)
PHONE_RATIO = 0.30

BASE = Path(__file__).resolve().parent
SOURCES = BASE / "sources"

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, max(8, int(size)))
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, key[1])
    return _font_cache[key]


# --------------------------------------------------------------------------
# Outils de texte
# --------------------------------------------------------------------------
def text_h(d: ImageDraw.ImageDraw, txt: str, f) -> int:
    box = d.textbbox((0, 0), txt or "A", font=f)
    return box[3] - box[1]


def text_w(d: ImageDraw.ImageDraw, txt: str, f) -> int:
    box = d.textbbox((0, 0), txt, font=f)
    return box[2] - box[0]


def wrap(d: ImageDraw.ImageDraw, txt: str, f, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in txt.split("\n"):
        if not para:
            lines.append("")
            continue
        cur = ""
        for word in para.split(" "):
            essai = f"{cur} {word}".strip()
            if text_w(d, essai, f) <= max_w or not cur:
                cur = essai
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def draw_lines(d, x, y, lines, f, fill, lh, align="left", width=0):
    for line in lines:
        if line:
            dx = 0
            if align == "center":
                dx = (width - text_w(d, line, f)) // 2
            d.text((x + dx, y), line, font=f, fill=fill)
        y += lh
    return y


# --------------------------------------------------------------------------
# Le logo, dessine (meme geometrie que components/brand/Logo.tsx)
# --------------------------------------------------------------------------
def logo_icone(size: int, plate=INK, face=SAND) -> Image.Image:
    s = 4
    n = size * s
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = n / 512.0

    def P(v):
        return v * u

    d.rounded_rectangle([0, 0, n - 1, n - 1], radius=P(116), fill=plate)
    x0, y0, x1, y1, arm, w = 120, 124, 392, 396, 66, 26

    def seg(a, b, col):
        d.line([P(a[0]), P(a[1]), P(b[0]), P(b[1])], fill=col, width=int(P(w)))
        for (px_, py_) in (a, b):
            r = P(w) / 2
            d.ellipse([P(px_) - r, P(py_) - r, P(px_) + r, P(py_) + r], fill=col)

    for a, b in [((x0, y0 + arm), (x0, y0)), ((x0, y0), (x0 + arm, y0)),
                 ((x1 - arm, y0), (x1, y0)), ((x1, y0), (x1, y0 + arm)),
                 ((x0 + arm, y1), (x0, y1)), ((x0, y1), (x0, y1 - arm))]:
        seg(a, b, ORANGE)
    seg((x1, y1 - arm), (x1, y1), GREEN)
    seg((x1, y1), (x1 - arm, y1), GREEN)

    for cx in (208, 304):
        r = P(15)
        d.ellipse([P(cx) - r, P(226) - r, P(cx) + r, P(226) + r], fill=face)

    import math
    pts = [(256 + 68.3 * math.cos(math.radians(a)), 237.7 + 68.3 * math.sin(math.radians(a)))
           for a in [40 + 100 * i / 24 for i in range(25)]]
    for a, b in zip(pts, pts[1:]):
        seg(a, b, face)

    return img.resize((size, size), Image.LANCZOS)


# --------------------------------------------------------------------------
# Blocs
# --------------------------------------------------------------------------
def b_logo(ratio=0.075, tone="auto"):
    return {"t": "logo", "ratio": ratio, "tone": tone}


def b_title(txt, ratio=0.098, color=None, align="left"):
    return {"t": "title", "txt": txt, "ratio": ratio, "color": color, "align": align}


def b_body(txt, ratio=0.036, color=None, align="left", bold=False):
    return {"t": "body", "txt": txt, "ratio": ratio, "color": color, "align": align, "bold": bold}


def b_steps(items, ratio=0.034):
    return {"t": "steps", "items": items, "ratio": ratio}


def b_bullets(items, ratio=0.036):
    return {"t": "bullets", "items": items, "ratio": ratio}


def b_prices(rows, ratio=0.038):
    return {"t": "prices", "rows": rows, "ratio": ratio}


def b_chips(items, ratio=0.03):
    return {"t": "chips", "items": items, "ratio": ratio}


def b_image(fichier, ratio=0.55, tirage=False):
    """Un visuel prepare (sources/borne.png, sources/telephone.png).

    `ratio` = hauteur de l'image, en part de la largeur de l'affiche.
    `tirage` ajoute une photo qui sort de la fente d'impression de la borne.
    """
    return {"t": "image", "fichier": fichier, "ratio": ratio, "tirage": tirage}


def b_ecrans(items, ratio=0.5):
    """Une suite d'ecrans de l'application, numerotes : montre que le
    parcours est court. items = [(fichier, legende), ...]"""
    return {"t": "ecrans", "items": items, "ratio": ratio}


def b_phone():
    return {"t": "phone"}


def b_kiosk():
    return {"t": "kiosk"}


def b_printer():
    return {"t": "printer"}


def b_grid():
    return {"t": "grid"}


def b_beforeafter():
    return {"t": "beforeafter"}


def b_qr(fichier, legende=""):
    return {"t": "qr", "fichier": fichier, "legende": legende}


def b_date(jour, mois):
    return {"t": "date", "jour": jour, "mois": mois}


def b_gap(ratio=0.03):
    return {"t": "gap", "ratio": ratio}


def b_spacer():
    return {"t": "spacer"}


def b_rule():
    return {"t": "rule"}


# --------------------------------------------------------------------------
# Mesure et rendu des blocs
# --------------------------------------------------------------------------
def mesure(d, bloc, W, CW):
    t = bloc["t"]
    if t == "gap":
        return int(bloc["ratio"] * W)
    if t == "spacer":
        return 0
    if t == "rule":
        return max(2, int(0.004 * W))
    if t == "logo":
        return int(bloc["ratio"] * W)
    if t == "title":
        f = font(F_DISPLAY, int(bloc["ratio"] * W))
        lines = wrap(d, bloc["txt"], f, CW)
        return int(len(lines) * bloc["ratio"] * W * 1.06)
    if t == "body":
        f = font(F_BODY_B if bloc["bold"] else F_BODY, int(bloc["ratio"] * W))
        lines = wrap(d, bloc["txt"], f, CW)
        return int(len(lines) * bloc["ratio"] * W * 1.42)
    if t == "steps":
        h = 0
        for _titre, desc in bloc["items"]:
            fb = font(F_BODY, int(bloc["ratio"] * W))
            h += int(bloc["ratio"] * W * 1.25)
            h += len(wrap(d, desc, fb, CW - int(0.11 * W))) * int(bloc["ratio"] * W * 1.3)
            h += int(0.028 * W)
        return h
    if t == "bullets":
        h = 0
        f = font(F_BODY, int(bloc["ratio"] * W))
        for it in bloc["items"]:
            h += len(wrap(d, it, f, CW - int(0.055 * W))) * int(bloc["ratio"] * W * 1.42)
            h += int(0.016 * W)
        return h
    if t == "prices":
        return len(bloc["rows"]) * int(bloc["ratio"] * W * 1.95)
    if t == "chips":
        return int(bloc["ratio"] * W * 2.4)
    if t == "image":
        h = int(bloc["ratio"] * W)
        return h + (int(0.1 * W) if bloc["tirage"] else 0)
    if t == "ecrans":
        n = len(bloc["items"])
        gap = int(0.016 * W)
        cell = (CW - gap * (n - 1)) // n
        f = font(F_BODY, int(0.022 * W))
        lignes = max(len(wrap(d, leg, f, cell)) for _, leg in bloc["items"])
        return int(cell / 0.4615) + int(0.05 * W) + lignes * int(0.032 * W)
    if t == "phone":
        pw = PHONE_RATIO * W
        return int(pw / 0.4613)
    if t == "kiosk":
        return int(0.44 * W)
    if t == "printer":
        return int(0.48 * W)
    if t == "grid":
        return int(0.58 * W)
    if t == "beforeafter":
        return int(0.52 * W)
    if t == "qr":
        h = int(0.34 * W)
        if bloc["legende"]:
            h += int(0.055 * W)
        return h
    if t == "date":
        return int(0.2 * W)
    return 0


def dessine(img, d, bloc, x, y, W, CW, fg, bg_dark):
    t = bloc["t"]
    if t in ("gap", "spacer"):
        return
    if t == "rule":
        d.rectangle([x, y, x + int(0.18 * W), y + max(2, int(0.004 * W))], fill=ORANGE)
        return
    if t == "logo":
        size = int(bloc["ratio"] * W)
        ic = logo_icone(size, plate=SAND if bg_dark else INK, face=INK if bg_dark else SAND)
        img.paste(ic, (x, y), ic)
        f = font(F_DISPLAY, int(size * 0.62))
        tx = x + int(size * 1.28)
        ty = y + (size - text_h(d, "MYFACE", f)) // 2 - int(size * 0.07)
        d.text((tx, ty), "MY", font=f, fill=fg)
        d.text((tx + text_w(d, "MY", f), ty), "FACE", font=f, fill=ORANGE)
        return
    if t == "title":
        f = font(F_DISPLAY, int(bloc["ratio"] * W))
        col = bloc["color"] or fg
        lines = wrap(d, bloc["txt"], f, CW)
        draw_lines(d, x, y, lines, f, col, int(bloc["ratio"] * W * 1.06), bloc["align"], CW)
        return
    if t == "body":
        f = font(F_BODY_B if bloc["bold"] else F_BODY, int(bloc["ratio"] * W))
        col = bloc["color"] or (SAND if bg_dark else (51, 72, 77))
        lines = wrap(d, bloc["txt"], f, CW)
        draw_lines(d, x, y, lines, f, col, int(bloc["ratio"] * W * 1.42), bloc["align"], CW)
        return
    if t == "steps":
        s = bloc["ratio"] * W
        fn = font(F_DISPLAY, int(s * 1.15))
        ft = font(F_BODY_B, int(s))
        fb = font(F_BODY, int(s * 0.94))
        for i, (titre, desc) in enumerate(bloc["items"], start=1):
            d.text((x, y - int(s * 0.12)), str(i), font=fn, fill=ORANGE)
            d.text((x + int(0.075 * W), y), titre, font=ft, fill=fg)
            yy = y + int(s * 1.25)
            col = SAND if bg_dark else (94, 115, 120)
            yy = draw_lines(d, x + int(0.075 * W), yy,
                            wrap(d, desc, fb, CW - int(0.11 * W)), fb, col, int(s * 1.3))
            y = yy + int(0.028 * W)
        return
    if t == "bullets":
        s = bloc["ratio"] * W
        f = font(F_BODY, int(s))
        col = SAND if bg_dark else (51, 72, 77)
        for it in bloc["items"]:
            r = int(s * 0.16)
            d.ellipse([x, y + int(s * 0.5), x + r * 2, y + int(s * 0.5) + r * 2], fill=ORANGE)
            y = draw_lines(d, x + int(0.055 * W), y,
                           wrap(d, it, f, CW - int(0.055 * W)), f, col, int(s * 1.42))
            y += int(0.016 * W)
        return
    if t == "prices":
        s = bloc["ratio"] * W
        fl = font(F_BODY, int(s))
        fv = font(F_NUM, int(s * 1.12))
        for label, valeur in bloc["rows"]:
            d.text((x, y), label, font=fl, fill=SAND if bg_dark else (51, 72, 77))
            vw = text_w(d, valeur, fv)
            d.text((x + CW - vw, y - int(s * 0.08)), valeur, font=fv, fill=fg)
            ligne_y = y + int(s * 1.5)
            pas = int(0.018 * W)
            xx = x
            col = (SAND[0], SAND[1], SAND[2]) if bg_dark else (216, 206, 190)
            while xx < x + CW:
                d.rectangle([xx, ligne_y, xx + pas // 2, ligne_y + max(1, int(0.002 * W))],
                            fill=col if not bg_dark else (60, 80, 84))
                xx += pas
            y += int(s * 1.95)
        return
    if t == "chips":
        s = bloc["ratio"] * W
        f = font(F_BODY_B, int(s))
        xx, yy = x, y
        h = int(s * 2.0)
        for it in bloc["items"]:
            w = text_w(d, it, f) + int(s * 1.5)
            if xx + w > x + CW:
                xx = x
                yy += h + int(s * 0.45)
            d.rounded_rectangle([xx, yy, xx + w, yy + h], radius=h // 2,
                                fill=None, outline=ORANGE, width=max(2, int(0.004 * W)))
            d.text((xx + int(s * 0.75), yy + (h - text_h(d, it, f)) // 2 - int(s * 0.18)),
                   it, font=f, fill=fg)
            xx += w + int(s * 0.45)
        return
    if t == "image":
        visuel(img, d, bloc, x, y, W, CW)
        return
    if t == "ecrans":
        suite_ecrans(img, d, bloc, x, y, W, CW, fg, bg_dark)
        return
    if t == "phone":
        phone_iphone17(img, d, x, y, W, CW)
        return
    if t == "kiosk":
        borne(img, d, x, y, W, CW, bg_dark)
        return
    if t == "printer":
        imprimante(img, d, x, y, W, CW, bg_dark)
        return
    if t == "grid":
        grille(d, x, y, W, CW)
        return
    if t == "beforeafter":
        avant_apres(d, x, y, W, CW, bg_dark)
        return
    if t == "qr":
        size = int(0.34 * W)
        qr = Image.open(SOURCES / bloc["fichier"]).convert("RGB").resize((size, size), Image.NEAREST)
        cadre = int(0.022 * W)
        d.rounded_rectangle([x + (CW - size) // 2 - cadre, y - cadre,
                             x + (CW - size) // 2 + size + cadre, y + size + cadre],
                            radius=int(0.02 * W), fill=WHITE)
        img.paste(qr, (x + (CW - size) // 2, y))
        if bloc["legende"]:
            f = font(F_BODY_B, int(0.028 * W))
            draw_lines(d, x, y + size + int(0.03 * W), wrap(d, bloc["legende"], f, CW), f,
                       SAND if bg_dark else (94, 115, 120), int(0.04 * W), "center", CW)
        return
    if t == "date":
        s = int(0.2 * W)
        w = int(0.42 * W)
        d.rounded_rectangle([x, y, x + w, y + s], radius=int(0.03 * W), fill=ORANGE)
        fj = font(F_DISPLAY, int(0.115 * W))
        fm = font(F_BODY_B, int(0.032 * W))
        jour, mois = bloc["jour"], bloc["mois"]
        d.text((x + (w - text_w(d, jour, fj)) // 2, y + int(0.022 * W)), jour, font=fj, fill=WHITE)
        d.text((x + (w - text_w(d, mois, fm)) // 2, y + int(0.145 * W)), mois.upper(), font=fm, fill=WHITE)
        return


# --------------------------------------------------------------------------
# Illustrations
# --------------------------------------------------------------------------

def photo_synthetique(taille: int, graine: int = 0) -> Image.Image:
    """Fausse photo de soiree, dessinee : degrade, silhouettes, halos.

    Sert a illustrer les affiches sans utiliser la photo de quelqu'un. Le
    rendu est volontairement flou et sombre : on doit y lire "photo de fete",
    pas reconnaitre un visage.
    """
    import math
    im = Image.new("RGB", (taille, taille))
    d = ImageDraw.Draw(im, "RGBA")
    palettes = [((38, 52, 66), (96, 74, 58)), ((46, 40, 58), (120, 82, 52)),
                ((30, 54, 52), (86, 96, 62)), ((52, 44, 40), (128, 96, 64)),
                ((34, 46, 62), (110, 88, 70)), ((44, 52, 48), (96, 104, 70))]
    haut, bas = palettes[graine % len(palettes)]
    for k in range(taille):
        f = k / max(1, taille)
        d.line([0, k, taille, k],
               fill=tuple(int(haut[j] + (bas[j] - haut[j]) * f) for j in range(3)))

    # halos lumineux (guirlandes, projecteurs)
    for i in range(5):
        a = (graine * 37 + i * 61) % 100 / 100
        b = (graine * 53 + i * 29) % 100 / 100
        r = int(taille * (0.05 + 0.05 * ((graine + i) % 3)))
        cx, cy = int(a * taille), int(b * taille * 0.55)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 206, 140, 42))

    # silhouettes : epaules + tete, jamais de traits du visage
    nb = 2 + graine % 2
    for i in range(nb):
        pos = 0.22 + 0.34 * i + 0.06 * math.sin(graine + i)
        cx = int(pos * taille)
        larg = int(taille * 0.3)
        haut_ep = int(taille * (0.58 + 0.05 * ((graine + i) % 2)))
        d.ellipse([cx - larg // 2, haut_ep, cx + larg // 2, taille + larg // 2],
                  fill=(16, 24, 30, 235))
        rt = int(taille * 0.1)
        d.ellipse([cx - rt, haut_ep - int(rt * 1.9), cx + rt, haut_ep + int(rt * 0.1)],
                  fill=(16, 24, 30, 235))

    return im.filter(__import__("PIL.ImageFilter", fromlist=["ImageFilter"]).GaussianBlur(taille * 0.004))


def suite_ecrans(img, d, bloc, x, y, W, CW, fg, bg_dark):
    """Les ecrans cote a cote, dans un cadre sombre, avec leur numero."""
    items = bloc["items"]
    n = len(items)
    gap = int(0.016 * W)
    cell = (CW - gap * (n - 1)) // n
    bord = max(3, int(cell * 0.035))
    ecr_w = cell - 2 * bord
    ecr_h = int(ecr_w / 0.4615)
    fleg = font(F_BODY, int(0.022 * W))
    fnum = font(F_DISPLAY, int(0.03 * W))

    for i, (fichier, legende) in enumerate(items):
        cx = x + i * (cell + gap)
        # chassis
        d.rounded_rectangle([cx, y, cx + cell, y + ecr_h + 2 * bord],
                            radius=int(cell * 0.12), fill=(22, 26, 28))
        src = Image.open(SOURCES / fichier).convert("RGB").resize((ecr_w, ecr_h), Image.LANCZOS)
        masque = Image.new("L", (ecr_w, ecr_h), 0)
        ImageDraw.Draw(masque).rounded_rectangle([0, 0, ecr_w - 1, ecr_h - 1],
                                                 radius=int(cell * 0.09), fill=255)
        img.paste(src, (cx + bord, y + bord), masque)

        # numero, sur l'angle
        r = int(0.026 * W)
        bx, by = cx + cell - r, y + r // 2
        d.ellipse([bx - r, by - r, bx + r, by + r], fill=ORANGE)
        num = str(i + 1)
        d.text((bx - text_w(d, num, fnum) // 2, by - int(0.021 * W)), num, font=fnum, fill=(255, 255, 255))

        # legende
        ly = y + ecr_h + 2 * bord + int(0.022 * W)
        draw_lines(d, cx, ly, wrap(d, legende, fleg, cell), fleg,
                   SAND if bg_dark else (51, 72, 77), int(0.032 * W), "left", cell)


def visuel(img, d, bloc, x, y, W, CW):
    """Pose une image preparee, centree, et eventuellement le tirage papier."""
    src = Image.open(SOURCES / bloc["fichier"]).convert("RGBA")
    h = int(bloc["ratio"] * W)
    w = int(src.width * h / src.height)
    if w > CW:
        w, h = CW, int(src.height * CW / src.width)
    src = src.resize((w, h), Image.LANCZOS)
    px_ = x + (CW - w) // 2
    img.alpha_composite(src, (px_, y))

    if bloc["tirage"]:
        # la fente d'impression de la borne, en proportions de l'image
        fx = px_ + int(w * 0.24)
        fy = y + int(h * 0.71)
        tw = int(w * 0.34)
        th = int(tw * 1.32)
        photo = Image.new("RGBA", (tw, th), (255, 255, 255, 255))
        marge = max(2, int(tw * 0.07))
        vign = photo_synthetique(tw - 2 * marge, graine=5).resize((tw - 2 * marge, th - 2 * marge))
        photo.paste(vign, (marge, marge))
        pd = ImageDraw.Draw(photo)
        pd.rectangle([0, 0, tw - 1, th - 1], outline=(214, 208, 198, 255), width=max(1, int(tw * 0.02)))
        photo = photo.rotate(-5, expand=True, resample=Image.BICUBIC)
        ombre = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(ombre).rectangle([fx + 6, fy + 10, fx + photo.width + 6, fy + photo.height + 10],
                                        fill=(0, 0, 0, 55))
        img.alpha_composite(ombre.filter(ImageFilter.GaussianBlur(int(W * 0.012))))
        img.alpha_composite(photo, (fx, fy))


def phone_iphone17(img, d, x, y, W, CW):
    """iPhone 17 : coins tres arrondis, bords fins, Dynamic Island."""
    pw = int(PHONE_RATIO * W)
    ph = int(pw / 0.4613)
    px_ = x + (CW - pw) // 2
    rad = int(pw * 0.125)

    # ombre douce
    ombre = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ombre)
    od.rounded_rectangle([px_ + int(pw * 0.03), y + int(pw * 0.05),
                          px_ + pw + int(pw * 0.03), y + ph + int(pw * 0.05)],
                         radius=rad, fill=(0, 0, 0, 70))
    img.alpha_composite(ombre.filter(__import__("PIL.ImageFilter", fromlist=["ImageFilter"]).GaussianBlur(int(pw * 0.05))))

    # chassis
    d.rounded_rectangle([px_, y, px_ + pw, y + ph], radius=rad, fill=(28, 30, 32))
    bord = max(3, int(pw * 0.022))
    sx0, sy0 = px_ + bord, y + bord
    sx1, sy1 = px_ + pw - bord, y + ph - bord
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=rad - bord, fill=(9, 22, 26))

    sw = sx1 - sx0
    pad = int(sw * 0.055)

    # barre d'etat
    fs = font(F_BODY_B, int(sw * 0.075))
    d.text((sx0 + pad, sy0 + int(sw * 0.055)), "20:24", font=fs, fill=SAND)
    bx = sx1 - pad
    for i, hh in enumerate([0.028, 0.038, 0.048, 0.058]):
        h = int(sw * hh)
        bw = int(sw * 0.016)
        d.rounded_rectangle([bx - bw, sy0 + int(sw * 0.1) - h, bx, sy0 + int(sw * 0.1)],
                            radius=bw // 3, fill=SAND)
        bx -= int(bw * 1.7)
    d.rounded_rectangle([bx - int(sw * 0.075), sy0 + int(sw * 0.052),
                         bx - int(sw * 0.012), sy0 + int(sw * 0.098)],
                        radius=int(sw * 0.012), outline=SAND, width=max(2, int(sw * 0.006)))

    # Dynamic Island
    iw, ih = int(sw * 0.33), int(sw * 0.098)
    ix = sx0 + (sw - iw) // 2
    iy = sy0 + int(sw * 0.038)
    d.rounded_rectangle([ix, iy, ix + iw, iy + ih], radius=ih // 2, fill=(0, 0, 0))
    r = int(ih * 0.26)
    cx = ix + iw - int(ih * 0.55)
    cy = iy + ih // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(16, 26, 34))

    # en-tete de l'app
    ft = font(F_BODY_B, int(sw * 0.082))
    fsub = font(F_BODY, int(sw * 0.055))
    ty = sy0 + int(sw * 0.2)
    d.text((sx0 + pad, ty), "Mes photos", font=ft, fill=SAND)
    d.text((sx0 + pad, ty + int(sw * 0.115)), "14 photos trouvées", font=fsub, fill=(150, 170, 175))

    # grille de vignettes
    gy = ty + int(sw * 0.21)
    cols, gap = 3, int(sw * 0.022)
    tile = (sw - 2 * pad - gap * (cols - 1)) // cols
    for i in range(9):
        r_, c_ = divmod(i, cols)
        tx = sx0 + pad + c_ * (tile + gap)
        tyy = gy + r_ * (tile + gap)
        vign = photo_synthetique(tile, graine=i + 1)
        masque = Image.new("L", (tile, tile), 0)
        ImageDraw.Draw(masque).rounded_rectangle([0, 0, tile - 1, tile - 1],
                                                 radius=int(tile * 0.12), fill=255)
        img.paste(vign, (tx, tyy), masque)
        if i in (1, 4, 6):
            m = int(tile * 0.16)
            d.rounded_rectangle([tx + m, tyy + m, tx + tile - m, tyy + tile - m],
                                radius=int(tile * 0.06), outline=ORANGE, width=max(2, int(tile * 0.045)))

    # bouton principal
    by = gy + 3 * (tile + gap) + int(sw * 0.05)
    bh = int(sw * 0.14)
    d.rounded_rectangle([sx0 + pad, by, sx1 - pad, by + bh], radius=bh // 2, fill=ORANGE)
    fb = font(F_BODY_B, int(sw * 0.062))
    lbl = "Télécharger mes photos"
    d.text((sx0 + (sw - text_w(d, lbl, fb)) // 2, by + (bh - text_h(d, lbl, fb)) // 2 - int(sw * 0.012)),
           lbl, font=fb, fill=WHITE)

    # ligne panier + barre d'accueil, pour que l'ecran ne paraisse pas vide
    fp = font(F_BODY, int(sw * 0.055))
    panier = "Panier · 3 photos · 2 100 F"
    d.text((sx0 + (sw - text_w(d, panier, fp)) // 2, by + bh + int(sw * 0.055)),
           panier, font=fp, fill=(150, 170, 175))
    hw = int(sw * 0.34)
    hh = max(3, int(sw * 0.011))
    d.rounded_rectangle([sx0 + (sw - hw) // 2, sy1 - int(sw * 0.045),
                         sx0 + (sw + hw) // 2, sy1 - int(sw * 0.045) + hh],
                        radius=hh // 2, fill=(120, 140, 145))


def borne(img, d, x, y, W, CW, bg_dark):
    """Borne : ecran sur pied, cadre de detection a l'ecran."""
    ew = int(0.42 * W)
    eh = int(ew * 0.72)
    ex = x + (CW - ew) // 2
    d.rounded_rectangle([ex, y, ex + ew, y + eh], radius=int(0.02 * W), fill=(46, 64, 68))
    b = int(0.016 * W)
    d.rounded_rectangle([ex + b, y + b, ex + ew - b, y + eh - b], radius=int(0.014 * W), fill=INK)

    # cadre de detection + visage sur l'ecran
    cw = int(ew * 0.34)
    cx0 = ex + (ew - cw) // 2
    cy0 = y + int(eh * 0.2)
    arm = int(cw * 0.3)
    lw = max(3, int(0.007 * W))
    for (a, bb, col) in [((cx0, cy0 + arm), (cx0, cy0), ORANGE), ((cx0, cy0), (cx0 + arm, cy0), ORANGE),
                         ((cx0 + cw - arm, cy0), (cx0 + cw, cy0), ORANGE), ((cx0 + cw, cy0), (cx0 + cw, cy0 + arm), ORANGE),
                         ((cx0, cy0 + cw - arm), (cx0, cy0 + cw), ORANGE), ((cx0, cy0 + cw), (cx0 + arm, cy0 + cw), ORANGE),
                         ((cx0 + cw, cy0 + cw - arm), (cx0 + cw, cy0 + cw), GREEN), ((cx0 + cw, cy0 + cw), (cx0 + cw - arm, cy0 + cw), GREEN)]:
        d.line([a[0], a[1], bb[0], bb[1]], fill=col, width=lw)
    r = int(cw * 0.06)
    for ox in (0.32, 0.68):
        d.ellipse([cx0 + int(cw * ox) - r, cy0 + int(cw * 0.38) - r,
                   cx0 + int(cw * ox) + r, cy0 + int(cw * 0.38) + r], fill=SAND)
    d.arc([cx0 + int(cw * 0.26), cy0 + int(cw * 0.42), cx0 + int(cw * 0.74), cy0 + int(cw * 0.82)],
          start=20, end=160, fill=SAND, width=max(3, int(cw * 0.06)))

    f = font(F_BODY_B, int(0.03 * W))
    lbl = "Touchez pour commencer"
    d.text((ex + (ew - text_w(d, lbl, f)) // 2, y + int(eh * 0.78)), lbl, font=f, fill=(150, 170, 175))

    # pied et socle
    pw = int(ew * 0.12)
    d.rectangle([ex + (ew - pw) // 2, y + eh, ex + (ew + pw) // 2, y + int(0.39 * W)], fill=(46, 64, 68))
    sw = int(ew * 0.5)
    d.rounded_rectangle([ex + (ew - sw) // 2, y + int(0.39 * W), ex + (ew + sw) // 2, y + int(0.43 * W)],
                        radius=int(0.012 * W), fill=(46, 64, 68))


def imprimante(img, d, x, y, W, CW, bg_dark):
    """Imprimante photo avec un tirage qui sort."""
    pw = int(0.42 * W)
    ph = int(pw * 0.52)
    px_ = x + (CW - pw) // 2
    top = y + int(0.26 * W)

    # tirage qui sort : bord blanc + image en degrade, comme un 10x15
    tw = int(pw * 0.46)
    th = int(tw * 1.34)
    tx = px_ + (pw - tw) // 2
    ty0 = top - th + int(0.02 * W)
    d.rectangle([tx, ty0, tx + tw, top + int(0.03 * W)], fill=WHITE)
    m = int(tw * 0.07)
    ix0, iy0, ix1, iy1 = tx + m, ty0 + m, tx + tw - m, top - int(0.02 * W)
    photo = photo_synthetique(max(8, ix1 - ix0), graine=4).resize((ix1 - ix0, iy1 - iy0))
    img.paste(photo, (ix0, iy0))
    d.rectangle([ix0, iy0, ix1, iy1], outline=(196, 204, 210), width=max(1, int(0.0015 * W)))

    # corps
    d.rounded_rectangle([px_, top, px_ + pw, top + ph], radius=int(0.022 * W), fill=(30, 42, 46))
    fente = int(pw * 0.6)
    d.rounded_rectangle([px_ + (pw - fente) // 2, top - int(0.008 * W),
                         px_ + (pw + fente) // 2, top + int(0.012 * W)],
                        radius=int(0.006 * W), fill=(12, 18, 20))
    d.rounded_rectangle([px_ + int(pw * 0.08), top + int(ph * 0.55),
                         px_ + int(pw * 0.34), top + int(ph * 0.72)],
                        radius=int(0.008 * W), fill=ORANGE)
    r = int(pw * 0.022)
    d.ellipse([px_ + pw - int(pw * 0.14) - r, top + int(ph * 0.6) - r,
               px_ + pw - int(pw * 0.14) + r, top + int(ph * 0.6) + r], fill=GREEN)


def grille(d, x, y, W, CW):
    cols = 3
    gap = int(0.018 * W)
    size = int(0.58 * W)
    tile = (min(size, CW) - gap * (cols - 1)) // cols
    x0 = x + (CW - (tile * cols + gap * (cols - 1))) // 2
    img = d._image
    for i in range(9):
        r_, c_ = divmod(i, cols)
        tx = x0 + c_ * (tile + gap)
        ty = y + r_ * (tile + gap)
        vign = photo_synthetique(tile, graine=i + 3)
        masque = Image.new("L", (tile, tile), 0)
        ImageDraw.Draw(masque).rounded_rectangle([0, 0, tile - 1, tile - 1],
                                                 radius=int(tile * 0.08), fill=255)
        img.paste(vign, (tx, ty), masque)


def avant_apres(d, x, y, W, CW, bg_dark):
    """La meme photo : massacree par les partages, et nette."""
    from PIL import ImageFilter
    gap = int(0.03 * W)
    tile = (CW - gap) // 2
    nette = photo_synthetique(tile, graine=2)
    abimee = nette.resize((22, 22), Image.BILINEAR).resize((tile, tile), Image.NEAREST)
    abimee = abimee.filter(ImageFilter.GaussianBlur(tile * 0.012))

    masque = Image.new("L", (tile, tile), 0)
    ImageDraw.Draw(masque).rounded_rectangle([0, 0, tile - 1, tile - 1],
                                             radius=int(tile * 0.06), fill=255)
    img = d._image
    img.paste(abimee, (x, y), masque)
    img.paste(nette, (x + tile + gap, y), masque)

    f = font(F_BODY_B, int(0.03 * W))
    ly = y + tile + int(0.022 * W)
    g1, g2 = "GROUPE WHATSAPP", "CHEZ MYFACE"
    d.text((x + (tile - text_w(d, g1, f)) // 2, ly), g1, font=f, fill=(179, 74, 8))
    d.text((x + tile + gap + (tile - text_w(d, g2, f)) // 2, ly), g2, font=f, fill=GREEN)


def fond_motif(img, W, H, dark):
    """Motif discret sur toute l'affiche : le fond ne doit jamais etre plat."""
    calque = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(calque)
    pas = int(W * 0.055)
    trait = (244, 239, 230, 16) if dark else (14, 36, 41, 14)
    point = (255, 138, 61, 26) if dark else (242, 106, 27, 30)
    r = max(1, int(pas * 0.07))
    for yy in range(0, H + pas, pas):
        for xx in range(0, W + pas, pas):
            cd.polygon([(xx + pas // 2, yy), (xx + pas, yy + pas // 2),
                        (xx + pas // 2, yy + pas), (xx, yy + pas // 2)], outline=trait)
            cd.ellipse([xx - r, yy - r, xx + r, yy + r], fill=point)
    # halo doux dans un coin, pour casser la regularite
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    rr = int(W * 0.7)
    hd.ellipse([-rr // 3, -rr // 2, rr, rr // 2],
               fill=(255, 138, 61, 16) if dark else (242, 106, 27, 14))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(W * 0.06)))
    img.alpha_composite(calque)


def fond_wax(img, d, W, H, dark):
    """Motif inspire du pagne, tres pale, en fond."""
    pas = int(W * 0.075)
    col = (255, 255, 255, 26) if dark else (14, 36, 41, 22)
    calque = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(calque)
    r = int(pas * 0.14)
    for yy in range(0, H + pas, pas):
        for xx in range(0, W + pas, pas):
            cd.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(ORANGE[0], ORANGE[1], ORANGE[2], 24))
            cd.polygon([(xx + pas // 2, yy), (xx + pas, yy + pas // 2),
                        (xx + pas // 2, yy + pas), (xx, yy + pas // 2)], outline=col)
    img.alpha_composite(calque)


def cadre_detection(d, W, H, marge=0.055):
    m = int(W * marge)
    arm = int(W * 0.1)
    lw = max(4, int(W * 0.012))
    coins = [((m, m + arm), (m, m), (m + arm, m), ORANGE),
             ((W - m - arm, m), (W - m, m), (W - m, m + arm), ORANGE),
             ((m, H - m - arm), (m, H - m), (m + arm, H - m), ORANGE),
             ((W - m - arm, H - m), (W - m, H - m), (W - m, H - m - arm), GREEN)]
    for a, b, c, col in coins:
        d.line([a[0], a[1], b[0], b[1]], fill=col, width=lw)
        d.line([b[0], b[1], c[0], c[1]], fill=col, width=lw)


# --------------------------------------------------------------------------
# Rendu d'une affiche
# --------------------------------------------------------------------------
def rendre(nom, blocs, W, H, fond="sand", deco=None):
    dark = fond == "ink"
    img = Image.new("RGBA", (W, H), (*(INK if dark else SAND), 255))
    d = ImageDraw.Draw(img)

    fond_motif(img, W, H, dark)
    if deco == "wax":
        fond_wax(img, d, W, H, dark)
    if deco == "cadre":
        cadre_detection(d, W, H)

    pad = int(W * (0.115 if deco == "cadre" else 0.085))
    CW = W - 2 * pad
    fg = SAND if dark else INK

    hauteurs = [mesure(d, b, W, CW) for b in blocs]
    fixes = sum(hauteurs)
    n_spacers = sum(1 for b in blocs if b["t"] == "spacer")
    libre = max(0, H - 2 * pad - fixes)
    if n_spacers:
        part = libre // n_spacers
    else:
        part = 0

    if fixes > H - 2 * pad:
        print(f"    ! {nom} depasse de {fixes - (H - 2 * pad)} px ({W}x{H})")

    y = pad + (libre // 2 if not n_spacers else 0)
    for b, h in zip(blocs, hauteurs):
        if b["t"] == "spacer":
            y += part
            continue
        dessine(img, d, b, pad, y, W, CW, fg, dark)
        y += h

    return img.convert("RGB")


# --------------------------------------------------------------------------
# Les affiches
# --------------------------------------------------------------------------
SIG = "Un selfie. Toutes tes photos."

AFFICHES = [
    # ---------------- Serie A : la marque et le principe ----------------
    dict(nom="A1-signature", formats=["post", "story"], fond="ink", deco="cadre", blocs=[
        b_logo(0.07), b_spacer(),
        b_title("Un selfie.\nToutes\ntes photos.", 0.125),
        b_spacer(),
        b_body("Mariages · Remises de diplômes · Soirées · Entreprises\nAbidjan, Côte d'Ivoire", 0.032),
    ]),
    dict(nom="A2-mode-emploi", formats=["post", "a4"], fond="sand", blocs=[
        b_logo(0.07), b_gap(0.05),
        b_title("Tes photos\nen 3 étapes", 0.085), b_gap(0.045),
        b_steps([("Scanne le QR code", "posé sur ta table ou affiché à l'entrée"),
                 ("Prends un selfie", "l'application reconnaît ton visage"),
                 ("Récupère tes photos", "en qualité d'origine, sur ton téléphone")]),
        b_spacer(), b_rule(), b_gap(0.02),
        b_body(SIG, 0.034, bold=True),
    ]),
    dict(nom="A3-telephone", formats=["post", "story"], fond="ink", blocs=[
        b_logo(0.065), b_gap(0.03),
        b_image("telephone.png", 0.6), b_gap(0.04),
        b_title("14 photos d'elle.\nTrouvées en 4 secondes.", 0.062),
        b_gap(0.015),
        b_body("Elle n'a rien fait défiler.", 0.032),
        b_spacer(),
    ]),
    dict(nom="A4-avant-apres", formats=["post"], fond="sand", blocs=[
        b_logo(0.07), b_spacer(),
        b_beforeafter(), b_gap(0.05),
        b_title("Ta tenue méritait mieux\nqu'une photo floue.", 0.062),
        b_spacer(),
        b_body("Chez MYFACE, tes photos ne passent par aucun groupe : qualité d'origine, directement sur ton téléphone.", 0.031),
    ]),
    dict(nom="A5-prix", formats=["post", "a4"], fond="sand", deco="wax", blocs=[
        b_logo(0.07), b_gap(0.04),
        b_title("Tes photos,\nà partir de 450 F", 0.078), b_gap(0.04),
        b_prices([("La photo", "450 F"),
                  ("Impression papier, en option", "+500 F"),
                  ("Lots et remises", "selon l'événement")]),
        b_gap(0.02),
        b_body("Les prix sont fixés par événement : ils s'adaptent au type de cérémonie et au nombre d'invités. Demandez les vôtres à l'organisateur.", 0.029),
        b_spacer(),
        b_body("Mobile Money ou espèces à la borne.", 0.032, bold=True),
    ]),
    dict(nom="A6-photographes", formats=["post", "story"], fond="ink", deco="cadre", blocs=[
        b_logo(0.07), b_spacer(),
        b_title("Photographe\nà Abidjan ?", 0.095), b_gap(0.035),
        b_body("Tu photographies.\nOn vend tes photos pour toi.", 0.04),
        b_gap(0.01),
        b_title("Tu gardes 70 %.", 0.058, color=ORANGE),
        b_spacer(),
        b_body("Les 5 premiers partenaires gardent 100 % pendant 3 mois.\nWhatsApp 07 58 50 94 03", 0.03),
    ]),
    dict(nom="A7-offre-datee", formats=["post", "story"], fond="sand", blocs=[
        b_logo(0.07), b_spacer(),
        b_title("Galas et soirées\nde fin d'année", 0.078), b_gap(0.04),
        b_date("30", "novembre"), b_gap(0.04),
        b_body("Réservez avant cette date : les tirages papier sont offerts pour vos invités.", 0.036),
        b_spacer(),
        b_body("WhatsApp · 07 58 50 94 03", 0.032, bold=True),
    ]),
    dict(nom="A8-pagne-qr", formats=["story", "a4"], fond="sand", deco="wax", blocs=[
        b_logo(0.07), b_spacer(),
        b_title("Tes invités\nrepartent avec\nleurs photos.", 0.088), b_gap(0.03),
        b_body("Tu n'as plus à les envoyer une par une dans le groupe.", 0.034),
        b_spacer(),
        b_qr("qr-demo.png", "Scanne : un événement en vrai"),
        b_spacer(),
        b_body(SIG, 0.03, bold=True, align="center"),
    ]),


    dict(nom="A9-en-4-ecrans", formats=["post", "story", "a4"], fond="ink", blocs=[
        b_logo(0.065), b_gap(0.03),
        b_title("Du QR code\nà tes photos :\nquatre écrans.", 0.058), b_gap(0.025),
        b_body("Rien à installer. Tout se passe dans le navigateur du téléphone, ou sur la borne.", 0.031),
        b_gap(0.035),
        b_ecrans([("ecran-1-accueil.png", "Tu ouvres le lien de l'événement"),
                  ("ecran-2-selfie.png", "Tu prends un selfie"),
                  ("ecran-3-photos.png", "Tes photos apparaissent"),
                  ("ecran-4-paiement.png", "Tu paies et tu télécharges")]),
        b_spacer(),
        b_body("Moins d'une minute, du premier scan au téléchargement.", 0.033, bold=True),
    ]),

    # ---------------- Serie B : les volets de l'application ----------------
    dict(nom="B1-borne", formats=["post", "a4"], fond="ink", blocs=[
        b_logo(0.065), b_gap(0.03),
        b_title("La borne MYFACE,\nsur place", 0.068), b_gap(0.03),
        b_image("borne-face.png", 0.47), b_gap(0.025),
        b_steps([("Un écran à l'entrée", "les invités viennent y chercher leurs photos"),
                 ("Selfie sur la borne", "pas besoin de téléphone ni de connexion"),
                 ("Paiement sur place", "Mobile Money ou espèces, reçu remis")], 0.029),
        b_spacer(),
    ]),
    dict(nom="B2-impression", formats=["post", "a4"], fond="sand", blocs=[
        b_logo(0.07), b_gap(0.035),
        b_title("Repartez avec\nvos photos\nimprimées", 0.078),
        b_gap(0.03),
        b_image("borne-34.png", 0.46), b_gap(0.025),
        b_body("Le tirage 10x15 sort à la borne, en quelques secondes, pendant que la fête continue.", 0.034),
        b_spacer(),
        b_body("Disponible uniquement à la borne de l'événement.", 0.029),
    ]),
    dict(nom="B3-recherche-visage", formats=["post"], fond="ink", deco="cadre", blocs=[
        b_logo(0.065), b_spacer(),
        b_title("Ton visage\nsuffit.", 0.115), b_gap(0.035),
        b_body("Plus besoin de faire défiler 400 photos pour te trouver. Un selfie, et l'application sort toutes celles où tu apparais.", 0.034),
        b_spacer(),
        b_body("Le selfie sert uniquement à la recherche.", 0.028),
    ]),
    dict(nom="B4-galerie", formats=["post"], fond="sand", blocs=[
        b_logo(0.07), b_gap(0.035),
        b_title("Toutes les photos\nde l'événement", 0.07), b_gap(0.035),
        b_grid(), b_gap(0.04),
        b_body("La galerie complète reste ouverte à tous les invités : on regarde, on choisit, on achète seulement ce qu'on veut.", 0.033),
        b_spacer(),
    ]),
    dict(nom="B5-paiement", formats=["post"], fond="ink", blocs=[
        b_logo(0.065), b_spacer(),
        b_title("Paye comme\ntu veux.", 0.098), b_gap(0.04),
        b_chips(["Wave", "Orange Money", "MTN MoMo", "Moov Money", "Espèces à la borne"], 0.031),
        b_spacer(),
        b_body("Chaque commande donne un reçu détaillé : le nombre de photos, les noms des fichiers et le montant payé.", 0.032),
    ]),
    dict(nom="B6-telechargement", formats=["post"], fond="sand", blocs=[
        b_logo(0.07), b_spacer(),
        b_title("Qualité d'origine,\npas de compression", 0.064), b_gap(0.035),
        b_bullets(["Les fichiers tels que sortis de l'appareil photo",
                   "Un lien personnel, à rouvrir après la fête",
                   "Photo par photo, ou tout d'un coup"], 0.034),
        b_spacer(),
        b_body("Pensez à télécharger vos photos le jour même.", 0.029),
    ]),
    dict(nom="B7-organisateurs", formats=["post"], fond="ink", blocs=[
        b_logo(0.065), b_spacer(),
        b_title("Organisateurs :\nvous voyez tout.", 0.062), b_gap(0.035),
        b_bullets(["Les photos mises en ligne au fil de la soirée",
                   "Les commandes et les recettes en direct",
                   "Les tirages à imprimer, événement par événement",
                   "Le lien et l'affiche à partager à vos invités"], 0.032),
        b_spacer(),
        b_body("Un espace organisateur par événement. Vos invités, eux, n'ont rien à installer.\nWhatsApp 07 58 50 94 03", 0.031),
    ]),
    # ---------------- Serie C : vendre a ceux qui paient ----------------
    dict(nom="C1-organisateurs-forfait", formats=["post", "a4"], fond="sand", deco="wax", blocs=[
        b_logo(0.07), b_spacer(),
        b_title("Offrez leurs photos\nà vos invités.", 0.076), b_gap(0.035),
        b_body("Un forfait, et chaque invité repart avec ses photos sans rien payer. Le cadeau dont on parle encore la semaine suivante.", 0.035),
        b_gap(0.02),
        b_prices([("Jusqu'à 150 invités", "150 000 F"),
                  ("Jusqu'à 300 invités", "250 000 F"),
                  ("Au-delà", "sur devis")]),
        b_spacer(),
        b_body("Devis en une heure · WhatsApp 07 58 50 94 03", 0.032, bold=True),
    ]),
    dict(nom="C2-evenement-photographie", formats=["a4", "post"], fond="sand", blocs=[
        b_logo(0.07), b_gap(0.04),
        b_title("Cet événement\nest photographié", 0.072), b_gap(0.03),
        b_body("Vos photos seront disponibles sur MYFACE : scannez le code, faites un selfie, et retrouvez celles où vous apparaissez.", 0.034),
        b_gap(0.03),
        b_qr("qr-demo.png", "Scannez pour retrouver vos photos"),
        b_spacer(), b_rule(), b_gap(0.02),
        b_body("Si vous ne souhaitez pas apparaître sur les photos, signalez-le à l'équipe ou à l'organisateur. Le selfie sert uniquement à retrouver vos photos.", 0.027),
    ]),
    dict(nom="C3-entreprises", formats=["post"], fond="ink", blocs=[
        b_logo(0.065), b_spacer(),
        b_title("Vos événements\nd'entreprise,\nphotographiés.", 0.066), b_gap(0.035),
        b_bullets(["Chaque collaborateur retrouve ses photos avec un selfie",
                   "Vos photos en qualité d'origine pour la communication interne",
                   "Un rapport de participation après l'événement"], 0.032),
        b_spacer(),
        b_body("Galas, séminaires, 8 mars, présentation des vœux.\nDevis sous 24 h · WhatsApp 07 58 50 94 03", 0.031),
    ]),
    dict(nom="C4-ecoles", formats=["post"], fond="sand", blocs=[
        b_logo(0.07), b_spacer(),
        b_title("Remises de diplômes\net sorties de promo", 0.064), b_gap(0.035),
        b_bullets(["Les familles retrouvent leurs photos le soir même",
                   "Une borne à l'entrée de la cérémonie, sans file d'attente",
                   "Une part des ventes reversée au bureau des étudiants"], 0.033),
        b_spacer(),
        b_body("Parlez-en à votre BDE, on s'occupe du reste.\nWhatsApp 07 58 50 94 03", 0.032, bold=True),
    ]),
    dict(nom="C5-on-vient-chez-vous", formats=["post", "story"], fond="ink", deco="cadre", blocs=[
        b_logo(0.07), b_spacer(),
        b_title("On vient\nchez vous.", 0.105), b_gap(0.035),
        b_body("Abidjan et ses environs pour le moment. Ailleurs en Côte d'Ivoire, on se déplace selon la taille de l'événement.", 0.033),
        b_gap(0.025),
        b_chips(["Mariages", "Diplômes", "Entreprises", "Soirées", "Baptêmes"], 0.029),
        b_spacer(),
        b_body("Devis en une heure · WhatsApp 07 58 50 94 03", 0.031, bold=True),
    ]),
    dict(nom="C6-photos-identite", formats=["post", "a4"], fond="sand", deco="wax", blocs=[
        b_logo(0.07), b_spacer(),
        b_title("Photos d'identité :\nc'est la rentrée.", 0.068), b_gap(0.035),
        b_bullets(["On se déplace dans l'école ou l'université",
                   "Tirage immédiat, aux formats demandés",
                   "Tarif de groupe à partir de 20 élèves"], 0.033),
        b_spacer(),
        b_body("Dossiers d'inscription, concours, badges. WhatsApp 07 58 50 94 03", 0.031, bold=True),
    ]),
]



def main():
    for cle in FORMATS:
        (BASE / cle).mkdir(parents=True, exist_ok=True)
    total = 0
    for a in AFFICHES:
        for cle in a["formats"]:
            W, H = FORMATS[cle]
            img = rendre(a["nom"], a["blocs"], W, H, a.get("fond", "sand"), a.get("deco"))
            dest = BASE / cle / f"{a['nom']}.png"
            img.save(dest, dpi=(300, 300) if cle == "a4" else (72, 72))
            total += 1
            print(f"  {dest.relative_to(BASE)}  {W}x{H}")
    print(f"{total} fichiers generes dans {BASE}")


if __name__ == "__main__":
    main()
