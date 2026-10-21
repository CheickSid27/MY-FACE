# -*- coding: utf-8 -*-
"""Motion design MYFACE, version 4 (2 min) : la v2 / v3 completee pour un jury.

Reprend toutes les scenes de la v2 (v2/rendre_film_v2.py, inchange) et ajoute :
- le photographe qui depose ses photos ;
- l'IA qui detecte les visages et regroupe les photos de chaque invite ;
- le selfie jamais enregistre, efface apres la recherche ;
- le paiement Mobile Money et le telechargement en qualite d'origine ;
- les photos offertes par l'organisateur ;
- l'espace de l'organisateur, en direct ;
- le test reel a Abidjan (remise de diplomes de l'IIT : 119 photos, 12 commandes) ;
- les evenements vises, et « une solution ivoirienne ».
Les durees viennent de v4/montage_v4.py (calees sur la voix).

    python marketing/motion-design/v4/rendre_film_v4.py              -> v4/myface-motion-design-v4-muet.mp4
    python marketing/motion-design/v4/rendre_film_v4.py --apercu     -> v4/apercus/*.jpg (images de controle)
"""

import math
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from scipy import ndimage

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI.parent / "v2"))
sys.path.insert(0, str(ICI))
from rendre_film import (ELE, F_BOLD, F_DISPLAY, FPS, GREEN, H, INK, ORANGE, SAND, WHITE, W,  # noqa: E402
                         clamp, coller, coller_centre, doux, entree_cubique, etiquette, pastille, police,
                         ressort, sortie_cubique, texte, transformer)
from rendre_film_v2 import FilmV2, photos_demo  # noqa: E402
import montage_v4  # noqa: E402

SORTIE = ICI / "myface-motion-design-v4-muet.mp4"
EX, EY, EW, EH = 220, 221, 640, 1478     # ecran du telephone dans l'image
F_TXT = "C:/Windows/Fonts/segoeui.ttf"
CREME, GRIS, GRIS_CLAIR = (245, 241, 234), (120, 128, 130), (226, 220, 210)
# les visages sur la photo des maries (image 1080 x 1920) : centre x, centre y, taille
VISAGES = [(360, 505, 290), (722, 548, 262)]


# --------------------------------------------------------------------------
# Petits outils de dessin
# --------------------------------------------------------------------------
def rond(im, d, anneau=0, couleur=ORANGE):
    """Photo ronde, avec un anneau de couleur."""
    im = ImageOps.fit(im.convert("RGB"), (d, d), Image.LANCZOS)
    m = Image.new("L", (d * 3, d * 3), 0)
    ImageDraw.Draw(m).ellipse([0, 0, d * 3 - 1, d * 3 - 1], fill=255)
    m = m.resize((d, d), Image.LANCZOS)
    out = Image.new("RGBA", (d + 2 * anneau, d + 2 * anneau), (0, 0, 0, 0))
    if anneau:
        g = Image.new("L", (out.width * 3, out.height * 3), 0)
        ImageDraw.Draw(g).ellipse([0, 0, g.width - 1, g.height - 1], fill=255)
        disque = Image.new("RGBA", out.size, (*couleur, 255))
        disque.putalpha(g.resize(out.size, Image.LANCZOS))
        out.alpha_composite(disque)
    out.paste(im, (anneau, anneau), m)
    return out


def vignette(ph, w, h, r=18, bord=0):
    im = ImageOps.fit(ph.convert("RGB"), (w, h), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    im.putalpha(m)
    if not bord:
        return im
    out = Image.new("RGBA", (w + 2 * bord, h + 2 * bord), (0, 0, 0, 0))
    ImageDraw.Draw(out).rounded_rectangle([0, 0, out.width - 1, out.height - 1], radius=r + bord, fill=(250, 247, 242, 255))
    out.alpha_composite(im, (bord, bord))
    return out


def carte_blanche(w, h, r=34, couleur=(255, 255, 255, 255)):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=couleur)
    return im


def ombre_de(im, flou=18, force=0.35):
    o = Image.new("RGBA", (im.width + 80, im.height + 80), (0, 0, 0, 0))
    a = im.split()[3].point(lambda v: int(v * force))
    noir = Image.new("RGBA", im.size, (0, 0, 0, 255))
    noir.putalpha(a)
    o.alpha_composite(noir, (40, 40))
    return o.filter(ImageFilter.GaussianBlur(flou))


