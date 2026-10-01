# -*- coding: utf-8 -*-
"""Kit motion design MYFACE : le telephone et la borne sur fond vert.

Pour chaque geste du film (un doigt qui touche un bouton), une image de
depart 1080 x 1920 : l'appareil avec le VRAI ecran de l'application dedans,
sur un fond vert uni (#00B140) qu'on retire au montage. On la donne a un
outil d'IA en mode image vers video (Kling, Veo, Runway, Hailuo) avec la
consigne du plan : voir fiches/sources-html/motion-design-myface.html.

Entrees
- captures/iphone/*.png          les ecrans du parcours invite (1206 x 2622)
- captures/borne/01-accueil.png  l'accueil de la borne (1080 x 1920)
- motion-design/sources/3.jpg    la borne de face, ecran vert (photo fournie)
- motion-design/sources/4.jpg    la borne de trois quarts, tirage dans la fente
- la photo du tirage, prise dans l'evenement de demonstration

Sorties (hors git : elles montrent les photos de la demo)
- fond-vert/  images de depart, fond vert uni, sans ombre
- detoure/    les memes sur fond transparent, plus les appareils a ecran vide
- ecrans/     les ecrans seuls (barre d'etat comprise), pour l'incrustation
- elements/   logo, coins du cadre, onde de toucher, coche, fonds, mur de photos
- guides/storyboard.png  les plans dans l'ordre et l'endroit ou le doigt touche

    python motion-design/preparer_motion.py
"""

import random
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(RACINE / "affiches"))
sys.path.insert(0, str(RACINE / "affiches" / "sources"))

from generer_affiches import (F_BODY, F_BODY_B, F_DISPLAY, GREEN, INK, ORANGE,  # noqa: E402
                              SAND, fond_motif, fond_wax, logo_icone)
from preparer_visuels import calque_perspective, coins, masque_vert  # noqa: E402

VERT = (0, 177, 64)  # #00B140 : le vert d'incrustation standard
W, H = 1080, 1920
LARGEUR_ECRAN = 640  # largeur de l'ecran du telephone dans l'image

CAPTURES = RACINE / "captures" / "iphone"
ACCUEIL_BORNE = RACINE / "captures" / "borne" / "01-accueil.png"
# Les autres ecrans de la borne, en gros plan : le panier avec l'impression
# cochee et le paiement en especes (points touches, en part de l'ecran).
ECRANS_BORNE = {
    "impression": (RACINE / "captures" / "borne" / "02-panier-impression.png", (0.18, 0.758)),
    "especes": (RACINE / "captures" / "borne" / "03-paiement-especes.png", (0.28, 0.766)),
}
SOURCES = ICI / "sources"
DEMO = RACINE / "watched-photos" / "6b3391d9-e2eb-4942-990b-ac1353cd170e"
PHOTO_TIRAGE = DEMO / "pexels-joshua-j-lewis-1577020288-27333351.jpg"
LEGENDE = "DÉMONSTRATION MYFACE"
F_LEGENDE = "C:/Windows/Fonts/GARA.TTF"  # proche du Cormorant Garamond du cadre de l'app

DOSSIERS = {n: ICI / n for n in ("fond-vert", "detoure", "ecrans", "elements", "guides")}

# Les ecrans du telephone. 11-panier est ecarte : la demo n'a aucun moyen de
# paiement configure et l'ecran affiche « paiement indisponible ».
ECRANS = ["01-accueil", "02-galerie", "03-visionneuse", "04-visages-regroupes",
          "05-photos-d-un-visage", "06-photos-d-un-visage-selectionnees",
          "07-scan-consentement", "08-scan-camera", "09-scan-recherche",
          "10-scan-resultats", "12-panier-paiement"]

