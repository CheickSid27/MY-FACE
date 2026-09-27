# -*- coding: utf-8 -*-
"""Fabrique les videos de demonstration MYFACE, image par image.

Aucun tournage : tout est dessine, avec les couleurs, le logo et l'interface
de l'application. Le rendu sort en MP4, pret pour WhatsApp, TikTok et
Instagram.

python generer_video.py            (les deux formats)
python generer_video.py vertical   (9:16 seulement)

Sortie : video/myface-parcours-9x16.mp4 et video/myface-parcours-1x1.mp4
"""

import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = Path(__file__).resolve().parent
PROJET = BASE.parent
sys.path.insert(0, str(PROJET / "affiches"))
from generer_affiches import logo_icone, photo_synthetique  # noqa: E402

INK = (14, 36, 41)
INK_2 = (19, 48, 56)
SAND = (244, 239, 230)
ORANGE = (242, 106, 27)
GREEN = (0, 133, 75)
GRIS = (150, 170, 175)
BLANC = (255, 255, 255)

F_DISPLAY = "C:/Windows/Fonts/ariblk.ttf"
F_BODY = "C:/Windows/Fonts/segoeui.ttf"
F_BODY_B = "C:/Windows/Fonts/segoeuib.ttf"
F_NUM = "C:/Windows/Fonts/arialbd.ttf"

FPS = 30
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


# --------------------------------------------------------------------------
# Courbes d'animation
# --------------------------------------------------------------------------
def borne01(v):
    return max(0.0, min(1.0, v))


def sortie(t):          # demarre vite, finit doucement
    return 1 - (1 - borne01(t)) ** 3


def entree_sortie(t):
    t = borne01(t)
    return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2


def rebond(t):
    t = borne01(t)
    return 1 - math.cos(t * math.pi / 2) ** 3


def fenetre(t, debut, duree):
    """Avancement 0..1 d'une animation qui commence a `debut` et dure `duree`."""
    return borne01((t - debut) / duree) if duree > 0 else 1.0


