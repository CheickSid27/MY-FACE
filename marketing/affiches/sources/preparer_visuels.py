# -*- coding: utf-8 -*-
"""Prepare les visuels des affiches a partir des images fournies.

- 3.jpg : la borne de face, ecran sur fond vert        -> borne-face.png
- 4.jpg : la borne de trois quarts, tirage dans la fente -> borne-34.png
  Dans les deux cas : fond retire, marque du fabricant effacee, fond vert
  remplace par la plateforme MYFACE.
- 2.png : mockup iPhone sur fond vert                  -> telephone.png
- Les quatre ecrans du parcours                        -> ecran-1..4.png

    python sources/preparer_visuels.py
"""

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = Path(__file__).resolve().parent
SRC = Path(r"C:\Users\cheic\AppData\Local\Temp\claude\D--MY-FACE"
           r"\bcf1b7a6-912f-4f82-8d22-cca915f93b35\images")

INK = (14, 36, 41)
SAND = (244, 239, 230)
ORANGE = (242, 106, 27)
GREEN = (0, 133, 75)
GRIS = (150, 170, 175)
F_DISPLAY = "C:/Windows/Fonts/ariblk.ttf"
F_BODY = "C:/Windows/Fonts/segoeui.ttf"
F_BODY_B = "C:/Windows/Fonts/segoeuib.ttf"
F_NUM = "C:/Windows/Fonts/arialbd.ttf"

_fc: dict = {}


def font(p, s):
    k = (p, max(8, int(s)))
    if k not in _fc:
        _fc[k] = ImageFont.truetype(*k)
    return _fc[k]


def larg(d, t, f):
    b = d.textbbox((0, 0), t, font=f)
    return b[2] - b[0]


def haut(d, t, f):
    b = d.textbbox((0, 0), t, font=f)
    return b[3] - b[1]