# Le film, plan par plan : image de depart, endroit touche et geste.
# Pour le telephone, l'endroit est en part de la largeur et de la hauteur de
# la capture ; None = plan sans main (simple insert).
PLANS = [
    ("P01", "telephone-01-accueil", (0.50, 0.840), "Touche « Parcourir la galerie »"),
    ("P02", "telephone-02-galerie", (0.25, 0.250), "Touche une photo des mariés"),
    ("P03", "telephone-03-visionneuse", (0.50, 0.948), "Touche « Ajouter au panier »"),
    ("P04", "telephone-02-galerie", (0.75, 0.107), "Touche « Trouver mon visage »"),
    ("P05", "telephone-04-visages-regroupes", (0.21, 0.270), "Touche le visage de la mariée"),
    ("P06", "telephone-05-photos-d-un-visage", (0.50, 0.267), "Touche « Tout sélectionner »"),
    ("P07", "telephone-06-photos-d-un-visage-selectionnees", None, "Les 10 coches, image fixe"),
    ("P08", "telephone-02-galerie", (0.30, 0.107), "Touche « Scanner mon visage »"),
    ("P09", "telephone-07-scan-consentement", (0.50, 0.670), "Touche « J'accepte »"),
    ("P10", "telephone-08-scan-camera", (0.50, 0.753), "Touche « Prendre la photo »"),
    ("P11", "telephone-09-scan-recherche", None, "Recherche en cours, image fixe"),
    ("P12", "telephone-10-scan-resultats", (0.74, 0.794), "Touche « Voir le panier »"),
    ("P13", "telephone-12-panier-paiement", (0.29, 0.656), "Touche « Wave »"),
    ("P14", "borne-gros-plan-accueil", "borne", "Touche « Scanner mon visage » sur la borne"),
    ("P15", "borne-gros-plan-impression", "impression", "Touche « Imprimer » sur une photo"),
    ("P16", "borne-gros-plan-especes", "especes", "Touche « Espèces »"),
    ("P17", "borne-34-tirage", "fente", "Tire la photo hors de la fente"),
    ("P18", "tirage-10x15", "tirage", "Lève le tirage vers la caméra"),
]

# La fente d'impression sur la photo de trois quarts (4.jpg, en pixels).
FENTE_34 = (476, 737)

# Detourage de la borne : borne blanche sur fond gris clair (3.jpg) ou creme
# (4.jpg), trop proches pour un simple seuil de couleur (le corps blanc
# devenait transparent). On guide donc GrabCut : un cadre ou chercher, des
# zones sures de la borne (fente, lecteur, tete, socle, flanc) et des zones
# sures du fond (l'ombre au sol). Coordonnees en pixels de la photo source.
GRAINES = {
    "3.jpg": dict(
        cadre=(372, 22, 692, 1046),
        borne=[(430, 724, 515, 752), (560, 676, 608, 724), (480, 232, 580, 268),
               (384, 1004, 680, 1026), (500, 300, 560, 990)],
        fond=[],
    ),
    "4.jpg": dict(
        cadre=(368, 22, 778, 1046),
        borne=[(440, 724, 515, 752), (560, 676, 608, 724), (480, 232, 600, 268),
               (690, 650, 730, 950), (420, 1004, 740, 1026), (500, 300, 560, 990),
               (655, 300, 662, 540)],
        fond=[(745, 1040, 991, 1088), (778, 940, 991, 1088)],
    ),
}


# --------------------------------------------------------------------------
# Outils
# --------------------------------------------------------------------------
def masque_arrondi(taille, rayon, ss=4):
    m = Image.new("L", (taille[0] * ss, taille[1] * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, taille[0] * ss - 1, taille[1] * ss - 1],
                                        radius=int(rayon * ss), fill=255)
    return m.resize(taille, Image.LANCZOS)


def masque_quad(taille, quad, ss=4):
    m = Image.new("L", (taille[0] * ss, taille[1] * ss), 0)
    ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in quad], fill=255)
    return m.resize(taille, Image.LANCZOS)


def dilater(quad, d):
    """Agrandit le quadrilatere de `d` pixels environ, depuis son centre."""
    cx = sum(x for x, _ in quad) / 4
    cy = sum(y for _, y in quad) / 4
    out = []
    for x, y in quad:
        vx, vy = x - cx, y - cy
        n = max(1e-6, (vx * vx + vy * vy) ** 0.5)
        out.append((x + vx / n * d * 1.41, y + vy / n * d * 1.41))
    return out


def homographie(src, dst):
    a, b = [], []
    for (x, y), (X, Y) in zip(src, dst):
        a.append([x, y, 1, 0, 0, 0, -X * x, -X * y])
        b.append(X)
        a.append([0, 0, 0, x, y, 1, -Y * x, -Y * y])
        b.append(Y)
    h = np.linalg.solve(np.array(a, float), np.array(b, float))
    return np.append(h, 1.0).reshape(3, 3)


def projeter(hm, x, y):
    v = hm @ np.array([x, y, 1.0])
    return float(v[0] / v[2]), float(v[1] / v[2])


def toile(fond):
    return Image.new("RGBA", (W, H), (*fond, 255) if fond else (0, 0, 0, 0))


def sauver(img, dossier, nom):
    chemin = DOSSIERS[dossier] / f"{nom}.png"
    img.save(chemin)
    return chemin