def etiquette_coche(base, txt, cx, cy, taille, t, t0, coche):
    """Pastille encre avec une coche orange a gauche."""
    if t < t0:
        return
    p = sortie_cubique((t - t0) / 0.3)
    f = police(F_DISPLAY, taille)
    bb = f.getbbox(txt)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    m = int(taille * 0.55)
    c = int(taille * 1.25)
    im = Image.new("RGBA", (tw + 3 * m + c, max(th, c) + 2 * m), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=im.height // 2, fill=(*INK, 235))
    im.alpha_composite(transformer(coche, c / coche.width), (m, (im.height - c) // 2))
    d.text((2 * m + c - bb[0], (im.height - th) / 2 - bb[1]), txt, font=f, fill=WHITE)
    coller_centre(base, im, cx, cy - 30 * (1 - p), 0.6 + 0.4 * ressort(clamp((t - t0) / 0.35)), 0, p)


def barre_etat(d, couleur=INK):
    d.text((40, 22), "21:47", font=police(F_BOLD, 24), fill=couleur)
    d.rounded_rectangle([EW - 92, 26, EW - 46, 46], radius=5, outline=couleur, width=2)
    d.rectangle([EW - 88, 30, EW - 58, 42], fill=couleur)


# --------------------------------------------------------------------------
# Le film
# --------------------------------------------------------------------------
class FilmV4(FilmV2):
    def __init__(self):
        super().__init__()
        rng = random.Random(42)
        self.sources = photos_demo(700)
        # -- depot : les photos qui volent vers MYFACE
        self.cartes_depot = []
        for k in range(22):
            ph = self.sources[(k * 5) % len(self.sources)]
            w, h = (300, 220) if ph.width > ph.height else (220, 300)
            self.cartes_depot.append({
                "img": vignette(ph, w, h, 10, 8),
                "x0": rng.uniform(60, 1020), "a0": rng.uniform(-35, 35),
                "cote": rng.uniform(-380, 380), "t0": 0.35 + k * 0.155,
            })
        self.halo = self._halo(900, (255, 170, 90))
        # -- l'IA : la ligne de balayage, les visages
        self.ligne_scan = self._ligne(W, 90)
        self.avatars = []
        for cx, cy, s in VISAGES:
            c = s * 0.62
            self.avatars.append(rond(self.net.crop((int(cx - c), int(cy - c), int(cx + c), int(cy + c))), 250, 9))
        self.vignettes_groupes = [[vignette(self.sources[(i * 3 + k * 7) % len(self.sources)], 132, 132, 16) for k in range(10)]
                                  for i in range(2)]
        # -- le selfie efface
        cx, cy, s = VISAGES[1]
        c = s * 0.72
        self.selfie_grand = rond(self.net.crop((int(cx - c), int(cy - c), int(cx + c), int(cy + c))), 520)
        self.tuiles = []
        pas = 40
        for ty in range(0, 520, pas):
            for tx in range(0, 520, pas):
                tuile = self.selfie_grand.crop((tx, ty, tx + pas, ty + pas))
                if tuile.getbbox() is None:
                    continue
                self.tuiles.append({"img": tuile, "x": tx - 260 + pas / 2, "y": ty - 260 + pas / 2,
                                    "vx": rng.uniform(-260, 260), "vy": rng.uniform(-620, -160),
                                    "d": rng.uniform(0, 0.55) + (ty / 520) * 0.25, "rot": rng.uniform(-200, 200)})
        self.bouclier = self._bouclier()
        # -- telechargement
        self.vignettes_ecran = [vignette(self.sources[k * 2 % len(self.sources)], 280, 280, 22) for k in range(6)]
        # -- photos offertes
        self.confettis = [{"vx": rng.uniform(-700, 700), "vy": rng.uniform(-1500, -500),
                           "col": rng.choice([ORANGE, GREEN, WHITE, (255, 196, 70), (64, 160, 220)]),
                           "w": rng.randint(14, 26), "h": rng.randint(8, 14), "rot": rng.uniform(-720, 720),
                           "d": rng.uniform(0, 0.25)} for _ in range(90)]
        self.cadeau = self._cadeau()
        # -- tableau de bord
        self.vignettes_tirages = [vignette(self.sources[(k * 4 + 1) % len(self.sources)], 92, 92, 14) for k in range(4)]
        # -- preuve
        self.epingle = self._epingle()
        # -- solution ivoirienne
        self.fond_sable_pagne = Image.open(ELE / "fond-sable-pagne.png").convert("RGBA")
        # -- la forme exacte de l'ecran (coins arrondis), prise dans le cadre du telephone
        trou = np.asarray(self.cadre_tel)[..., 3] < 20
        lab, _ = ndimage.label(trou)
        forme = (lab == lab[H // 2, W // 2])[EY:EY + EH, EX:EX + EW]
        self.masque_ecran = Image.fromarray((forme * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))

    # ------------------------------------------------------------ elements
    @staticmethod
    def _halo(d, couleur):
        im = Image.new("RGBA", (d, d), (0, 0, 0, 0))
        ImageDraw.Draw(im).ellipse([d * 0.2, d * 0.2, d * 0.8, d * 0.8], fill=(*couleur, 150))
        return im.filter(ImageFilter.GaussianBlur(d // 9))

    @staticmethod
    def _ligne(larg, haut):
        im = Image.new("RGBA", (larg, haut), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        mi = haut // 2
        for k in range(mi):
            a = int(200 * (1 - k / mi) ** 2)
            d.line([(0, mi - k), (larg, mi - k)], fill=(*ORANGE, a))
            d.line([(0, mi + k), (larg, mi + k)], fill=(*ORANGE, a))
        d.line([(0, mi), (larg, mi)], fill=(255, 220, 190, 255), width=3)
        return im

    @staticmethod
    def _bouclier():
        s = 2
        L, Hh = 340 * s, 400 * s
        im = Image.new("RGBA", (L, Hh), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        pts = [(L / 2, 0), (L, Hh * 0.15), (L * 0.95, Hh * 0.56), (L / 2, Hh), (L * 0.05, Hh * 0.56), (0, Hh * 0.15)]
        d.polygon(pts, fill=(*ORANGE, 255))
        inner = [(L / 2, Hh * 0.06), (L * 0.9, Hh * 0.19), (L * 0.86, Hh * 0.55), (L / 2, Hh * 0.92),
                 (L * 0.14, Hh * 0.55), (L * 0.1, Hh * 0.19)]
        d.line(inner + [inner[0]], fill=(255, 190, 140, 255), width=5 * s)
        ep = 15 * s
        d.arc([L * 0.37, Hh * 0.24, L * 0.63, Hh * 0.52], 180, 360, fill=WHITE, width=ep)
        d.line([(L * 0.37 + ep / 2, Hh * 0.38), (L * 0.37 + ep / 2, Hh * 0.45)], fill=WHITE, width=ep)
        d.line([(L * 0.63 - ep / 2, Hh * 0.38), (L * 0.63 - ep / 2, Hh * 0.45)], fill=WHITE, width=ep)
        d.rounded_rectangle([L * 0.3, Hh * 0.43, L * 0.7, Hh * 0.72], radius=16 * s, fill=WHITE)
        d.ellipse([L * 0.465, Hh * 0.52, L * 0.535, Hh * 0.58], fill=(*ORANGE, 255))
        d.rectangle([L * 0.485, Hh * 0.56, L * 0.515, Hh * 0.65], fill=(*ORANGE, 255))
        return im.resize((L // s, Hh // s), Image.LANCZOS)

    @staticmethod
    def _cadeau():
        s = 2
        L = 200 * s
        im = Image.new("RGBA", (L, L), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([L * 0.12, L * 0.42, L * 0.88, L * 0.95], radius=12 * s, fill=(*ORANGE, 255))
        d.rounded_rectangle([L * 0.06, L * 0.3, L * 0.94, L * 0.46], radius=10 * s, fill=(255, 140, 70, 255))
        d.rectangle([L * 0.44, L * 0.3, L * 0.56, L * 0.95], fill=(255, 226, 120, 255))
        d.ellipse([L * 0.22, L * 0.08, L * 0.5, L * 0.32], outline=(255, 226, 120, 255), width=12 * s)
        d.ellipse([L * 0.5, L * 0.08, L * 0.78, L * 0.32], outline=(255, 226, 120, 255), width=12 * s)
        return im.resize((L // s, L // s), Image.LANCZOS)

    @staticmethod
    def _epingle():
        s = 2
        L, Hh = 120 * s, 160 * s
        im = Image.new("RGBA", (L, Hh), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([0, 0, L, L], fill=(*ORANGE, 255))
        d.polygon([(L * 0.14, L * 0.72), (L * 0.86, L * 0.72), (L / 2, Hh)], fill=(*ORANGE, 255))
        d.ellipse([L * 0.3, L * 0.3, L * 0.7, L * 0.7], fill=WHITE)
        return im.resize((L // s, Hh // s), Image.LANCZOS)

    def telephone_ecran(self, img, ecran, cx, cy, echelle=1.0, angle=0.0, opacite=1.0):
        ecran = ecran.copy()
        ecran.putalpha(self.masque_ecran)
        calque = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        calque.alpha_composite(ecran, (EX, EY))
        calque.alpha_composite(self.cadre_tel)
        coller_centre(img, calque, cx, cy, echelle, angle, opacite)

    @staticmethod
    def point_ecran(x, y, cx, cy, echelle):
        """Un point de l'ecran du telephone -> sa place dans l'image."""
        return cx + (EX + x - W / 2) * echelle, cy + (EY + y - H / 2) * echelle

    # ------------------------------------------------------------ scenes
    def depot(self, t):
        img = self.fond(bokeh=True)
        centre = (W / 2, 840)
        arrivees = [c["t0"] + 0.85 for c in self.cartes_depot]
        recues = sum(1 for a in arrivees if t >= a)
        pouls = max([math.exp(-(t - a) / 0.12) for a in arrivees if t >= a] + [0.0])
        apparition = sortie_cubique(t / 0.5)
        coller_centre(img, self.halo, *centre, 0.8 + 0.25 * pouls, 0, 0.55 * apparition + 0.45 * pouls)
        d = ImageDraw.Draw(img)
        r = 230 * (0.6 + 0.4 * ressort(t / 0.6)) * (1 + 0.04 * pouls)
        d.ellipse([centre[0] - r, centre[1] - r, centre[0] + r, centre[1] + r], fill=(*INK, 255), outline=ORANGE, width=8)
        coller_centre(img, self.logo_fonce, *centre, 0.36 * apparition)
        for c in self.cartes_depot:
            u = (t - c["t0"]) / 0.85
            if not 0 <= u <= 1:
                continue
            e = entree_cubique(u) * 0.35 + sortie_cubique(u) * 0.65
            x0, y0 = c["x0"], 2080
            xc, yc = (x0 + centre[0]) / 2 + c["cote"], 1500
            x = (1 - e) ** 2 * x0 + 2 * (1 - e) * e * xc + e ** 2 * centre[0]
            y = (1 - e) ** 2 * y0 + 2 * (1 - e) * e * yc + e ** 2 * centre[1]
            coller_centre(img, c["img"], x, y, 1.0 - 0.85 * e, c["a0"] * (1 - e), 1 - clamp((u - 0.82) / 0.18))
        n = int(round(240 * recues / len(self.cartes_depot)))
        if t >= 0.9:
            texte(img, f"{n} photos", W / 2, 1200, 96, WHITE, opacite=clamp((t - 0.9) / 0.2))
        self.bandeau_haut(img, "Le photographe dépose ses photos", t, 0.2, WHITE, 48, 150)
        etiquette(img, "Aucun tri à faire", W / 2, 1390, 54, ORANGE, t, 3.0)
        return img

    def ia(self, t):
        bascule = 3.6
        if t < bascule:
            z = 1.0 + 0.05 * t / bascule
            img = Image.new("RGBA", (W, H))
            coller_centre(img, self.net, W / 2, H / 2, z)
            self.degrade_haut(img, 560, 215)

            def place(x, y):
                return W / 2 + (x - W / 2) * z, H / 2 + (y - H / 2) * z

            if 0.5 <= t <= 2.5:
                y = 260 + 1300 * doux((t - 0.5) / 2.0)
                coller(img, self.ligne_scan, 0, y - self.ligne_scan.height / 2)
            for i, (cx, cy, s) in enumerate(VISAGES):
                tp = 1.05 + 0.25 * i
                if t >= tp:
                    p = ressort((t - tp) / 0.35)
                    x, y = place(cx, cy)
                    coller_centre(img, self.coins, x, y, (s * z / 1036) * (1.6 - 0.6 * p), 0, clamp((t - tp) / 0.12))
                    if t >= tp + 0.3:
                        pastille(img, f"Personne {i + 1}", x, y + s * z * 0.62, True, 26, clamp((t - tp - 0.3) / 0.2))
            pastille(img, "IA de reconnaissance faciale", W / 2, 120, True, 34, clamp((t - 0.15) / 0.25),
                     0.8 + 0.2 * ressort(clamp((t - 0.15) / 0.35)))
            if t >= 0.6:
                texte(img, "Chaque visage est détecté", W / 2, 240, 56, WHITE, opacite=clamp((t - 0.6) / 0.25))
            if t > bascule - 0.45:
                img.alpha_composite(Image.new("RGBA", (W, H), (*INK, int(255 * clamp((t - bascule + 0.45) / 0.45)))))
            return img
        u = t - bascule
        img = self.fond()
        self.bandeau_haut(img, "Regroupées automatiquement", u, 0.1, WHITE, 56, 170)
        for i, (cx, cy, s) in enumerate(VISAGES):
            cible = (W / 2 - 240 if i == 0 else W / 2 + 240, 430)
            p = sortie_cubique(u / 0.6)
            x, y = cx + (cible[0] - cx) * p, cy + (cible[1] - cy) * p
            coller_centre(img, self.avatars[i], x, y, 0.8 + 0.2 * p)
            if u >= 0.45:
                pastille(img, f"Personne {i + 1}", cible[0], 600, True, 28, clamp((u - 0.45) / 0.2))
            for k, v in enumerate(self.vignettes_groupes[i]):
                t0 = 0.7 + k * 0.09 + i * 0.05
                if u >= t0:
                    r, c = divmod(k, 3)
                    vx = cible[0] - 146 + c * 146
                    vy = 760 + r * 146
                    coller_centre(img, v, vx, vy, ressort((u - t0) / 0.3) * 1.0)
            if u >= 1.9:
                texte(img, "10 photos", cible[0], 1360, 58, ORANGE, opacite=clamp((u - 1.9) / 0.2))
        if u >= 2.4:
            p = ressort((u - 2.4) / 0.35)
            texte(img, "Chaque invité, ses photos.", W / 2, 1640, 64, WHITE, echelle=1.25 - 0.25 * p,
                  opacite=clamp((u - 2.4) / 0.15))
        return img

    def confiance(self, t):
        img = self.fond()
        centre = (W / 2, 860)
        self.bandeau_haut(img, "Ton selfie", t, 0.15, WHITE, 72, 170)
        if t < 2.55:
            p = ressort(t / 0.45)
            coller_centre(img, self.selfie_grand, *centre, 0.6 + 0.4 * p, 0, clamp(t / 0.15))
        else:
            for tu in self.tuiles:
                u = t - 2.55 - tu["d"]
                if u < 0:
                    coller(img, tu["img"], centre[0] + tu["x"] - 20, centre[1] + tu["y"] - 20)
                    continue
                if u > 1.0:
                    continue
                x = centre[0] + tu["x"] + tu["vx"] * u
                y = centre[1] + tu["y"] + tu["vy"] * u + 300 * u * u
                coller_centre(img, tu["img"], x, y, 1 - 0.6 * u, tu["rot"] * u, 1 - u)
        if 0.3 <= t <= 2.6:
            d = ImageDraw.Draw(img)
            r = 300
            debut = (t * 220) % 360
            for k in range(12):
                a0 = debut + k * 30
                d.arc([centre[0] - r, centre[1] - r, centre[0] + r, centre[1] + r], a0, a0 + 16, fill=ORANGE, width=10)
            if t < 2.3:
                texte(img, "Recherche...", W / 2, 1250, 44, WHITE, chemin=F_BOLD, opacite=0.5 + 0.5 * math.sin(t * 9))
        etiquette_coche(img, "Jamais enregistré", W / 2, 1400, 50, t, 1.0, self.coche)
        if t >= 3.3:
            p = ressort((t - 3.3) / 0.45)
            coller_centre(img, self.bouclier, *centre, 0.4 + 0.6 * p, 0, clamp((t - 3.3) / 0.15))
        etiquette_coche(img, "Effacé après la recherche", W / 2, 1530, 50, t, 3.7, self.coche)
        return img

    def _ecran_telechargement(self, progres, coches):
        e = Image.new("RGBA", (EW, EH), (*CREME, 255))
        d = ImageDraw.Draw(e)
        barre_etat(d)
        d.text((EW / 2, 118), "Vos photos sont prêtes !", font=police(F_BOLD, 44), fill=INK, anchor="mm")
        d.text((EW / 2, 174), "10 photos · qualité d'origine", font=police(F_TXT, 30), fill=GRIS, anchor="mm")
        for k, v in enumerate(self.vignettes_ecran):
            r, c = divmod(k, 2)
            x, y = 30 + c * 300, 230 + r * 300
            e.alpha_composite(v, (x, y))
            if k < coches:
                d.ellipse([x + 216, y + 14, x + 266, y + 64], fill=GREEN)
                d.line([(x + 228, y + 40), (x + 238, y + 50), (x + 255, y + 28)], fill=WHITE, width=6)
                d.rounded_rectangle([x + 14, y + 226, x + 76, y + 264], radius=12, fill=(*INK, 230))
                d.text((x + 45, y + 245), "HD", font=police(F_BOLD, 22), fill=WHITE, anchor="mm")
        bx0, by0, bx1, by1 = 40, 1170, EW - 40, 1270
        if progres <= 0:
            d.rounded_rectangle([bx0, by0, bx1, by1], radius=50, fill=ORANGE)
            d.text((EW / 2, (by0 + by1) / 2), "Tout télécharger", font=police(F_BOLD, 34), fill=WHITE, anchor="mm")
        else:
            d.rounded_rectangle([bx0, by0, bx1, by1], radius=50, fill=(250, 210, 180))
            fin = bx0 + (bx1 - bx0) * min(1.0, progres)
            if fin - bx0 > 100:
                d.rounded_rectangle([bx0, by0, fin, by1], radius=50, fill=ORANGE if progres < 1 else GREEN)
            txt = f"Téléchargement {int(progres * 100)} %" if progres < 1 else "Téléchargées"
            d.text((EW / 2, (by0 + by1) / 2), txt, font=police(F_BOLD, 32), fill=WHITE if progres > 0.45 else INK, anchor="mm")
        return e

    def telechargement(self, t):
        img = self.fond(bokeh=True)
        moyens = ["Wave", "Orange Money", "MTN Money", "Moov Money"]
        xs = [140, 390, 668, 930]
        for i, m in enumerate(moyens):
            p = ressort((t - 0.1 - i * 0.12) / 0.3)
            if p > 0:
                pastille(img, m, xs[i], 95, m == "Wave", 28, clamp(p), p)
        etiquette_coche(img, "Paiement confirmé", W / 2, 205, 40, t, 1.3, self.coche)
        appui = 3.3
        progres = clamp((t - appui - 0.15) / 1.5)
        coches = int(clamp((t - appui - 1.7) / 0.6) * 6.999)
        ecran = self._ecran_telechargement(progres if t > appui + 0.1 else 0, coches)
        entree = ressort(clamp((t - 0.8) / 0.6))
        cx, cy, ech = W / 2, H / 2 + 120 + 9 * math.sin(t * 2), 0.86
        if t >= 0.8:
            self.telephone_ecran(img, ecran, cx, cy + (1 - entree) * 1200, ech, 0, clamp((t - 0.8) / 0.2))
        bouton = self.point_ecran(EW / 2, 1220, cx, cy, ech)
        self.onde_a(img, bouton, t, appui)
        self.main.dessiner(img, bouton, t, appui, "droite")
        etiquette(img, "Qualité d'origine", W / 2, 1840, 52, ORANGE, t, 5.4)
        return img

    def tirage_sort(self, t):
        img = super().tirage_sort(t)
        etiquette_coche(img, "Sans smartphone", W / 2, 1700, 48, t, 1.8, self.coche)
        etiquette_coche(img, "Sans Mobile Money", W / 2, 1830, 48, t, 2.5, self.coche)
        return img

    def qualite(self, t):
        z = 1 + 0.05 * t / 4
        img = Image.new("RGBA", (W, H))
        coller_centre(img, self.flou, W / 2, H / 2, z)
        split = W * doux((t - 0.45) / 1.5)
        if split > 0:
            net = transformer(self.net, z)
            ox, oy = (net.width - W) / 2, (net.height - H) / 2
            img.alpha_composite(net.crop((int(ox), int(oy), int(ox + split), int(oy + H))), (0, 0))
            d = ImageDraw.Draw(img)
            if split < W - 2:
                d.rectangle([split - 4, 0, split + 4, H], fill=ORANGE)
                d.ellipse([split - 38, H / 2 - 38, split + 38, H / 2 + 38], fill=ORANGE)
                d.text((split, H / 2), "‹ ›", font=police(F_BOLD, 34), fill=WHITE, anchor="mm")
        self.degrade_haut(img, 420, 180)
        if t < 1.7:
            etiquette(img, "Dans le groupe", W - 230, 150, 40, WHITE, t, 0.1)
        if split > 260:
            etiquette(img, "Avec MYFACE", 230 if t < 2.0 else W / 2, 150, 40, ORANGE, t, 0.9)
        etiquette(img, "Qualité d'origine, le soir même", W / 2, 1780, 46, WHITE, t, 2.1)
        return img

    def _carte_evenement(self, bascule):
        c = carte_blanche(900, 330)
        d = ImageDraw.Draw(c)
        d.text((44, 36), "Créer un événement", font=police(F_BOLD, 36), fill=INK)
        d.rounded_rectangle([44, 102, 856, 168], radius=16, fill=CREME, outline=GRIS_CLAIR, width=2)
        d.text((68, 135), "Mariage Awa & Koffi", font=police(F_TXT, 30), fill=INK, anchor="lm")
        d.text((44, 250), "Photos offertes par l'organisateur", font=police(F_BOLD, 30), fill=INK, anchor="lm")
        tx0, ty0 = 726, 220
        piste = tuple(int(GRIS_CLAIR[i] + (ORANGE[i] - GRIS_CLAIR[i]) * bascule) for i in range(3))
        d.rounded_rectangle([tx0, ty0, tx0 + 120, ty0 + 62], radius=31, fill=piste)
        kx = tx0 + 6 + 58 * bascule
        d.ellipse([kx, ty0 + 6, kx + 50, ty0 + 56], fill=WHITE)
        return c

    def _ecran_offert(self):
        e = Image.new("RGBA", (EW, EH), (*CREME, 255))
        d = ImageDraw.Draw(e)
        barre_etat(d)
        e.alpha_composite(transformer(self.cadeau, 1.2), (EW // 2 - 120, 150))
        d.text((EW / 2, 450), "Vos photos", font=police(F_DISPLAY, 46), fill=INK, anchor="mm")
        d.text((EW / 2, 510), "sont offertes !", font=police(F_DISPLAY, 46), fill=ORANGE, anchor="mm")
        d.text((EW / 2, 590), "Par les organisateurs du mariage.", font=police(F_TXT, 26), fill=GRIS, anchor="mm")
        d.text((48, 690), "Votre numéro, pour les recevoir", font=police(F_BOLD, 26), fill=INK)
        d.rounded_rectangle([40, 740, EW - 40, 830], radius=20, fill=WHITE, outline=GRIS_CLAIR, width=2)
        d.text((70, 785), "+225   07 •• •• •• ••", font=police(F_TXT, 32), fill=INK, anchor="lm")
        d.rounded_rectangle([40, 880, EW - 40, 980], radius=50, fill=ORANGE)
        d.text((EW / 2, 930), "Recevoir mes photos", font=police(F_BOLD, 34), fill=WHITE, anchor="mm")
        d.text((EW / 2, 1040), "Aucun paiement demandé", font=police(F_TXT, 26), fill=GREEN, anchor="mm")
        return e

    def offertes(self, t):
        img = self.fond(bokeh=True)
        bascule = doux((t - 1.05) / 0.25)
        carte = self._carte_evenement(bascule)
        p = sortie_cubique(t / 0.45)
        cx_c, cy_c = W / 2, 330 - 60 * (1 - p)
        coller_centre(img, ombre_de(carte), cx_c + 6, cy_c + 16, 1.0, 0, p)
        coller_centre(img, carte, cx_c, cy_c, 1.0, 0, p)
        inter = (cx_c - 450 + 726 + 60, cy_c - 165 + 220 + 31)
        self.onde_a(img, inter, t, 0.95)
        self.main.dessiner(img, inter, t, 0.95, "droite")
        cx, cy, ech = W / 2, 1230 + 8 * math.sin(t * 2), 0.7
        if t >= 1.7:
            e = ressort(clamp((t - 1.7) / 0.6))
            self.telephone_ecran(img, self._ecran_offert(), cx, cy + (1 - e) * 1100, ech, 0, clamp((t - 1.7) / 0.2))
        bouton = self.point_ecran(EW / 2, 930, cx, cy, ech)
        appui = 3.5
        self.onde_a(img, bouton, t, appui)
        self.main.dessiner(img, bouton, t, appui, "gauche")
        if t >= appui + 0.1:
            u = t - appui - 0.1
            d = ImageDraw.Draw(img)
            for c in self.confettis:
                v = u - c["d"]
                if v <= 0 or v > 2.2:
                    continue
                x = bouton[0] + c["vx"] * v
                y = bouton[1] + c["vy"] * v + 1300 * v * v
                a = math.radians(c["rot"] * v)
                dx, dy = c["w"] / 2 * math.cos(a), c["w"] / 2 * math.sin(a)
                d.line([(x - dx, y - dy), (x + dx, y + dy)], fill=c["col"], width=c["h"])
        etiquette(img, "Aucune page de paiement", W / 2, 565, 46, ORANGE, t, 3.9)
        return img

    def tableau(self, t):
        img = self.fond(bokeh=True)
        self.bandeau_haut(img, "Son espace, en direct", t, 0.15, WHITE, 60, 150)
        p = sortie_cubique(clamp(t / 0.5))
        carte = carte_blanche(960, 1340, 40)
        d = ImageDraw.Draw(carte)
        # barre du navigateur
        d.rounded_rectangle([0, 0, 959, 80], radius=40, fill=(236, 230, 220))
        d.rectangle([0, 40, 959, 80], fill=(236, 230, 220))
        for k, col in enumerate([(240, 96, 80), (245, 190, 60), (90, 190, 100)]):
            d.ellipse([30 + k * 34, 28, 52 + k * 34, 50], fill=col)
        d.rounded_rectangle([150, 20, 810, 60], radius=20, fill=WHITE)
        d.text((480, 40), "app.myfaceci.online/admin", font=police(F_TXT, 24), fill=GRIS, anchor="mm")
        d.text((48, 118), "Mariage Awa & Koffi", font=police(F_BOLD, 42), fill=INK)
        clign = 0.5 + 0.5 * math.sin(t * 6)
        d.ellipse([50, 190, 70, 210], fill=(int(40 + 60 * clign), int(170 + 40 * clign), 90))
        d.text((82, 200), "en direct", font=police(F_BOLD, 26), fill=GREEN, anchor="lm")
        # les photos analysees : un anneau qui se remplit
        d.rounded_rectangle([40, 250, 470, 640], radius=28, fill=CREME)
        d.text((70, 280), "Photos analysées", font=police(F_BOLD, 30), fill=INK)
        a = clamp((t - 0.6) / 1.6)
        d.ellipse([150, 340, 360, 550], outline=GRIS_CLAIR, width=26)
        if a > 0:
            d.arc([150, 340, 360, 550], -90, -90 + 360 * a, fill=ORANGE, width=26)
        d.text((255, 445), f"{int(a * 100)} %", font=police(F_DISPLAY, 46), fill=INK, anchor="mm")
        d.text((255, 600), "visages regroupés", font=police(F_TXT, 24), fill=GRIS, anchor="mm")
        # les ventes : des barres qui montent
        d.rounded_rectangle([490, 250, 920, 640], radius=28, fill=CREME)
        d.text((520, 280), "Ventes", font=police(F_BOLD, 30), fill=INK)
        hauteurs = [0.35, 0.55, 0.45, 0.7, 0.62, 0.85, 1.0]
        for k, hb in enumerate(hauteurs):
            q = ressort(clamp((t - 1.0 - k * 0.12) / 0.4))
            x0 = 525 + k * 54
            haut = 230 * hb * q
            d.rounded_rectangle([x0, 600 - haut, x0 + 36, 600], radius=10, fill=ORANGE if k == 6 else (246, 170, 120))
        # les tirages a imprimer
        d.rounded_rectangle([40, 670, 920, 1300], radius=28, fill=CREME)
        d.text((70, 700), "Tirages à imprimer", font=police(F_BOLD, 30), fill=INK)
        for k in range(4):
            t0 = 2.0 + k * 0.25
            if t < t0:
                continue
            y = 770 + k * 128
            carte.alpha_composite(self.vignettes_tirages[k], (70, y))
            d.text((190, y + 30), f"Photo {412 + k * 37:04d}", font=police(F_BOLD, 28), fill=INK)
            d.text((190, y + 66), "Tirage 10×15", font=police(F_TXT, 24), fill=GRIS)
            fait = t >= 3.7 + k * 0.3
            d.rounded_rectangle([660, y + 26, 890, y + 76], radius=25, fill=GREEN if fait else ORANGE)
            d.text((775, y + 51), "Imprimé" if fait else "À imprimer", font=police(F_BOLD, 24), fill=WHITE, anchor="mm")
        cx, cy = W / 2, 1040 + 50 * (1 - p)
        coller_centre(img, ombre_de(carte), cx + 6, cy + 20, 1.0, 0, p)
        coller_centre(img, carte, cx, cy, 1.0, 0, p)
        bouton = (cx - 480 + 775, cy - 670 + 770 + 51)
        self.onde_a(img, bouton, t, 3.6)
        self.main.dessiner(img, bouton, t, 3.6, "droite")
        return img

    def preuve(self, t):
        img = self.fond(bokeh=True)
        if t >= 0.3:
            p = ressort((t - 0.3) / 0.45)
            coller_centre(img, self.epingle, W / 2 - 230, 250 - 80 * (1 - p), 1.0, 0, clamp((t - 0.3) / 0.15))
        if t >= 0.6:
            texte(img, "Abidjan", W / 2 + 60, 250, 96, WHITE, opacite=clamp((t - 0.6) / 0.25))
        etiquette(img, "Remise de diplômes · IIT", W / 2, 400, 46, ORANGE, t, 2.0)
        chiffres = [(3.3, 119, "photos mises en ligne", 640), (5.0, 12, "commandes payées par les invités", 1000)]
        for t0, val, lib, y in chiffres:
            if t < t0:
                continue
            n = int(round(val * sortie_cubique((t - t0) / 0.9)))
            texte(img, str(n), W / 2, y, 190, ORANGE, opacite=clamp((t - t0) / 0.15))
            texte(img, lib, W / 2, y + 150, 46, WHITE, chemin=F_BOLD, opacite=clamp((t - t0 - 0.2) / 0.25))
        if t >= 6.4:
            p = ressort((t - 6.4) / 0.35)
            texte(img, "1 à 2 s", W / 2, 1400, 150, WHITE, echelle=1.3 - 0.3 * p, opacite=clamp((t - 6.4) / 0.15))
            texte(img, "pour retrouver ses photos", W / 2, 1530, 46, ORANGE, chemin=F_BOLD, opacite=clamp((t - 6.6) / 0.25))
        etiquette(img, "Premier test en conditions réelles", W / 2, 1760, 42, WHITE, t, 6.9)
        return img

    def partout(self, t):
        img = self.fond()
        decal = -int(300 + 700 * t / 8.0)
        coller(img, self.mur, 0, decal)
        img.alpha_composite(Image.new("RGBA", (W, H), (*INK, 175)))
        mots = [("Mariages", 300, 380, 0.4), ("Remises de diplômes", 610, 560, 1.1), ("Galas d'entreprise", 420, 760, 2.0),
                ("Églises", 790, 950, 2.9), ("Concerts", 300, 1110, 3.4), ("Anniversaires", 700, 1270, 3.8),
                ("Baptêmes", 330, 1420, 4.05), ("Séminaires", 760, 1540, 4.3)]
        for k, (m, x, y, t0) in enumerate(mots):
            flotte = 6 * math.sin(t * 2 + k)
            etiquette(img, m, x, y + flotte, 54 if t0 < 3.6 else 44, ORANGE if k % 2 == 0 else WHITE, t, t0)
        bas = Image.new("L", (1, 520))
        for y in range(520):
            bas.putpixel((0, y), int(230 * (y / 520) ** 1.4))
        voile = Image.new("RGBA", (W, 520), (*INK, 255))
        voile.putalpha(bas.resize((W, 520)))
        img.alpha_composite(voile, (0, H - 520))
        if t >= 5.0:
            p = ressort((t - 5.0) / 0.35)
            texte(img, "Partout où il y a", W / 2, 1720, 66, WHITE, echelle=1.2 - 0.2 * p, opacite=clamp((t - 5.0) / 0.15))
            texte(img, "du monde et des photos.", W / 2, 1810, 66, ORANGE, echelle=1.2 - 0.2 * p, opacite=clamp((t - 5.2) / 0.15))
        return img

    def ivoirienne(self, t):
        img = self.fond_sable_pagne.copy()
        img.alpha_composite(Image.new("RGBA", (W, H), (*SAND, 150)))
        if t >= 0.2:
            p = ressort((t - 0.2) / 0.45)
            coller_centre(img, self.logo_clair, W / 2, 560, 0.85 * p, 0, clamp((t - 0.2) / 0.15))
        if t >= 0.9:
            texte(img, "Une solution", W / 2, 820, 64, INK, opacite=clamp((t - 0.9) / 0.2), ombre=False)
        if t >= 1.3:
            p = ressort((t - 1.3) / 0.35)
            texte(img, "ivoirienne", W / 2, 950, 124, ORANGE, echelle=1.3 - 0.3 * p, opacite=clamp((t - 1.3) / 0.12), ombre=False)
        if t >= 1.6:
            q = sortie_cubique((t - 1.6) / 0.5)
            d = ImageDraw.Draw(img)
            larg = 160 * q
            for k, col in enumerate([ORANGE, WHITE, GREEN]):
                x0 = W / 2 - 240 + k * 160 + (160 - larg) / 2
                d.rectangle([x0, 1045, x0 + larg, 1067], fill=col, outline=(200, 190, 175) if col == WHITE else None)
        if t >= 2.6:
            texte(img, "d'intelligence artificielle", W / 2, 1170, 58, INK, opacite=clamp((t - 2.6) / 0.25), ombre=False)
        if t >= 3.8:
            texte(img, "pensée pour nos événements.", W / 2, 1270, 58, INK, chemin=F_BOLD,
                  opacite=clamp((t - 3.8) / 0.25), ombre=False)
        return img

    # ------------------------------------------------------------ montage
    def scene(self, nom):
        titres = {"titre_scanne": "Scanne.", "titre_retrouve": "Retrouve.", "titre_repars": "Repars avec."}
        if nom in titres:
            return self.titre(titres[nom])
        return getattr(self, nom)

    def scenes(self):
        decoupe, _, _ = montage_v4.decoupage()
        return [(d, self.scene(nom)) for nom, _, d in decoupe]


def apercu():
    """Images de controle de chaque nouvelle scene, dans v4/apercus/."""
    film = FilmV4()
    dossier = ICI / "apercus"
    dossier.mkdir(exist_ok=True)
    points = {"depot": [0.6, 2.0, 4.5], "ia": [1.6, 3.0, 6.5], "confiance": [1.5, 3.1, 4.6],
              "telechargement": [1.6, 3.9, 6.2], "tirage_sort": [3.2], "qualite": [3.5], "offertes": [1.2, 3.0, 4.6],
              "tableau": [1.5, 4.5], "preuve": [2.6, 7.5], "partout": [2.5, 6.5], "ivoirienne": [4.5]}
    for nom, ts in points.items():
        for t in ts:
            im = film.scene(nom)(t).convert("RGB")
            im.resize((W // 2, H // 2), Image.LANCZOS).save(dossier / f"{nom}-{t:.1f}.jpg", quality=85)
            print(f"  {nom} {t:.1f} s")


def main():
    film = FilmV4()
    scenes = film.scenes()
    total = sum(d for d, _ in scenes)
    ecrivain = cv2.VideoWriter(str(SORTIE), cv2.CAP_FFMPEG, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    n = 0
    for duree, scene in scenes:
        for k in range(int(round(duree * FPS))):
            ecrivain.write(cv2.cvtColor(np.array(scene(k / FPS).convert("RGB")), cv2.COLOR_RGB2BGR))
            n += 1
            if n % 300 == 0:
                print(f"  {n / FPS:.0f} s / {total:.0f} s", flush=True)
    ecrivain.release()
    print(f"{SORTIE}  {n} images, {n / FPS:.1f} s")


if __name__ == "__main__":
    if "--apercu" in sys.argv:
        apercu()
    else:
        main()