def centre(d, t, f, w, y, fill):
    d.text(((w - larg(d, t, f)) // 2, y), t, font=f, fill=fill)


# --------------------------------------------------------------------------
# Outils image
# --------------------------------------------------------------------------
def remplir_lignes(m: np.ndarray) -> np.ndarray:
    plein = np.zeros_like(m)
    for y in range(m.shape[0]):
        xs = np.where(m[y])[0]
        if xs.size:
            plein[y, xs.min():xs.max() + 1] = True
    return plein


def coins(m: np.ndarray):
    ys, xs = np.where(m)
    s, d = xs + ys, xs - ys
    return [(int(xs[s.argmin()]), int(ys[s.argmin()])),
            (int(xs[d.argmax()]), int(ys[d.argmax()])),
            (int(xs[s.argmax()]), int(ys[s.argmax()])),
            (int(xs[d.argmin()]), int(ys[d.argmin()]))]


def detourer(im: Image.Image, t0: int = 25, t1: int = 90) -> Image.Image:
    """Enleve le fond uni : seuil global sur la couleur des bords, puis on ne
    supprime que le fond relie aux bords (les zones grises a l'interieur du
    chassis, comme la fente d'impression, restent opaques)."""
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    h, w = a.shape[:2]
    bord = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    fond_col = np.median(bord, axis=0)
    dist = np.abs(a - fond_col).sum(axis=2)

    candidat = dist < t0
    relie = np.zeros((h, w), dtype=bool)
    file = deque()
    for x in range(w):
        for y in (0, h - 1):
            if candidat[y, x] and not relie[y, x]:
                relie[y, x] = True
                file.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if candidat[y, x] and not relie[y, x]:
                relie[y, x] = True
                file.append((y, x))
    while file:
        y, x = file.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and candidat[ny, nx] and not relie[ny, nx]:
                relie[ny, nx] = True
                file.append((ny, nx))

    alpha = np.clip((dist - t0) / max(1, (t1 - t0)), 0, 1)
    alpha[relie] = 0.0
    out = im.convert("RGBA")
    out.putalpha(Image.fromarray((alpha * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.7)))
    return out


def masque_vert(a: np.ndarray) -> np.ndarray:
    """Le fond vert de l'ecran : vert franchement dominant, puis fermeture
    morphologique pour boucher le bruit du JPEG."""
    dominance = a[:, :, 1] - np.maximum(a[:, :, 0], a[:, :, 2])
    m = (dominance > 45) & (a[:, :, 1] > 110)
    img = Image.fromarray((m * 255).astype(np.uint8), "L")
    img = img.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
    return np.asarray(img) > 127


def calque_perspective(taille, ecran: Image.Image, quad) -> Image.Image:
    dst = [(float(x), float(y)) for x, y in quad]
    src = [(0.0, 0.0), (float(ecran.width), 0.0),
           (float(ecran.width), float(ecran.height)), (0.0, float(ecran.height))]
    A, B = [], []
    for (X, Y), (u, v) in zip(dst, src):
        A.append([X, Y, 1, 0, 0, 0, -u * X, -u * Y]); B.append(u)
        A.append([0, 0, 0, X, Y, 1, -v * X, -v * Y]); B.append(v)
    coeffs = np.linalg.solve(np.array(A), np.array(B))
    return ecran.convert("RGBA").transform(taille, Image.PERSPECTIVE, coeffs, Image.BICUBIC)


def photo(taille, graine=0):
    import sys
    sys.path.insert(0, str(BASE.parent))
    from generer_affiches import photo_synthetique
    return photo_synthetique(int(taille), graine=graine)


# --------------------------------------------------------------------------
# La plateforme MYFACE sur l'ecran de la borne
# --------------------------------------------------------------------------
def ecran_borne(w: int, h: int) -> Image.Image:
    im = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(im)

    fl = font(F_DISPLAY, int(w * 0.055))
    x = (w - larg(d, "MYFACE", fl)) // 2
    d.text((x, int(h * 0.05)), "MY", font=fl, fill=SAND)
    d.text((x + larg(d, "MY", fl), int(h * 0.05)), "FACE", font=fl, fill=ORANGE)

    cw = int(w * 0.52)
    cx0 = (w - cw) // 2
    cy0 = int(h * 0.19)
    arm = int(cw * 0.3)
    lw = max(3, int(w * 0.02))
    for a, b, col in [((cx0, cy0 + arm), (cx0, cy0), ORANGE), ((cx0, cy0), (cx0 + arm, cy0), ORANGE),
                      ((cx0 + cw - arm, cy0), (cx0 + cw, cy0), ORANGE), ((cx0 + cw, cy0), (cx0 + cw, cy0 + arm), ORANGE),
                      ((cx0, cy0 + cw - arm), (cx0, cy0 + cw), ORANGE), ((cx0, cy0 + cw), (cx0 + arm, cy0 + cw), ORANGE),
                      ((cx0 + cw, cy0 + cw - arm), (cx0 + cw, cy0 + cw), GREEN),
                      ((cx0 + cw, cy0 + cw), (cx0 + cw - arm, cy0 + cw), GREEN)]:
        d.line([a[0], a[1], b[0], b[1]], fill=col, width=lw)
    r = int(cw * 0.05)
    for ox in (0.34, 0.66):
        d.ellipse([cx0 + int(cw * ox) - r, cy0 + int(cw * 0.36) - r,
                   cx0 + int(cw * ox) + r, cy0 + int(cw * 0.36) + r], fill=SAND)
    d.arc([cx0 + int(cw * 0.27), cy0 + int(cw * 0.4), cx0 + int(cw * 0.73), cy0 + int(cw * 0.78)],
          start=20, end=160, fill=SAND, width=max(3, int(cw * 0.05)))

    centre(d, "Touchez l'écran", font(F_DISPLAY, int(w * 0.07)), w, int(h * 0.6), SAND)
    centre(d, "et retrouvez vos photos", font(F_BODY, int(w * 0.046)), w, int(h * 0.68), GRIS)

    bh = int(h * 0.072)
    bw = int(w * 0.62)
    by = int(h * 0.79)
    d.rounded_rectangle([(w - bw) // 2, by, (w + bw) // 2, by + bh], radius=bh // 2, fill=ORANGE)
    fb = font(F_BODY_B, int(w * 0.05))
    centre(d, "Commencer", fb, w, by + (bh - haut(d, "Commencer", fb)) // 2 - int(h * 0.005), (255, 255, 255))
    return im


# --------------------------------------------------------------------------
# Les quatre ecrans du parcours, pour l'affiche « en 4 ecrans »
# --------------------------------------------------------------------------
def cadre_tel(w, h):
    im = Image.new("RGB", (w, h), (9, 22, 26))
    d = ImageDraw.Draw(im)
    d.text((int(w * 0.07), int(h * 0.028)), "20:24", font=font(F_BODY_B, int(w * 0.055)), fill=SAND)
    iw, ih = int(w * 0.3), int(w * 0.085)
    d.rounded_rectangle([(w - iw) // 2, int(h * 0.016), (w + iw) // 2, int(h * 0.016) + ih],
                        radius=ih // 2, fill=(0, 0, 0))
    return im, d


def ecran_accueil(w, h):
    im, d = cadre_tel(w, h)
    fl = font(F_DISPLAY, int(w * 0.05))
    x = int(w * 0.07)
    d.text((x, int(h * 0.09)), "MY", font=fl, fill=SAND)
    d.text((x + larg(d, "MY", fl), int(h * 0.09)), "FACE", font=fl, fill=ORANGE)

    v = photo(int(w * 0.7), graine=6)
    px, py = (w - v.width) // 2, int(h * 0.16)
    im.paste(v, (px, py))
    d.rectangle([px, py, px + v.width, py + v.height], outline=(60, 80, 84), width=2)

    centre(d, "MARIAGE KENZA", font(F_DISPLAY, int(w * 0.068)), w, int(h * 0.56), SAND)
    centre(d, "27 septembre · Abidjan", font(F_BODY, int(w * 0.044)), w, int(h * 0.62), GRIS)

    bw, bh = int(w * 0.82), int(h * 0.058)
    for i, (txt, plein) in enumerate([("Scanner mon visage", True), ("Parcourir la galerie", False)]):
        by = int(h * 0.7) + i * int(bh * 1.4)
        if plein:
            d.rounded_rectangle([(w - bw) // 2, by, (w + bw) // 2, by + bh], radius=bh // 2, fill=ORANGE)
            col = (255, 255, 255)
        else:
            d.rounded_rectangle([(w - bw) // 2, by, (w + bw) // 2, by + bh], radius=bh // 2,
                                outline=(90, 110, 115), width=max(2, int(w * 0.005)))
            col = SAND
        fb = font(F_BODY_B, int(w * 0.048))
        centre(d, txt, fb, w, by + (bh - haut(d, txt, fb)) // 2 - int(h * 0.004), col)
    return im


def ecran_selfie(w, h):
    im, d = cadre_tel(w, h)
    vx0, vy0, vx1, vy1 = int(w * 0.07), int(h * 0.11), int(w * 0.93), int(h * 0.71)
    for k in range(vy1 - vy0):
        f = k / max(1, vy1 - vy0)
        d.line([vx0, vy0 + k, vx1, vy0 + k],
               fill=(int(44 + 28 * f), int(54 + 24 * f), int(62 + 20 * f)))
    cx, cy = w // 2, int(h * 0.4)
    rt = int(w * 0.16)
    d.ellipse([cx - int(rt * 1.75), cy + int(rt * 0.8), cx + int(rt * 1.75), vy1], fill=(20, 30, 36))
    d.ellipse([cx - rt, cy - rt, cx + rt, cy + rt], fill=(20, 30, 36))

    cw = int(w * 0.5)
    cx0, cy0 = cx - cw // 2, cy - int(cw * 0.52)
    arm = int(cw * 0.28)
    lw = max(3, int(w * 0.016))
    for a, b, col in [((cx0, cy0 + arm), (cx0, cy0), ORANGE), ((cx0, cy0), (cx0 + arm, cy0), ORANGE),
                      ((cx0 + cw - arm, cy0), (cx0 + cw, cy0), ORANGE), ((cx0 + cw, cy0), (cx0 + cw, cy0 + arm), ORANGE),
                      ((cx0, cy0 + cw - arm), (cx0, cy0 + cw), ORANGE), ((cx0, cy0 + cw), (cx0 + arm, cy0 + cw), ORANGE),
                      ((cx0 + cw, cy0 + cw - arm), (cx0 + cw, cy0 + cw), GREEN),
                      ((cx0 + cw, cy0 + cw), (cx0 + cw - arm, cy0 + cw), GREEN)]:
        d.line([a[0], a[1], b[0], b[1]], fill=col, width=lw)

    centre(d, "Centre ton visage", font(F_DISPLAY, int(w * 0.058)), w, int(h * 0.75), SAND)
    centre(d, "le selfie sert juste à te retrouver", font(F_BODY, int(w * 0.04)), w, int(h * 0.8), GRIS)
    r = int(w * 0.085)
    cyb = int(h * 0.88)
    d.ellipse([w // 2 - r, cyb - r, w // 2 + r, cyb + r], outline=SAND, width=max(3, int(w * 0.012)))
    d.ellipse([w // 2 - int(r * 0.7), cyb - int(r * 0.7), w // 2 + int(r * 0.7), cyb + int(r * 0.7)], fill=ORANGE)
    return im


def ecran_photos(w, h):
    im, d = cadre_tel(w, h)
    pad = int(w * 0.07)
    d.text((pad, int(h * 0.095)), "Mes photos", font=font(F_BODY_B, int(w * 0.085)), fill=SAND)
    d.text((pad, int(h * 0.155)), "14 photos trouvées", font=font(F_BODY, int(w * 0.048)), fill=GRIS)
    cols, gap = 3, int(w * 0.025)
    tile = (w - 2 * pad - gap * (cols - 1)) // cols
    gy = int(h * 0.21)
    for i in range(9):
        r_, c_ = divmod(i, cols)
        tx, ty = pad + c_ * (tile + gap), gy + r_ * (tile + gap)
        v = photo(tile, graine=i + 1)
        masque = Image.new("L", (tile, tile), 0)
        ImageDraw.Draw(masque).rounded_rectangle([0, 0, tile - 1, tile - 1], radius=int(tile * 0.12), fill=255)
        im.paste(v, (tx, ty), masque)
        if i in (1, 4, 6):
            m = int(tile * 0.16)
            d.rounded_rectangle([tx + m, ty + m, tx + tile - m, ty + tile - m],
                                radius=int(tile * 0.06), outline=ORANGE, width=max(2, int(tile * 0.05)))
    by = gy + 3 * (tile + gap) + int(h * 0.028)
    bh = int(h * 0.06)
    d.rounded_rectangle([pad, by, w - pad, by + bh], radius=bh // 2, fill=ORANGE)
    fb = font(F_BODY_B, int(w * 0.052))
    centre(d, "Télécharger mes photos", fb, w,
           by + (bh - haut(d, "Télécharger mes photos", fb)) // 2 - int(h * 0.004), (255, 255, 255))
    fp = font(F_BODY, int(w * 0.044))
    centre(d, "Panier · 3 photos · 1 350 F", fp, w, by + bh + int(h * 0.022), GRIS)
    return im


def ecran_paiement(w, h):
    im, d = cadre_tel(w, h)
    pad = int(w * 0.07)
    d.text((pad, int(h * 0.095)), "Paiement", font=font(F_BODY_B, int(w * 0.085)), fill=SAND)
    d.text((pad, int(h * 0.155)), "3 photos · 1 tirage", font=font(F_BODY, int(w * 0.048)), fill=GRIS)

    d.rounded_rectangle([pad, int(h * 0.21), w - pad, int(h * 0.3)], radius=int(w * 0.03), fill=(22, 44, 50))
    d.text((pad + int(w * 0.05), int(h * 0.235)), "À payer", font=font(F_BODY, int(w * 0.048)), fill=GRIS)
    ft = font(F_NUM, int(w * 0.085))
    montant = "1 550 F"
    d.text((w - pad - int(w * 0.05) - larg(d, montant, ft), int(h * 0.228)), montant, font=ft, fill=SAND)

    y = int(h * 0.34)
    for nom, choisi in [("Wave", True), ("Orange Money", False), ("MTN MoMo", False), ("Espèces à la borne", False)]:
        hb = int(h * 0.06)
        d.rounded_rectangle([pad, y, w - pad, y + hb], radius=int(w * 0.03),
                            outline=ORANGE if choisi else (60, 80, 84), width=max(2, int(w * 0.006)))
        r = int(w * 0.02)
        cx, cy = pad + int(w * 0.07), y + hb // 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ORANGE if choisi else (90, 110, 115),
                  width=max(2, int(w * 0.006)))
        if choisi:
            d.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], fill=ORANGE)
        f = font(F_BODY_B if choisi else F_BODY, int(w * 0.048))
        d.text((pad + int(w * 0.14), cy - haut(d, nom, f) // 2 - int(h * 0.004)), nom, font=f, fill=SAND)
        y += int(hb * 1.28)

    bh = int(h * 0.062)
    by = int(h * 0.79)
    d.rounded_rectangle([pad, by, w - pad, by + bh], radius=bh // 2, fill=ORANGE)
    fb = font(F_BODY_B, int(w * 0.054))
    centre(d, "Payer et télécharger", fb, w,
           by + (bh - haut(d, "Payer et télécharger", fb)) // 2 - int(h * 0.004), (255, 255, 255))
    centre(d, "Lien de téléchargement par SMS", font(F_BODY, int(w * 0.04)), w, by + bh + int(h * 0.02), GRIS)
    return im


# --------------------------------------------------------------------------
def preparer_borne(fichier, sortie, zone_marque, t0=25, t1=90):
    im = Image.open(SRC / fichier).convert("RGB")
    a = np.asarray(im).astype(int)

    vert = masque_vert(a)
    quad = coins(vert)
    ys, xs = np.where(vert)
    print(f"  {fichier} : ecran x {xs.min()}-{xs.max()} y {ys.min()}-{ys.max()} ({vert.sum()} px)")

    decoupe = detourer(im, t0=t0, t1=t1)

    ui = ecran_borne(int(xs.max() - xs.min()) * 3, int(ys.max() - ys.min()) * 3)
    calque = calque_perspective(decoupe.size, ui, quad)
    masque = Image.fromarray((vert * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(3))
    decoupe.paste(calque, (0, 0), masque)

    y0, y1, x0, x1 = zone_marque
    zone = np.zeros(a.shape[:2], dtype=bool)
    zone[y0:y1, x0:x1] = True
    texte = zone & (a.min(axis=2) < 215)
    if texte.any():
        ys2, xs2 = np.where(texte)
        print(f"    marque effacee : x {xs2.min()}-{xs2.max()} y {ys2.min()}-{ys2.max()}")
        # on recouvre franchement la zone, mais seulement la ou le chassis
        # est opaque (jamais sur le fond deja rendu transparent)
        opaque = np.asarray(decoupe.split()[3]) > 200
        rect = np.zeros(a.shape[:2], dtype=bool)
        rect[max(0, y0 - 6):y1 + 6, max(0, x0 - 6):x1 + 6] = True
        mt = Image.fromarray(((rect & opaque) * 255).astype(np.uint8), "L")
        blanc = Image.new("RGBA", decoupe.size, (250, 250, 250, 255))
        decoupe.paste(blanc, (0, 0), mt)

    decoupe = decoupe.crop(decoupe.getbbox())
    decoupe.save(BASE / sortie)
    print(f"    -> {sortie} {decoupe.size}")


def preparer_telephone():
    brut = Image.open(SRC / "2.png").convert("RGBA")
    f = 3
    grand_rgba = brut.resize((brut.width * f, brut.height * f), Image.LANCZOS)
    grand = Image.new("RGB", grand_rgba.size, (255, 255, 255))
    grand.paste(grand_rgba, (0, 0), grand_rgba)
    alpha_src = np.asarray(grand_rgba.split()[3])
    a = np.asarray(grand).astype(int)

    vert = masque_vert(a)
    quad = coins(vert)
    ys, xs = np.where(vert)

    blanc = np.abs(a - 255).sum(axis=2) < 45
    alpha = np.minimum(((~blanc) * 255).astype(np.uint8), alpha_src)
    decoupe = grand.convert("RGBA")
    decoupe.putalpha(Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(1.0)))

    ui = ecran_photos(int(xs.max() - xs.min()), int(ys.max() - ys.min()))
    calque = calque_perspective(decoupe.size, ui, quad)
    masque = Image.fromarray((vert * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(5))
    decoupe.paste(calque, (0, 0), masque)
    decoupe = decoupe.crop(decoupe.getbbox())
    decoupe.save(BASE / "telephone.png")
    print(f"  -> telephone.png {decoupe.size}")


def preparer_ecrans():
    w, h = 540, 1170
    for nom, fn in [("ecran-1-accueil.png", ecran_accueil), ("ecran-2-selfie.png", ecran_selfie),
                    ("ecran-3-photos.png", ecran_photos), ("ecran-4-paiement.png", ecran_paiement)]:
        fn(w, h).save(BASE / nom)
        print(f"  -> {nom} {w}x{h}")


if __name__ == "__main__":
    preparer_borne("3.jpg", "borne-face.png", zone_marque=(276, 299, 596, 660), t0=72, t1=125)
    preparer_borne("4.jpg", "borne-34.png", zone_marque=(272, 302, 590, 676), t0=38, t1=70)
    preparer_telephone()
    preparer_ecrans()