# --------------------------------------------------------------------------
# Le telephone
# --------------------------------------------------------------------------
def ecran_complet(capture: Image.Image, largeur: int) -> Image.Image:
    """La capture sous une barre d'etat iOS (heure, reseau, batterie) de la
    couleur du haut de la page, coins arrondis, barre d'accueil en bas.
    Sans l'ilot : il fait partie du telephone (voir telephone())."""
    pt = largeur / 402.0
    hb = round(54 * pt)
    hc = round(capture.height * largeur / capture.width)
    cap = capture.convert("RGB").resize((largeur, hc), Image.LANCZOS)
    haut = np.asarray(cap.crop((0, 0, largeur, max(2, round(4 * pt))))).reshape(-1, 3).mean(axis=0)
    fond = tuple(int(v) for v in haut)
    encre = INK if sum(fond) / 3 > 150 else (255, 255, 255)

    ss = 3
    barre = Image.new("RGB", (largeur * ss, hb * ss), fond)
    d = ImageDraw.Draw(barre)

    def P(v):
        return v * pt * ss

    f = ImageFont.truetype(F_BODY_B, max(8, round(16.5 * pt * ss)))
    heure = "21:30"
    bb = d.textbbox((0, 0), heure, font=f)
    d.text((P(69) - (bb[2] - bb[0]) / 2 - bb[0], P(29.5) - (bb[1] + bb[3]) / 2), heure, font=f, fill=encre)
    # reseau : quatre barres
    x = P(294)
    for hh in (4.5, 7, 9.5, 12):
        d.rounded_rectangle([round(x), round(P(35) - P(hh)), round(x + P(3)), round(P(35))],
                            radius=max(1, round(P(0.8))), fill=encre)
        x += P(4.6)
    # wifi : trois arcs
    cx, cy = P(326), P(35.5)
    for r, col in ((12, encre), (9.6, fond), (7.6, encre), (5.2, fond), (3.2, encre)):
        d.pieslice([round(cx - P(r)), round(cy - P(r)), round(cx + P(r)), round(cy + P(r))], 225, 315, fill=col)
    # batterie
    bx, by = P(342), P(23.5)
    d.rounded_rectangle([round(bx), round(by), round(bx + P(25)), round(by + P(12))],
                        radius=round(P(3.6)), outline=encre, width=max(1, round(P(1.1))))
    d.rounded_rectangle([round(bx + P(2.2)), round(by + P(2.2)), round(bx + P(18.7)), round(by + P(9.8))],
                        radius=max(1, round(P(1.8))), fill=encre)
    d.rounded_rectangle([round(bx + P(26.3)), round(by + P(4.2)), round(bx + P(27.8)), round(by + P(7.8))],
                        radius=max(1, round(P(0.7))), fill=encre)
    barre = barre.resize((largeur, hb), Image.LANCZOS)

    img = Image.new("RGBA", (largeur, hb + hc), (*fond, 255))
    img.paste(barre, (0, 0))
    img.paste(cap, (0, hb))

    # barre d'accueil, posee par-dessus la page comme sur iOS
    bas = np.asarray(cap.crop((0, hc - round(14 * pt), largeur, hc))).mean()
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    lw, lh = 139 * pt, 5 * pt
    x0, y1 = (largeur - lw) / 2, img.height - 8 * pt
    ImageDraw.Draw(calque).rounded_rectangle(
        [round(x0), round(y1 - lh), round(x0 + lw), round(y1)], radius=max(1, round(lh / 2)),
        fill=(0, 0, 0, 165) if bas > 150 else (255, 255, 255, 205))
    img.alpha_composite(calque)
    img.putalpha(masque_arrondi(img.size, 60 * pt))
    return img


def hauteur_ecran(largeur):
    """Hauteur de ecran_complet() pour une capture iPhone 1206 x 2622."""
    return round(54 * largeur / 402.0) + round(2622 * largeur / 1206)