# --------------------------------------------------------------------------
# Elements dessines
# --------------------------------------------------------------------------
def fond(W, H, sombre=True):
    img = Image.new("RGB", (W, H), INK if sombre else SAND)
    d = ImageDraw.Draw(img, "RGBA")
    pas = int(W * 0.055)
    trait = (244, 239, 230, 14) if sombre else (14, 36, 41, 12)
    point = (255, 138, 61, 26) if sombre else (242, 106, 27, 26)
    r = max(1, int(pas * 0.07))
    for y in range(0, H + pas, pas):
        for x in range(0, W + pas, pas):
            d.polygon([(x + pas // 2, y), (x + pas, y + pas // 2),
                       (x + pas // 2, y + pas), (x, y + pas // 2)], outline=trait)
            d.ellipse([x - r, y - r, x + r, y + r], fill=point)
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    rr = int(W * 0.8)
    hd.ellipse([-rr // 4, -rr // 2, rr, rr // 2], fill=(255, 138, 61, 34))
    img = Image.alpha_composite(img.convert("RGBA"), halo.filter(ImageFilter.GaussianBlur(W * 0.07)))
    return img.convert("RGB")


def voile_bas(img, W, H, depuis=0.58, force=235):
    """Degrade sombre sur le bas de l'image, pour que le texte passe partout."""
    y0 = int(H * depuis)
    voile = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(voile)
    for y in range(y0, H):
        a = int(force * ((y - y0) / max(1, H - y0)) ** 1.4)
        vd.line([0, y, W, y], fill=(INK[0], INK[1], INK[2], a))
    img.alpha_composite(voile)


def texte_centre(d, txt, f, W, y, couleur, opacite=1.0):
    if opacite <= 0.01:
        return
    col = tuple(int(c) for c in couleur) + (int(255 * borne01(opacite)),)
    for ligne in txt.split("\n"):
        d.text(((W - larg(d, ligne, f)) // 2, y), ligne, font=f, fill=col)
        y += int(f.size * 1.18)


def bloc_bas(img, W, H, titre, sous_titre, a_titre, a_sous, voile=True):
    """Titre et sous-titre empiles depuis le bas, sans jamais se chevaucher."""
    if voile:
        voile_bas(img, W, H, 0.58)
    d = ImageDraw.Draw(img, "RGBA")
    ft = font(F_DISPLAY, int(W * 0.062))
    fs = font(F_BODY, int(W * 0.036))
    y_sous = int(H * 0.87)
    lignes_titre = titre.count(chr(10)) + 1
    hauteur_titre = int(lignes_titre * ft.size * 1.18)
    y_titre = y_sous - hauteur_titre - int(H * 0.035)
    texte_centre(d, titre, ft, W, y_titre, SAND, a_titre)
    if sous_titre:
        texte_centre(d, sous_titre, fs, W, y_sous, GRIS, a_sous)


def cadre_detection(d, x, y, taille, avancement, couleur=ORANGE, epaisseur=None):
    """Les quatre coins qui se referment sur le visage."""
    e = epaisseur or max(3, int(taille * 0.035))
    bras = int(taille * 0.3)
    ecart = int(taille * 0.45 * (1 - sortie(avancement)))
    x0, y0 = x - taille // 2 - ecart, y - taille // 2 - ecart
    x1, y1 = x + taille // 2 + ecart, y + taille // 2 + ecart
    a = int(255 * borne01(avancement * 2))
    c = tuple(couleur) + (a,)
    v = tuple(GREEN) + (a,)
    for p0, p1, col in [((x0, y0 + bras), (x0, y0), c), ((x0, y0), (x0 + bras, y0), c),
                        ((x1 - bras, y0), (x1, y0), c), ((x1, y0), (x1, y0 + bras), c),
                        ((x0, y1 - bras), (x0, y1), c), ((x0, y1), (x0 + bras, y1), c),
                        ((x1, y1 - bras), (x1, y1), v), ((x1, y1), (x1 - bras, y1), v)]:
        d.line([p0[0], p0[1], p1[0], p1[1]], fill=col, width=e)


def telephone(img, cx, cy, larg_tel, ecran_img=None, ombre=True):
    """Chassis de telephone centre en (cx, cy). Renvoie la zone d'ecran."""
    pw = int(larg_tel)
    ph = int(pw / 0.4613)
    x0, y0 = int(cx - pw / 2), int(cy - ph / 2)
    rad = int(pw * 0.125)
    if ombre:
        o = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(o).rounded_rectangle([x0 + int(pw * .03), y0 + int(pw * .05),
                                             x0 + pw + int(pw * .03), y0 + ph + int(pw * .05)],
                                            radius=rad, fill=(0, 0, 0, 120))
        img.alpha_composite(o.filter(ImageFilter.GaussianBlur(int(pw * 0.06))))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=rad, fill=(28, 30, 32, 255))
    b = max(3, int(pw * 0.022))
    sx0, sy0, sx1, sy1 = x0 + b, y0 + b, x0 + pw - b, y0 + ph - b
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=rad - b, fill=(9, 22, 26, 255))
    if ecran_img is not None:
        e = ecran_img.resize((sx1 - sx0, sy1 - sy0), Image.LANCZOS).convert("RGBA")
        masque = Image.new("L", e.size, 0)
        ImageDraw.Draw(masque).rounded_rectangle([0, 0, e.width - 1, e.height - 1],
                                                 radius=rad - b, fill=255)
        img.paste(e, (sx0, sy0), masque)
    iw, ih = int((sx1 - sx0) * 0.33), int((sx1 - sx0) * 0.098)
    d.rounded_rectangle([sx0 + ((sx1 - sx0) - iw) // 2, sy0 + int((sx1 - sx0) * 0.038),
                         sx0 + ((sx1 - sx0) + iw) // 2, sy0 + int((sx1 - sx0) * 0.038) + ih],
                        radius=ih // 2, fill=(0, 0, 0, 255))
    return (sx0, sy0, sx1, sy1)


# --------------------------------------------------------------------------
# Ressources preparees une seule fois
# --------------------------------------------------------------------------
class Ressources:
    def __init__(self, W):
        self.W = W
        self.logo = logo_icone(int(W * 0.34))
        self.vignettes = [photo_synthetique(int(W * 0.30), graine=i + 1) for i in range(9)]
        self.grandes = [photo_synthetique(int(W * 0.52), graine=i + 1) for i in (1, 4, 6, 2, 7)]
        qr = PROJET / "affiches" / "sources" / "qr-demo.png"
        self.qr = Image.open(qr).convert("RGB") if qr.exists() else None
        self.portrait = photo_synthetique(int(W * 0.7), graine=3)


# --------------------------------------------------------------------------
# Les scenes : chacune dessine l'image a l'instant t (en secondes)
# --------------------------------------------------------------------------
def scene_logo(img, t, duree, W, H, R):
    d = ImageDraw.Draw(img, "RGBA")
    a = rebond(fenetre(t, 0.15, 0.7))
    taille = int(R.logo.width * (0.7 + 0.3 * a))
    lg = R.logo.resize((taille, taille), Image.LANCZOS)
    img.alpha_composite(lg, ((W - taille) // 2, int(H * 0.34) - taille // 2))

    f1 = font(F_DISPLAY, int(W * 0.115))
    f2 = font(F_BODY, int(W * 0.042))
    a2 = sortie(fenetre(t, 0.6, 0.6))
    y = int(H * 0.47) + int((1 - a2) * W * 0.05)
    mot = "MYFACE"
    x = (W - larg(d, mot, f1)) // 2
    d.text((x, y), "MY", font=f1, fill=tuple(SAND) + (int(255 * a2),))
    d.text((x + larg(d, "MY", f1), y), "FACE", font=f1, fill=tuple(ORANGE) + (int(255 * a2),))
    a3 = sortie(fenetre(t, 1.1, 0.6))
    texte_centre(d, "Un selfie. Toutes tes photos.", f2, W, y + int(W * 0.15), SAND, a3)


def scene_probleme(img, t, duree, W, H, R):
    """Des tirages qui tombent en tas : le probleme de depart."""
    d = ImageDraw.Draw(img, "RGBA")
    f1 = font(F_DISPLAY, int(W * 0.062))
    f2 = font(F_BODY, int(W * 0.038))

    # les ordonnees sont le HAUT de chaque tirage : on les garde au-dessus de
    # 0,62 H pour que le tas ne morde jamais sur le texte
    positions = [(-.22, -.17, -16), (.20, -.25, 12), (-.05, -.09, 5), (.26, -.07, -9),
                 (-.28, .01, 18), (.05, .04, -4), (.18, .12, 8), (-.18, .15, -13)]
    for i, (dx, dy, ang) in enumerate(positions):
        av = sortie(fenetre(t, 0.15 + i * 0.09, 0.5))
        if av <= 0:
            continue
        vign = R.vignettes[i % len(R.vignettes)]
        c = int(W * 0.23)
        photo = Image.new("RGBA", (c, int(c * 1.3)), (255, 255, 255, 255))
        m = int(c * 0.06)
        photo.paste(vign.resize((c - 2 * m, int(c * 1.3) - 3 * m)), (m, m))
        photo = photo.rotate(ang, expand=True, resample=Image.BICUBIC)
        x = int(W * (0.5 + dx)) - photo.width // 2
        y0 = int(H * (0.30 + dy))
        y = int(y0 - (1 - av) * H * 0.22)
        calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
        calque.paste(photo, (x, y), photo)
        img.alpha_composite(Image.blend(Image.new("RGBA", img.size, (0, 0, 0, 0)), calque, av))

    bloc_bas(img, W, H, "Les photos étalées par terre,\net chacun qui fouille.", "On perd du temps. On repart souvent sans rien.",
             sortie(fenetre(t, 1.5, 0.7)), sortie(fenetre(t, 2.2, 0.7)))

def scene_qr(img, t, duree, W, H, R):
    d = ImageDraw.Draw(img, "RGBA")
    f1 = font(F_DISPLAY, int(W * 0.062))
    f2 = font(F_BODY, int(W * 0.038))
    a = sortie(fenetre(t, 0.1, 0.6))
    cote = int(W * (0.34 + 0.06 * a))
    x, y = (W - cote) // 2, int(H * 0.30)
    marge = int(cote * 0.07)
    d.rounded_rectangle([x - marge, y - marge, x + cote + marge, y + cote + marge],
                        radius=int(cote * 0.06), fill=(255, 255, 255, int(255 * a)))
    if R.qr is not None and a > 0.05:
        qr = R.qr.resize((cote, cote), Image.NEAREST).convert("RGBA")
        qr.putalpha(int(255 * a))
        img.alpha_composite(qr, (x, y))

    balayage = fenetre(t, 0.8, 1.6)
    if 0 < balayage < 1:
        yb = int(y + cote * balayage)
        ligne = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(ligne).rectangle([x, yb - int(cote * .012), x + cote, yb + int(cote * .012)],
                                        fill=tuple(ORANGE) + (220,))
        img.alpha_composite(ligne.filter(ImageFilter.GaussianBlur(int(W * 0.006))))

    bloc_bas(img, W, H, "Scanne le QR code\nde l'événement", "Sur ta table, ou à l'entrée de la salle",
             sortie(fenetre(t, 0.5, 0.6)), sortie(fenetre(t, 1.0, 0.6)))

def scene_selfie(img, t, duree, W, H, R):
    d = ImageDraw.Draw(img, "RGBA")
    f1 = font(F_DISPLAY, int(W * 0.062))
    f2 = font(F_BODY, int(W * 0.038))

    lt = int(min(W * 0.56, H * 0.30))
    zone = telephone(img, W // 2, int(H * 0.42), lt, None)
    sx0, sy0, sx1, sy1 = zone
    vue = Image.new("RGBA", (sx1 - sx0, sy1 - sy0), (34, 46, 54, 255))
    vd = ImageDraw.Draw(vue)
    for k in range(vue.height):
        f = k / vue.height
        vd.line([0, k, vue.width, k], fill=(int(40 + 26 * f), int(50 + 22 * f), int(58 + 18 * f), 255))
    portrait = R.portrait.resize((int(vue.width * 0.86), int(vue.width * 0.86)))
    vue.paste(portrait, ((vue.width - portrait.width) // 2, int(vue.height * 0.22)))
    masque = Image.new("L", vue.size, 0)
    ImageDraw.Draw(masque).rounded_rectangle([0, 0, vue.width - 1, vue.height - 1],
                                             radius=int(lt * 0.1), fill=255)
    img.paste(vue, (sx0, sy0), masque)

    av = fenetre(t, 0.6, 1.1)
    cadre_detection(d, W // 2, sy0 + int(vue.height * 0.42), int(vue.width * 0.54), av)
    if av >= 1:
        clign = 0.5 + 0.5 * math.sin((t - 1.7) * 6)
        fv = font(F_BODY_B, int(W * 0.03))
        txt = "Visage reconnu"
        bx = W // 2 - larg(d, txt, fv) // 2
        by = sy0 + int(vue.height * 0.42) + int(vue.width * 0.34)
        d.rounded_rectangle([bx - int(W * .02), by - int(W * .012),
                             bx + larg(d, txt, fv) + int(W * .02), by + int(W * .046)],
                            radius=int(W * .02), fill=tuple(GREEN) + (int(200 + 55 * clign),))
        d.text((bx, by), txt, font=fv, fill=BLANC + (255,))

    bloc_bas(img, W, H, "Prends un selfie", "il sert seulement à retrouver tes photos",
             sortie(fenetre(t, 0.2, 0.5)), sortie(fenetre(t, 0.7, 0.5)))


def scene_photos(img, t, duree, W, H, R):
    d = ImageDraw.Draw(img, "RGBA")
    f1 = font(F_DISPLAY, int(W * 0.062))
    fnum = font(F_NUM, int(W * 0.085))
    f2 = font(F_BODY, int(W * 0.036))

    cols, gap = 3, int(W * 0.022)
    cote = int(min((W * 0.78 - gap * (cols - 1)) / cols, H * 0.13))
    x0 = (W - (cote * cols + gap * (cols - 1))) // 2
    y0 = int(H * 0.30)
    for i in range(9):
        av = rebond(fenetre(t, 0.25 + i * 0.1, 0.45))
        if av <= 0:
            continue
        r, c = divmod(i, cols)
        vign = R.vignettes[i].resize((cote, cote))
        taille = max(2, int(cote * (0.8 + 0.2 * av)))
        v = vign.resize((taille, taille)).convert("RGBA")
        v.putalpha(int(255 * av))
        masque = Image.new("L", (taille, taille), 0)
        ImageDraw.Draw(masque).rounded_rectangle([0, 0, taille - 1, taille - 1],
                                                 radius=int(taille * 0.1), fill=int(255 * av))
        cx = x0 + c * (cote + gap) + cote // 2
        cy = y0 + r * (cote + gap) + cote // 2
        img.paste(v, (cx - taille // 2, cy - taille // 2), masque)

    compte = int(14 * sortie(fenetre(t, 0.4, 1.4)))
    txt = f"{compte} photos"
    d.text(((W - larg(d, txt, fnum)) // 2, int(H * 0.19)), txt, font=fnum,
           fill=tuple(ORANGE) + (255,))
    bloc_bas(img, W, H, "Toutes celles où tu es,\net aucune autre.", "En quelques secondes",
             sortie(fenetre(t, 1.2, 0.6)), sortie(fenetre(t, 1.7, 0.5)))

def scene_paiement(img, t, duree, W, H, R):
    d = ImageDraw.Draw(img, "RGBA")
    f1 = font(F_DISPLAY, int(W * 0.062))
    fb = font(F_BODY_B, int(W * 0.04))
    fnum = font(F_NUM, int(W * 0.075))

    lignes = ["Wave", "Orange Money", "MTN Money", "Espèces à la borne"]
    y = int(H * 0.30)
    hb = int(W * 0.115)
    for i, nom in enumerate(lignes):
        av = sortie(fenetre(t, 0.2 + i * 0.12, 0.45))
        if av <= 0:
            continue
        choisi = (i == 0 and t > 1.5)
        x0 = int(W * 0.12)
        x1 = int(W * 0.88)
        yy = y + i * int(hb * 1.25) + int((1 - av) * W * 0.04)
        contour = tuple(ORANGE) + (int(255 * av),) if choisi else (60, 80, 84, int(255 * av))
        d.rounded_rectangle([x0, yy, x1, yy + hb], radius=hb // 2,
                            fill=(19, 48, 56, int(220 * av)),
                            outline=contour,
                            width=max(2, int(W * 0.006)))
        r = int(W * 0.022)
        cx, cy = x0 + int(W * 0.06), yy + hb // 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=tuple(ORANGE) + (int(255 * av),) if choisi else (110, 130, 134, int(255 * av)),
                  width=max(2, int(W * 0.005)))
        if choisi:
            d.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], fill=tuple(ORANGE) + (255,))
        d.text((x0 + int(W * 0.11), cy - haut(d, nom, fb) // 2 - int(W * 0.006)), nom,
               font=fb, fill=tuple(SAND) + (int(255 * av),))

    a = sortie(fenetre(t, 0.9, 0.5))
    txt = "450 F la photo"
    d.text(((W - larg(d, txt, fnum)) // 2, int(H * 0.19)), txt, font=fnum, fill=tuple(SAND) + (int(255 * a),))
    bloc_bas(img, W, H, "Tu paies, tu télécharges.", "Qualité d'origine, lien personnel",
             sortie(fenetre(t, 1.9, 0.5)), sortie(fenetre(t, 2.3, 0.5)))


def scene_impression(img, t, duree, W, H, R):
    d = ImageDraw.Draw(img, "RGBA")
    f1 = font(F_DISPLAY, int(W * 0.062))
    f2 = font(F_BODY, int(W * 0.036))

    pw = int(W * 0.58)
    ph = int(pw * 0.5)
    px = (W - pw) // 2
    py = int(H * 0.43)

    sortie_photo = sortie(fenetre(t, 0.5, 1.5))
    tw = int(pw * 0.46)
    th = int(tw * 1.34)
    tx = px + (pw - tw) // 2
    ty = py - int(th * sortie_photo) + int(th * 0.1)
    photo = Image.new("RGBA", (tw, th), (255, 255, 255, 255))
    m = int(tw * 0.07)
    photo.paste(R.vignettes[4].resize((tw - 2 * m, th - 3 * m)), (m, m))
    img.alpha_composite(photo, (tx, ty))

    d.rounded_rectangle([px, py, px + pw, py + ph], radius=int(W * 0.02), fill=(30, 42, 46, 255))
    d.rounded_rectangle([px + int(pw * 0.2), py - int(W * 0.008), px + int(pw * 0.8), py + int(W * 0.012)],
                        radius=int(W * 0.006), fill=(12, 18, 20, 255))
    d.rounded_rectangle([px + int(pw * 0.08), py + int(ph * 0.55), px + int(pw * 0.34), py + int(ph * 0.75)],
                        radius=int(W * 0.008), fill=tuple(ORANGE) + (255,))
    r = int(pw * 0.02)
    d.ellipse([px + pw - int(pw * 0.14) - r, py + int(ph * 0.62) - r,
               px + pw - int(pw * 0.14) + r, py + int(ph * 0.62) + r], fill=tuple(GREEN) + (255,))

    bloc_bas(img, W, H, "Ou repars avec\nle tirage papier.", "500 F, imprimé sur place en quelques secondes",
             sortie(fenetre(t, 1.0, 0.6)), sortie(fenetre(t, 1.6, 0.5)))

def scene_fin(img, t, duree, W, H, R):
    d = ImageDraw.Draw(img, "RGBA")
    a = rebond(fenetre(t, 0.1, 0.6))
    taille = int(R.logo.width * (0.8 + 0.2 * a))
    lg = R.logo.resize((taille, taille), Image.LANCZOS)
    img.alpha_composite(lg, ((W - taille) // 2, int(H * 0.30) - taille // 2))

    f1 = font(F_DISPLAY, int(W * 0.1))
    mot_y = int(H * 0.44)
    x = (W - larg(d, "MYFACE", f1)) // 2
    d.text((x, mot_y), "MY", font=f1, fill=tuple(SAND) + (int(255 * a),))
    d.text((x + larg(d, "MY", f1), mot_y), "FACE", font=f1, fill=tuple(ORANGE) + (int(255 * a),))

    texte_centre(d, "myfaceci.online", font(F_BODY_B, int(W * 0.052)), W, int(H * 0.57),
                 SAND, sortie(fenetre(t, 0.7, 0.5)))
    texte_centre(d, "WhatsApp 07 58 50 94 03", font(F_BODY, int(W * 0.042)), W, int(H * 0.65),
                 GRIS, sortie(fenetre(t, 1.0, 0.5)))
    texte_centre(d, "Mariages · Diplômes · Entreprises · Abidjan",
                 font(F_BODY, int(W * 0.032)), W, int(H * 0.74), GRIS, sortie(fenetre(t, 1.3, 0.5)))


SCENES = [
    (scene_logo, 3.2),
    (scene_probleme, 4.2),
    (scene_qr, 3.4),
    (scene_selfie, 4.2),
    (scene_photos, 4.4),
    (scene_paiement, 4.0),
    (scene_impression, 3.6),
    (scene_fin, 3.4),
]
FONDU = 0.35


def rendre(W, H, sortie_fichier):
    R = Ressources(W)
    base = fond(W, H)
    total = sum(dur for _, dur in SCENES)
    nb = int(total * FPS)
    print(f"  {sortie_fichier.name} : {W}x{H}, {total:.1f} s, {nb} images")

    # On impose le moteur FFMPEG d'OpenCV : le moteur Windows (MSMF) ecrit un
    # fichier quasiment non compresse (220 Mo pour 30 s), inutilisable pour
    # WhatsApp. En mp4v, le meme rendu tient dans quelques megaoctets.
    writer = cv2.VideoWriter(str(sortie_fichier), cv2.CAP_FFMPEG,
                             cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    if not writer.isOpened():
        raise SystemExit("Aucun codec video disponible")

    debuts = []
    c = 0.0
    for _, dur in SCENES:
        debuts.append(c)
        c += dur

    for n in range(nb):
        t = n / FPS
        img = base.copy().convert("RGBA")
        for (fn, dur), debut in zip(SCENES, debuts):
            fin = debut + dur
            if t < debut - FONDU or t > fin:
                continue
            calque = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            fn(calque, t - debut, dur, W, H, R)
            opacite = 1.0
            if t > fin - FONDU:
                opacite = borne01((fin - t) / FONDU)
            if opacite < 1:
                calque.putalpha(calque.split()[3].point(lambda v: int(v * opacite)))
            img.alpha_composite(calque)
        cadre = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
        writer.write(cadre)
        if n % 60 == 0:
            print(f"    {n}/{nb}", end="\r")
    writer.release()
    print(f"    termine : {sortie_fichier.stat().st_size // 1024} Ko")


def main():
    quoi = sys.argv[1] if len(sys.argv) > 1 else "tout"
    if quoi in ("tout", "vertical"):
        rendre(1080, 1920, BASE / "myface-parcours-9x16.mp4")
    if quoi in ("tout", "carre"):
        rendre(1080, 1080, BASE / "myface-parcours-1x1.mp4")
    if quoi in ("tout", "leger"):
        rendre(720, 1280, BASE / "myface-parcours-9x16-leger.mp4")


if __name__ == "__main__":
    main()