def telephone(capture, largeur=LARGEUR_ECRAN, ecran="ui"):
    """Telephone de face, facon iPhone 17 Pro : chassis titane graphite,
    bords noirs fins, ilot, boutons. ecran = "ui" (la capture), "vert" ou
    "vide" (transparent). Retourne (image RGBA, boite de l'ecran x, y, l, h)."""
    ss = 2
    pt = largeur / 402.0
    sw = largeur * ss
    if ecran == "ui":
        plein = ecran_complet(capture, sw)
    else:
        plein = Image.new("RGBA", (sw, hauteur_ecran(sw)), (*VERT, 255) if ecran == "vert" else (0, 0, 0, 0))
        plein.putalpha(Image.new("L", plein.size, 0) if ecran == "vide"
                       else masque_arrondi(plein.size, 60 * pt * ss, ss=2))
    sh = plein.height

    met = round(6 * ss * largeur / 640)
    bez = round(13 * ss * largeur / 640)
    marge = round(8 * ss)
    ow, oh = sw + 2 * (met + bez), sh + 2 * (met + bez)
    r_ecran = round(60 * pt * ss)
    r_ext = r_ecran + met + bez
    img = Image.new("RGBA", (ow + 2 * marge, oh + 2 * marge), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    X0 = Y0 = marge

    def bouton(cote, y, longueur):
        e, ep = round(3.5 * ss), round(8 * ss)
        x0, x1 = (X0 - e, X0 + ep) if cote == "g" else (X0 + ow - ep, X0 + ow + e)
        d.rounded_rectangle([x0, round(Y0 + y * oh), x1, round(Y0 + (y + longueur) * oh)],
                            radius=round(2.5 * ss), fill=(78, 80, 86))

    bouton("g", 0.185, 0.032)  # bouton Action
    bouton("g", 0.255, 0.062)  # volume +
    bouton("g", 0.335, 0.062)  # volume -
    bouton("d", 0.285, 0.095)  # marche / arret
    bouton("d", 0.545, 0.058)  # commande de l'appareil photo

    d.rounded_rectangle([X0, Y0, X0 + ow - 1, Y0 + oh - 1], radius=r_ext, fill=(62, 64, 69))
    i = round(1.5 * ss)
    d.rounded_rectangle([X0 + i, Y0 + i, X0 + ow - 1 - i, Y0 + oh - 1 - i], radius=r_ext - i,
                        outline=(122, 125, 132), width=max(1, round(1.2 * ss)))
    d.rounded_rectangle([X0 + met, Y0 + met, X0 + ow - 1 - met, Y0 + oh - 1 - met],
                        radius=r_ext - met, fill=(5, 5, 7))

    ex, ey = X0 + met + bez, Y0 + met + bez
    if ecran == "vide":
        # on perce l'ecran : le cadre seul, a poser par-dessus un ecran
        trou = masque_arrondi((sw, sh), r_ecran, ss=2)
        alpha = img.split()[3]
        alpha.paste(0, (ex, ey), trou)
        img.putalpha(alpha)
    else:
        img.alpha_composite(plein, (ex, ey))

    # ilot dynamique, avec sa lentille
    iw, ih = 125 * pt * ss, 37 * pt * ss
    ix, iy = ex + (sw - iw) / 2, ey + 11 * pt * ss
    d.rounded_rectangle([round(ix), round(iy), round(ix + iw), round(iy + ih)], radius=round(ih / 2), fill=(0, 0, 0))
    r = ih * 0.27
    lx, ly = ix + iw - ih * 0.55, iy + ih / 2
    d.ellipse([round(lx - r), round(ly - r), round(lx + r), round(ly + r)], fill=(18, 28, 38))

    final = img.resize((img.width // ss, img.height // ss), Image.LANCZOS)
    return final, (ex / ss, ey / ss, sw / ss, sh / ss)


def poser_telephone(tel, boite, fond):
    t = toile(fond)
    x, y = (W - tel.width) // 2, (H - tel.height) // 2
    t.alpha_composite(tel, (x, y))
    bx, by, bw, bh = boite
    return t, (x + bx, y + by, bw, bh)


# --------------------------------------------------------------------------
# La borne
# --------------------------------------------------------------------------
def detourer_borne(fichier, vert):
    """Masque de la borne (0 ou 1) par GrabCut guide, voir GRAINES."""
    im = cv2.imread(str(SOURCES / fichier))
    h, w = im.shape[:2]
    g = GRAINES[fichier]
    m = np.full((h, w), cv2.GC_BGD, np.uint8)
    x0, y0, x1, y1 = g["cadre"]
    m[y0:y1, x0:x1] = cv2.GC_PR_BGD
    ys, xs = np.where(vert)
    m[y0 + 8:y1 - 8, xs.min() - 30:xs.max() + 30] = cv2.GC_PR_FGD
    for a, b, c, d in g["borne"]:
        m[b:d, a:c] = cv2.GC_FGD
    blanc = im.min(axis=2) > 246  # le disque de la lumiere annulaire
    blanc[230:, :] = False
    m[blanc | vert] = cv2.GC_FGD
    for a, b, c, d in g["fond"]:
        m[b:d, a:c] = cv2.GC_BGD
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(im, m, None, bgd, fgd, 10, cv2.GC_INIT_WITH_MASK)
    fg = ((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)).astype(np.uint8)

    # on garde les gros morceaux, puis on bouche les trous (fente, ecran...)
    garde = np.zeros_like(fg)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg, 8)
    for k in range(1, n):
        if st[k, cv2.CC_STAT_AREA] > 1500:
            garde[lab == k] = 1
    n, lab, st, _ = cv2.connectedComponentsWithStats((1 - garde).astype(np.uint8), 4)
    for k in range(1, n):
        x, y, ww, hh, aire = st[k]
        if x > 0 and y > 0 and x + ww < w and y + hh < h and aire < 40000:
            garde[lab == k] = 1
    return garde


def borne_source(fichier, zone_marque):
    """Detourage, marque du fabricant effacee, vert du JPEG neutralise autour
    de l'ecran. Retourne (decoupe RGBA, coins de l'ecran)."""
    im = Image.open(SOURCES / fichier).convert("RGB")
    a = np.asarray(im).astype(int)
    vert = masque_vert(a)
    quad = coins(vert)
    alpha = cv2.GaussianBlur(detourer_borne(fichier, vert).astype(np.float32), (0, 0), 0.8)

    # la marque du fabricant est gommee par reconstruction (inpainting) : un
    # aplat blanc se voyait sur le gris du chassis
    y0, y1, x0, x1 = zone_marque
    corps = np.median(a[y0:y1, x0:x1].reshape(-1, 3), axis=0)
    texte = np.zeros(a.shape[:2], np.uint8)
    texte[y0:y1, x0:x1] = (np.abs(a[y0:y1, x0:x1] - corps).sum(axis=2) > 24) * 255
    texte = cv2.dilate(texte, np.ones((5, 5), np.uint8))
    bgr = cv2.inpaint(np.ascontiguousarray(np.asarray(im)[:, :, ::-1]), texte, 6, cv2.INPAINT_TELEA)
    decoupe = Image.fromarray(np.ascontiguousarray(bgr[:, :, ::-1])).convert("RGBA")
    decoupe.putalpha(Image.fromarray((alpha * 255).astype(np.uint8), "L"))

    arr = np.asarray(decoupe).copy()
    r, g, b = (arr[..., k].astype(int) for k in range(3))
    m = np.maximum(r, b)
    arr[..., 1] = np.where(g > m + 10, m, g).astype(np.uint8)
    return Image.fromarray(arr, "RGBA"), quad


def poser_borne(decoupe, quad, ui, echelle, decalage, fond, ecran="ui"):
    """La borne agrandie sur la toile, l'ecran remplace. Retourne (image,
    homographie ecran de l'app -> toile) pour placer les points de toucher."""
    grand = decoupe.convert("RGBa").resize(
        (round(decoupe.width * echelle), round(decoupe.height * echelle)), Image.LANCZOS).convert("RGBA")
    net = grand.convert("RGB").filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    grand = Image.merge("RGBA", (*net.split(), grand.split()[3]))

    calque = toile(None)
    calque.paste(grand, (round(decalage[0]), round(decalage[1])))
    q = [(x * echelle + decalage[0], y * echelle + decalage[1]) for x, y in quad]
    q = dilater(q, max(2, echelle * 1.2))
    masque = masque_quad((W, H), q)
    if ecran == "ui":
        couche = calque_perspective((W, H), ui, q)
    elif ecran == "vert":
        couche = toile(VERT)
    else:
        couche = toile(None)
    calque.paste(couche, (0, 0), masque)

    t = toile(fond)
    t.alpha_composite(calque)
    hm = homographie([(0, 0), (ui.width, 0), (ui.width, ui.height), (0, ui.height)], q)
    return t, hm


def cadrage_plein(decoupe, hauteur=1740, bas=90):
    bx0, by0, bx1, by1 = decoupe.getbbox()
    e = hauteur / (by1 - by0)
    return e, (W / 2 - (bx0 + bx1) / 2 * e, H - bas - by1 * e)


def cadrage_gros_plan(quad, part_largeur=0.62, centre_y=0.42):
    xs = [x for x, _ in quad]
    ys = [y for _, y in quad]
    e = part_largeur * W / (max(xs) - min(xs))
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    return e, (W / 2 - cx * e, centre_y * H - cy * e)


def bouton_scanner_borne(ui):
    """Centre du bouton « Scanner mon visage » de l'accueil de la borne : a
    droite du bouton orange « Parcourir la galerie », symetrique."""
    a = np.asarray(ui.convert("RGB")).astype(int)
    orange = (np.abs(a[..., 0] - 242) < 30) & (np.abs(a[..., 1] - 106) < 35) & (np.abs(a[..., 2] - 27) < 45)
    lignes = np.where(orange.sum(axis=1) > 100)[0]
    lignes = lignes[lignes > a.shape[0] * 0.5]
    ys, xs = np.where(orange[lignes.min():lignes.max() + 1])
    cx_orange = (xs.min() + xs.max()) / 2
    return a.shape[1] - cx_orange, lignes.min() + (lignes.max() - lignes.min()) / 2


# --------------------------------------------------------------------------
# Le tirage 10 x 15
# --------------------------------------------------------------------------
def tirage(largeur=760, ss=2):
    """Le tirage comme le cadre de l'app : papier creme, photo, legende en
    capitales espacees."""
    L = largeur * ss
    Ht = round(L * 1.5)
    img = Image.new("RGB", (L, Ht), (250, 247, 242))
    m = round(L * 0.055)
    bas = round(L * 0.2)
    pw, ph = L - 2 * m, Ht - m - bas
    photo = Image.open(PHOTO_TIRAGE)
    photo.draft("RGB", (pw * 2, ph * 2))
    photo = ImageOps.fit(photo.convert("RGB"), (pw, ph), Image.LANCZOS, centering=(0.5, 0.4))
    img.paste(photo, (m, m))
    d = ImageDraw.Draw(img)
    d.rectangle([m - 1, m - 1, m + pw, m + ph], outline=(222, 217, 208), width=max(1, ss))
    f = ImageFont.truetype(F_LEGENDE, round(L * 0.043))
    espace = 0.22 * f.size
    total = sum(d.textlength(c, font=f) for c in LEGENDE) + espace * (len(LEGENDE) - 1)
    x = (L - total) / 2
    bb = d.textbbox((0, 0), LEGENDE, font=f)
    y = m + ph + (bas - (bb[3] - bb[1])) / 2 - bb[1]
    for c in LEGENDE:
        d.text((x, y), c, font=f, fill=INK)
        x += d.textlength(c, font=f) + espace
    return img.convert("RGBA")


def poser_tirage(fond, angle=-3, ss=2):
    t = tirage(ss=ss).rotate(angle, resample=Image.BICUBIC, expand=True)
    t = t.convert("RGBa").resize((t.width // ss, t.height // ss), Image.LANCZOS).convert("RGBA")
    img = toile(fond)
    x, y = (W - t.width) // 2, (H - t.height) // 2 - 40
    img.alpha_composite(t, (x, y))
    return img, (x + t.width / 2, y + t.height * 0.93)


# --------------------------------------------------------------------------
# Elements de montage
# --------------------------------------------------------------------------
def elements():
    out = DOSSIERS["elements"]

    for nom, plaque, visage, texte in (("logo-myface-sur-fonce", SAND, INK, SAND),
                                       ("logo-myface-sur-clair", INK, SAND, INK)):
        taille = 240
        ic = logo_icone(taille, plate=plaque, face=visage)
        f = ImageFont.truetype(F_DISPLAY, int(taille * 0.62))
        mesure = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
        wmy, wface = mesure.textlength("MY", font=f), mesure.textlength("FACE", font=f)
        img = Image.new("RGBA", (int(taille * 1.28 + wmy + wface + taille * 0.12), taille), (0, 0, 0, 0))
        img.paste(ic, (0, 0), ic)
        d = ImageDraw.Draw(img)
        bb = d.textbbox((0, 0), "MYFACE", font=f)
        tx, ty = int(taille * 1.28), (taille - (bb[3] - bb[1])) // 2 - bb[1]
        d.text((tx, ty), "MY", font=f, fill=texte)
        d.text((tx + wmy, ty), "FACE", font=f, fill=ORANGE)
        img.save(out / f"{nom}.png")

    # les coins du cadre (la signature du logo) : trois orange, un vert
    n, ss = 1080, 3
    N = n * ss
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m, arm, lw = 40 * ss, 230 * ss, 30 * ss

    def coin(p0, p1, p2, col):
        d.line([p0, p1], fill=col, width=lw)
        d.line([p1, p2], fill=col, width=lw)
        for px, py in (p0, p1, p2):
            d.ellipse([px - lw / 2, py - lw / 2, px + lw / 2, py + lw / 2], fill=col)

    coin((m, m + arm), (m, m), (m + arm, m), ORANGE)
    coin((N - m - arm, m), (N - m, m), (N - m, m + arm), ORANGE)
    coin((m, N - m - arm), (m, N - m), (m + arm, N - m), ORANGE)
    coin((N - m - arm, N - m), (N - m, N - m), (N - m, N - m - arm), GREEN)
    img.resize((n, n), Image.LANCZOS).save(out / "cadre-coins.png")

    # l'onde du toucher : a agrandir de 30 % a 120 % en s'effacant
    n = 480
    N = n * ss
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = N / 2
    for r, w, a in ((0.46, 0.035, 255), (0.30, 0.02, 150)):
        d.ellipse([c - N * r, c - N * r, c + N * r, c + N * r], outline=(*ORANGE, a), width=int(N * w))
    d.ellipse([c - N * 0.11, c - N * 0.11, c + N * 0.11, c + N * 0.11], fill=(*ORANGE, 200))
    img.resize((n, n), Image.LANCZOS).save(out / "onde-toucher.png")

    # la coche de selection
    n = 240
    N = n * ss
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, N - 1, N - 1], fill=(*ORANGE, 255))
    w = int(N * 0.09)
    pts = [(N * 0.28, N * 0.52), (N * 0.44, N * 0.68), (N * 0.73, N * 0.36)]
    d.line(pts, fill=(255, 255, 255, 255), width=w, joint="curve")
    for px, py in pts:
        d.ellipse([px - w / 2, py - w / 2, px + w / 2, py + w / 2], fill=(255, 255, 255, 255))
    img.resize((n, n), Image.LANCZOS).save(out / "coche.png")

    # les fonds de la marque
    for nom, sombre, pagne in (("fond-encre", True, False), ("fond-encre-pagne", True, True),
                               ("fond-sable", False, False), ("fond-sable-pagne", False, True)):
        img = toile(INK if sombre else SAND)
        fond_motif(img, W, H, sombre)
        if pagne:
            fond_wax(img, ImageDraw.Draw(img), W, H, sombre)
        img.convert("RGB").save(out / f"{nom}.png")

    # le mur de photos de l'accroche : a faire defiler tres vite vers le haut
    vignettes = []
    for p in sorted(DEMO.glob("*.jpg")):
        im = Image.open(p)
        im.draft("RGB", (520, 780))
        vignettes.append(im.convert("RGB"))
    cols, gap, hauteur = 3, 14, 5400
    cw = (W - gap * (cols + 1)) // cols
    rng = random.Random(7)
    img = Image.new("RGB", (W, hauteur), INK)
    for c in range(cols):
        y = gap - c * cw // 3
        while y < hauteur:
            hcell = cw if rng.random() < 0.5 else int(cw * 1.25)
            tuile = ImageOps.fit(rng.choice(vignettes), (cw, hcell), Image.LANCZOS, centering=(0.5, 0.35))
            img.paste(tuile, (gap + c * (cw + gap), y), masque_arrondi((cw, hcell), 18, ss=2))
            y += hcell + gap
    img.save(out / "mur-de-photos.jpg", quality=90)


# --------------------------------------------------------------------------
# Le storyboard
# --------------------------------------------------------------------------
def storyboard(cadres, points):
    tw, th, pad, leg, cols = 270, 480, 24, 96, 6
    rows = (len(PLANS) + cols - 1) // cols
    haut = 120
    img = Image.new("RGB", (pad + cols * (tw + pad), haut + rows * (th + leg + pad)), SAND)
    d = ImageDraw.Draw(img)
    ft = ImageFont.truetype(F_DISPLAY, 34)
    fs = ImageFont.truetype(F_BODY, 21)
    fn = ImageFont.truetype(F_BODY_B, 20)
    d.text((pad, 30), "MYFACE · motion design", font=ft, fill=INK)
    d.text((pad, 78), "Les plans dans l'ordre. Le rond orange : l'endroit où le doigt touche.", font=fs, fill=(51, 72, 77))
    for i, (pid, nom, _, action) in enumerate(PLANS):
        r, c = divmod(i, cols)
        x, y = pad + c * (tw + pad), haut + r * (th + leg + pad)
        img.paste(cadres[nom].convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        pt = points.get(pid)
        if pt:
            px, py = x + pt[0] * tw / W, y + pt[1] * th / H
            d.ellipse([px - 18, py - 18, px + 18, py + 18], outline=ORANGE, width=5)
            d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=ORANGE)
        d.rounded_rectangle([x + 8, y + 8, x + 66, y + 38], radius=10, fill=INK)
        d.text((x + 15, y + 10), pid, font=fn, fill=SAND)
        mots, ligne, lignes = action.split(), "", []
        for mot in mots:
            essai = (ligne + " " + mot).strip()
            if d.textlength(essai, font=fs) > tw and ligne:
                lignes.append(ligne)
                ligne = mot
            else:
                ligne = essai
        lignes.append(ligne)
        for k, l in enumerate(lignes[:3]):
            d.text((x, y + th + 8 + k * 27), l, font=fs, fill=INK)
    img.save(DOSSIERS["guides"] / "storyboard.png")


# --------------------------------------------------------------------------
def main():
    for p in DOSSIERS.values():
        p.mkdir(parents=True, exist_ok=True)
    cadres, points = {}, {}

    # le telephone, un ecran par image
    boites = {}
    for nom in ECRANS:
        cap = Image.open(CAPTURES / f"{nom}.png")
        sauver(ecran_complet(cap, cap.width), "ecrans", f"telephone-{nom}")
        tel, boite = telephone(cap)
        for dossier, fond in (("fond-vert", VERT), ("detoure", None)):
            img, b = poser_telephone(tel, boite, fond)
            sauver(img, dossier, f"telephone-{nom}")
        cadres[f"telephone-{nom}"] = poser_telephone(tel, boite, VERT)[0]
        boites[f"telephone-{nom}"] = b
        print(f"  telephone-{nom}")
    tel, boite = telephone(None, ecran="vert")
    sauver(poser_telephone(tel, boite, VERT)[0], "fond-vert", "telephone-ecran-vert")
    tel, boite = telephone(None, ecran="vide")
    img, b = poser_telephone(tel, boite, None)
    sauver(img, "detoure", "telephone-cadre")
    print(f"  ecran du telephone dans l'image : x {b[0]:.0f}, y {b[1]:.0f}, {b[2]:.0f} x {b[3]:.0f}")

    hb = round(54 * LARGEUR_ECRAN / 402.0)
    for pid, nom, cible, _ in PLANS:
        if nom in boites and isinstance(cible, tuple):
            x, y, bw, bh = boites[nom]
            points[pid] = (x + cible[0] * bw, y + hb + cible[1] * (bh - hb))

    # la borne : de face (plein cadre et gros plan), de trois quarts
    ui = Image.open(ACCUEIL_BORNE).convert("RGB")
    Image.open(ACCUEIL_BORNE).save(DOSSIERS["ecrans"] / "borne-accueil.png")
    sx, sy = bouton_scanner_borne(ui)
    face, quad_face = borne_source("3.jpg", (276, 299, 596, 660))
    trois, quad_34 = borne_source("4.jpg", (272, 302, 590, 676))

    for nom, dec, quad, cadrage in (("borne-face", face, quad_face, cadrage_plein(face)),
                                    ("borne-gros-plan", face, quad_face, cadrage_gros_plan(quad_face)),
                                    ("borne-34", trois, quad_34, cadrage_plein(trois))):
        e, dec_xy = cadrage
        suffixe = "tirage" if nom == "borne-34" else "accueil"
        for dossier, fond in (("fond-vert", VERT), ("detoure", None)):
            img, hm = poser_borne(dec, quad, ui, e, dec_xy, fond)
            sauver(img, dossier, f"{nom}-{suffixe}")
        cadres[f"{nom}-{suffixe}"] = poser_borne(dec, quad, ui, e, dec_xy, VERT)[0]
        sauver(poser_borne(dec, quad, ui, e, dec_xy, VERT, ecran="vert")[0], "fond-vert", f"{nom}-ecran-vert")
        sauver(poser_borne(dec, quad, ui, e, dec_xy, None, ecran="vide")[0], "detoure", f"{nom}-cadre")
        if nom == "borne-gros-plan":
            points["P14"] = projeter(hm, sx, sy)
            for (cle, (fichier, (fx, fy))), pid in zip(ECRANS_BORNE.items(), ("P15", "P16")):
                autre = Image.open(fichier).convert("RGB")
                autre.save(DOSSIERS["ecrans"] / f"borne-{cle}.png")
                for dossier, fond in (("fond-vert", VERT), ("detoure", None)):
                    img, hm2 = poser_borne(dec, quad, autre, e, dec_xy, fond)
                    sauver(img, dossier, f"borne-gros-plan-{cle}")
                cadres[f"borne-gros-plan-{cle}"] = poser_borne(dec, quad, autre, e, dec_xy, VERT)[0]
                points[pid] = projeter(hm2, fx * autre.width, fy * autre.height)
        if nom == "borne-34":
            points["P17"] = (FENTE_34[0] * e + dec_xy[0], FENTE_34[1] * e + dec_xy[1])
        print(f"  {nom} (agrandie x{e:.2f})")

    # le tirage seul
    for dossier, fond in (("fond-vert", VERT), ("detoure", None)):
        img, prise = poser_tirage(fond)
        sauver(img, dossier, "tirage-10x15")
    cadres["tirage-10x15"] = poser_tirage(VERT)[0]
    points["P18"] = prise
    print("  tirage-10x15")

    elements()
    print("  elements")
    storyboard(cadres, points)
    print("  guides/storyboard.png")
    for pid, (x, y) in sorted(points.items()):
        print(f"    {pid} : x {x:.0f}, y {y:.0f}")


if __name__ == "__main__":
    main()
