# -*- coding: utf-8 -*-
"""Le motion design MYFACE, rendu image par image a partir du kit.

« Scanne. Retrouve. Repars avec. » : 38 s en 9:16, 30 images par seconde.
Une main dessinee touche les vrais ecrans un par un (telephone puis borne :
impression et especes), puis le tirage sort de la borne. Suit le prompt
maitre de fiches/sources-html/motion-design-myface.html.

    python motion-design/preparer_motion.py   (le kit, une fois)
    python motion-design/rendre_film.py       -> motion-design/myface-motion-design.mp4 (muet)
    python motion-design/sons.py              -> la bande son (musique, bruitages, voix off)
    powershell -ExecutionPolicy Bypass -File motion-design/assembler.ps1
                                              -> myface-motion-design-son.mp4 (+ version legere)
"""

import math
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from preparer_motion import PLANS  # noqa: E402

W, H, FPS = 1080, 1920, 30
INK, SAND, ORANGE, GREEN, WHITE = (14, 36, 41), (244, 239, 230), (242, 106, 27), (0, 133, 75), (255, 255, 255)
F_DISPLAY = "C:/Windows/Fonts/ariblk.ttf"
F_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
SORTIE = ICI / "myface-motion-design.mp4"

DET, ELE, CAP = ICI / "detoure", ICI / "elements", ICI.parent / "captures" / "iphone"

# ecran du telephone dans l'image (voir preparer_motion.py) et zone de la capture
EX, EY, EW, EH, HB = 220, 221, 640, 1478, 86
CAP_Y, CAP_H = EY + HB, EH - HB

_polices = {}


def police(chemin, taille):
    cle = (chemin, taille)
    if cle not in _polices:
        _polices[cle] = ImageFont.truetype(chemin, taille)
    return _polices[cle]


def charger(chemin):
    return Image.open(chemin).convert("RGBA")


# --------------------------------------------------------------------------
# Courbes
# --------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def sortie_cubique(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def entree_cubique(x):
    x = clamp(x)
    return x ** 3


def ressort(x):
    """Arrivee avec un leger depassement."""
    x = clamp(x)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def doux(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


# --------------------------------------------------------------------------
# Composition
# --------------------------------------------------------------------------
def coller(base, im, x, y, opacite=1.0):
    """alpha_composite qui accepte les positions hors de l'image."""
    x, y = int(round(x)), int(round(y))
    if opacite < 1.0:
        im = im.copy()
        im.putalpha(im.split()[3].point(lambda a: int(a * opacite)))
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(base.width, x + im.width), min(base.height, y + im.height)
    if x1 <= x0 or y1 <= y0:
        return
    base.alpha_composite(im.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


def transformer(im, echelle=1.0, angle=0.0):
    if echelle != 1.0:
        im = im.resize((max(1, int(im.width * echelle)), max(1, int(im.height * echelle))), Image.BICUBIC)
    if angle:
        im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
    return im


def coller_centre(base, im, cx, cy, echelle=1.0, angle=0.0, opacite=1.0):
    t = transformer(im, echelle, angle)
    coller(base, t, cx - t.width / 2, cy - t.height / 2, opacite)


def texte(base, txt, cx, cy, taille, couleur, chemin=F_DISPLAY, echelle=1.0, opacite=1.0, angle=0.0, ombre=True):
    f = police(chemin, max(8, int(taille)))
    bb = f.getbbox(txt)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    marge = int(taille * 0.4)
    calque = Image.new("RGBA", (tw + 2 * marge, th + 2 * marge), (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    if ombre:
        d.text((marge - bb[0] + 3, marge - bb[1] + 5), txt, font=f, fill=(0, 0, 0, 90))
    d.text((marge - bb[0], marge - bb[1]), txt, font=f, fill=(*couleur, 255))
    coller_centre(base, calque, cx, cy, echelle, angle, opacite)


def pastille(base, txt, cx, cy, actif, taille=30, opacite=1.0, echelle=1.0):
    f = police(F_BOLD, taille)
    bb = f.getbbox(txt)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pw, ph = tw + 2 * taille, th + int(taille * 1.1)
    im = Image.new("RGBA", (pw + 8, ph + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fond = (*ORANGE, 255) if actif else (255, 255, 255, 40)
    d.rounded_rectangle([4, 4, pw + 4, ph + 4], radius=ph // 2, fill=fond,
                        outline=None if actif else (255, 255, 255, 120), width=2)
    d.text((4 + (pw - tw) / 2 - bb[0], 4 + (ph - th) / 2 - bb[1]), txt, font=f, fill=WHITE)
    coller_centre(base, im, cx, cy, echelle, 0, opacite)


def etiquette(base, txt, cx, cy, taille, couleur, t, t0):
    """Texte sur une pastille encre : lisible meme sur le blanc de la borne."""
    if t < t0:
        return
    p = sortie_cubique((t - t0) / 0.3)
    f = police(F_DISPLAY, taille)
    bb = f.getbbox(txt)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    m = int(taille * 0.55)
    im = Image.new("RGBA", (tw + 2 * m, th + 2 * m), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=im.height // 2, fill=(*INK, 235))
    d.text((m - bb[0], m - bb[1]), txt, font=f, fill=(*couleur, 255))
    coller_centre(base, im, cx, cy - 30 * (1 - p), 1.0, 0, p)


# --------------------------------------------------------------------------
# La main (dessinee) : index tendu, ongle orange, bague, manche en pagne
# --------------------------------------------------------------------------
def dessiner_main():
    s = 2
    L, Hm = 700 * s, 1100 * s
    im = Image.new("RGBA", (L, Hm), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def R(x0, y0, x1, y1, r, col):
        d.rounded_rectangle([x0 * s, y0 * s, x1 * s, y1 * s], radius=r * s, fill=col)

    peau, peau_c, peau_f = (96, 60, 42), (112, 72, 51), (78, 48, 34)
    # manche en pagne
    R(140, 780, 600, 1150, 40, (24, 32, 72))
    for yy in range(800, 1100, 70):
        for xx in range(170, 600, 70):
            d.ellipse([(xx - 10) * s, (yy - 10) * s, (xx + 10) * s, (yy + 10) * s], fill=(*ORANGE, 255))
            d.polygon([((xx + 35) * s, (yy + 10) * s), ((xx + 55) * s, (yy + 35) * s),
                       ((xx + 35) * s, (yy + 60) * s), ((xx + 15) * s, (yy + 35) * s)],
                      outline=(244, 239, 230, 255), width=3 * s)
    R(140, 770, 600, 815, 18, (*ORANGE, 255))
    # paume et pouce
    R(170, 430, 570, 800, 150, peau)
    d.ellipse([140 * s, 500 * s, 300 * s, 760 * s], fill=peau_c)
    # doigts replies
    R(320, 395, 425, 545, 52, peau_f)
    R(418, 415, 512, 555, 48, peau_f)
    R(500, 450, 572, 565, 36, peau_f)
    R(418, 492, 512, 508, 6, (212, 175, 55, 255))  # bague en or
    # index tendu
    R(215, 60, 322, 600, 54, peau_c)
    d.arc([235 * s, 300 * s, 302 * s, 330 * s], 200, 340, fill=peau_f, width=3 * s)
    d.arc([235 * s, 420 * s, 302 * s, 450 * s], 200, 340, fill=peau_f, width=3 * s)
    # ongle orange verni
    R(236, 80, 301, 185, 32, (*ORANGE, 255))
    d.ellipse([250 * s, 95 * s, 268 * s, 140 * s], fill=(255, 210, 180, 150))
    im = im.resize((L // s, Hm // s), Image.LANCZOS)
    return im, (268, 72)


def tourner_point(pt, taille, angle, nouvelle):
    cx, cy = taille[0] / 2, taille[1] / 2
    dx, dy = pt[0] - cx, pt[1] - cy
    a = math.radians(angle)
    x = dx * math.cos(a) + dy * math.sin(a)
    y = -dx * math.sin(a) + dy * math.cos(a)
    return x + nouvelle[0] / 2, y + nouvelle[1] / 2


class Main:
    def __init__(self, echelle=0.82):
        brute, bout = dessiner_main()
        brute = transformer(brute, echelle)
        bout = (bout[0] * echelle, bout[1] * echelle)
        self.versions = {}
        for cote, angle in (("droite", 26), ("gauche", -26)):
            im = brute.rotate(angle, resample=Image.BICUBIC, expand=True)
            ombre = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ombre.putalpha(im.split()[3].point(lambda a: int(a * 0.33)).filter(ImageFilter.GaussianBlur(16)))
            pt = tourner_point(bout, brute.size, angle, im.size)
            sens = (0.55, 0.84) if cote == "droite" else (-0.55, 0.84)
            self.versions[cote] = (im, ombre, pt, sens)

    def dessiner(self, base, cible, t, t_contact, cote="droite"):
        """Le doigt arrive, touche la cible a t_contact, puis repart."""
        im, ombre, pt, (sx, sy) = self.versions[cote]
        avant, appui, apres = 0.42, 0.12, 0.40
        if t < t_contact - avant or t > t_contact + appui + apres:
            return
        if t < t_contact:
            p = sortie_cubique((t - (t_contact - avant)) / avant)
            dist = (1 - p) * 1000 + 18 * (1 - p)
        elif t < t_contact + appui:
            dist = 0
        else:
            dist = entree_cubique((t - t_contact - appui) / apres) * 1100
        x = cible[0] + sx * dist - pt[0]
        y = cible[1] + sy * dist - pt[1]
        presse = t_contact <= t < t_contact + appui
        coller(base, ombre, x + 22, y + 34)
        if presse:
            im2 = transformer(im, 0.975)
            coller(base, im2, x + pt[0] * 0.025, y + pt[1] * 0.025)
        else:
            coller(base, im, x, y)


# --------------------------------------------------------------------------
# Le film
# --------------------------------------------------------------------------
class Film:
    def __init__(self):
        self.fond_encre = Image.open(ELE / "fond-encre.png").convert("RGBA")
        self.fond_sable = Image.open(ELE / "fond-sable.png").convert("RGBA")
        self.mur = Image.open(ELE / "mur-de-photos.jpg").convert("RGBA")
        self.coins = charger(ELE / "cadre-coins.png")
        self.onde = charger(ELE / "onde-toucher.png")
        self.coche = charger(ELE / "coche.png")
        self.logo_fonce = charger(ELE / "logo-myface-sur-fonce.png")
        self.logo_clair = charger(ELE / "logo-myface-sur-clair.png")
        self.tel = {}
        for f in DET.glob("telephone-*.png"):
            self.tel[f.stem.replace("telephone-", "")] = charger(f)
        self.borne = {n: charger(DET / f"{n}.png") for n in
                      ("borne-face-accueil", "borne-gros-plan-accueil", "borne-gros-plan-impression",
                       "borne-gros-plan-especes", "borne-34-tirage")}
        tir = charger(DET / "tirage-10x15.png")
        self.tirage = tir.crop(tir.getbbox())
        self.main = Main()
        plans = {p[0]: p for p in PLANS}
        self.points = {}
        for pid, (_, nom, cible, _) in plans.items():
            if isinstance(cible, tuple):
                self.points[pid] = (EX + cible[0] * EW, CAP_Y + cible[1] * CAP_H)
        self.points.update({"P14": (650, 1120), "P15": (324, 1121), "P16": (391, 1131), "P17": (376, 1296)})
        self.bokeh = self._bokeh()
        self.anneau = self._anneau()
        self.cap02 = Image.open(CAP / "02-galerie.png").convert("RGBA")
        self.cap04 = Image.open(CAP / "04-visages-regroupes.png").convert("RGBA")

    def _bokeh(self):
        rng = random.Random(3)
        calque = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(calque)
        for _ in range(34):
            x, y, r = rng.randint(0, W), rng.randint(0, H), rng.randint(30, 130)
            col = rng.choice([(242, 106, 27), (255, 190, 90), (255, 220, 150), (40, 120, 120)])
            d.ellipse([x - r, y - r, x + r, y + r], fill=(*col, rng.randint(35, 85)))
        return calque.filter(ImageFilter.GaussianBlur(22))

    def _anneau(self):
        """Centre du disque lumineux de la borne de face (pour le halo)."""
        a = np.asarray(self.borne["borne-face-accueil"])
        blanc = (a[..., :3].min(axis=2) > 248) & (a[..., 3] > 200)
        blanc[H // 3:, :] = False
        ys, xs = np.where(blanc)
        return (float(xs.mean()), float(ys.mean())) if xs.size else (540.0, 300.0)

    # ---- briques -----------------------------------------------------------
    def fond(self, sable=False, bokeh=False):
        img = (self.fond_sable if sable else self.fond_encre).copy()
        if bokeh:
            img.alpha_composite(self.bokeh)
        return img

    def onde_a(self, base, pt, t, t0):
        p = (t - t0) / 0.45
        if 0 <= p <= 1:
            coller_centre(base, self.onde, pt[0], pt[1], 0.25 + 0.75 * sortie_cubique(p), 0, 1 - p)

    def telephone(self, base, ecran, t_scene, entree=False, decalage=(0, 0)):
        im = self.tel[ecran]
        flotte = 7 * math.sin(t_scene * 2.1)
        if entree and t_scene < 0.7:
            p = ressort(t_scene / 0.7)
            echelle = 0.55 + 0.45 * p
            angle = 22 * (1 - p)
            coller_centre(base, im, W / 2 + decalage[0], H / 2 + flotte + decalage[1] + (1 - p) * 500, echelle, angle,
                          clamp(t_scene / 0.25))
        else:
            coller(base, im, decalage[0], flotte + decalage[1])
        return flotte

    def titre_acte(self, base, mot, t, duree):
        p = t / duree
        echelle = 1.25 - 0.25 * sortie_cubique(p * 3)
        texte(base, mot, W / 2, H / 2, 150, ORANGE, echelle=echelle)

    def bandeau_haut(self, base, txt, t, t0, couleur=WHITE, taille=64, y=120):
        if t >= t0:
            p = sortie_cubique((t - t0) / 0.3)
            texte(base, txt, W / 2, y - 30 * (1 - p), taille, couleur, opacite=p)

    def pastilles(self, base, actif, t):
        noms = ["1 La galerie", "2 Ton visage", "3 Ton selfie"]
        for i, n in enumerate(noms):
            p = sortie_cubique((t - i * 0.06) / 0.3)
            pastille(base, n, 200 + i * 340, 1800 + 40 * (1 - p), i == actif, 30, p)

    # ---- les scenes --------------------------------------------------------
    def accroche(self, t):
        img = self.fond()
        v = 1 - sortie_cubique(t / 1.35)
        decal = -int((1 - v) * 2600)
        coller(img, self.mur, 0, decal)
        voile = Image.new("RGBA", (W, H), (*INK, 110))
        img.alpha_composite(voile)
        if t > 0.75:
            p = sortie_cubique((t - 0.75) / 0.5)
            coller_centre(img, self.coins, W / 2, H / 2, 1.6 - 1.15 * p, 0, p)
        if t > 1.35:
            tir = self.tirage
            visage = tir.crop((int(tir.width * 0.52), int(tir.height * 0.12), int(tir.width * 0.86), int(tir.height * 0.36)))
            p = ressort((t - 1.35) / 0.35)
            coller_centre(img, visage, W / 2, H / 2, 1.1 * p, 0, clamp((t - 1.35) / 0.15))
            coller_centre(img, self.coins, W / 2, H / 2, 0.45, 0)
        if t < 1.35:
            texte(img, "2 347 photos.", W / 2, 300, 96, WHITE, opacite=clamp(t / 0.2))
        else:
            texte(img, "Et toi, t'es où ?", W / 2, 300, 88, ORANGE, opacite=clamp((t - 1.35) / 0.15))
        return img

    def logo(self, t):
        img = self.fond()
        if t < 0.5:
            coller_centre(img, self.coins, W / 2, H / 2, 0.45 + 3 * entree_cubique(t / 0.5), 0, 1 - t / 0.5)
        if t > 0.35:
            p = ressort((t - 0.35) / 0.45)
            coller_centre(img, self.logo_fonce, W / 2, H / 2, 0.9 * p, 0, clamp((t - 0.35) / 0.15))
        return img

    def titre(self, mot):
        def scene(t):
            img = self.fond()
            self.titre_acte(img, mot, t, 0.5)
            return img
        return scene

    def accueil(self, t):
        img = self.fond()
        ecran = "01-accueil" if t < 1.35 else "02-galerie"
        self.telephone(img, ecran, t, entree=True)
        self.onde_a(img, self.points["P01"], t, 1.25)
        self.main.dessiner(img, self.points["P01"], t, 1.25)
        return img

    def galerie(self, t):
        img = self.fond()
        pop = (0.95, 1.9)
        ecran = "02-galerie" if t < pop[1] else "03-visionneuse"
        self.telephone(img, ecran, t + 3)
        self.onde_a(img, self.points["P02"], t, 0.6)
        self.main.dessiner(img, self.points["P02"], t, 0.6)
        if pop[0] <= t <= pop[1]:
            c = self.cap02.crop((int(0.01 * 1206), int(0.14 * 2622), int(0.49 * 1206), int(0.36 * 2622)))
            cadre = Image.new("RGBA", (c.width + 40, c.height + 40), (250, 247, 242, 255))
            cadre.paste(c, (20, 20))
            dep = self.points["P02"]
            u = (t - pop[0]) / (pop[1] - pop[0])
            p = sortie_cubique(u / 0.35) if u < 0.5 else 1 - entree_cubique((u - 0.65) / 0.35)
            cx = dep[0] + (W / 2 - dep[0]) * p
            cy = dep[1] + (H / 2 - dep[1]) * p
            coller_centre(img, cadre, cx, cy, 0.5 + 1.0 * p, -8 * p + 16 * p * (1 - p))
        self.onde_a(img, self.points["P03"], t, 2.35)
        self.main.dessiner(img, self.points["P03"], t, 2.35)
        self.pastilles(img, 0, t)
        return img

    def visages(self, t):
        img = self.fond()
        if t < 0.55:
            ecran = "02-galerie"
        elif t < 2.25:
            ecran = "04-visages-regroupes"
        elif t < 3.15:
            ecran = "05-photos-d-un-visage"
        else:
            ecran = "06-photos-d-un-visage-selectionnees"
        self.telephone(img, ecran, t + 6)
        self.onde_a(img, self.points["P04"], t, 0.45)
        self.main.dessiner(img, self.points["P04"], t, 0.45, "droite")
        # les visages jaillissent autour du telephone, puis reviennent
        if 0.6 <= t <= 1.6:
            u = (t - 0.6) / 1.0
            p = sortie_cubique(u / 0.4) if u < 0.55 else 1 - entree_cubique((u - 0.55) / 0.45)
            for r in range(3):
                for c in range(3):
                    x0, y0 = 0.08 + c * 0.29, 0.21 + r * 0.135
                    tuile = self.cap04.crop((int(x0 * 1206), int(y0 * 2622), int((x0 + 0.26) * 1206), int((y0 + 0.12) * 2622)))
                    sx, sy = EX + (x0 + 0.13) * EW, CAP_Y + (y0 + 0.06) * CAP_H
                    ang = math.radians(-90 + (r * 3 + c) * 40 + u * 60)
                    dx, dy = W / 2 + math.cos(ang) * 470, H / 2 + math.sin(ang) * 700
                    coller_centre(img, tuile, sx + (dx - sx) * p, sy + (dy - sy) * p, 0.42 + 0.25 * p, (c - 1) * 8 * p)
        if 1.55 <= t < 2.25:
            p = sortie_cubique((t - 1.55) / 0.3)
            coller_centre(img, self.coins, self.points["P05"][0], self.points["P05"][1], 0.5 - 0.32 * p, 0, p)
        self.onde_a(img, self.points["P05"], t, 2.1)
        self.main.dessiner(img, self.points["P05"], t, 2.1, "droite")
        self.onde_a(img, self.points["P06"], t, 3.0)
        self.main.dessiner(img, self.points["P06"], t, 3.0, "droite")
        if t >= 3.15:
            k = 0
            for r, n in ((0, 3), (1, 3), (2, 3), (3, 1)):
                for c in range(n):
                    t0 = 3.2 + k * 0.09
                    if t >= t0:
                        p = ressort((t - t0) / 0.25)
                        x = EX + (0.33 + c * 0.296) * EW
                        y = CAP_Y + (0.36 + r * 0.132) * CAP_H
                        coller_centre(img, self.coche, x, y, 0.32 * p)
                    k += 1
        self.pastilles(img, 1, t)
        return img

    def selfie(self, t):
        img = self.fond()
        etapes = [(0.0, "02-galerie"), (0.55, "07-scan-consentement"), (1.45, "08-scan-camera"),
                  (2.35, "09-scan-recherche"), (3.15, "10-scan-resultats")]
        ecran = [e for d, e in etapes if t >= d][-1]
        self.telephone(img, ecran, t + 10)
        for pid, tc in (("P08", 0.45), ("P09", 1.35), ("P10", 2.25), ("P12", 4.35)):
            self.onde_a(img, self.points[pid], t, tc)
            self.main.dessiner(img, self.points[pid], t, tc, "gauche" if pid == "P08" else "droite")
        if 2.25 <= t < 2.55:
            flash = Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (1 - (t - 2.25) / 0.3))))
            img.alpha_composite(flash)
        if 2.35 <= t < 3.15:
            y = CAP_Y + doux((t - 2.35) / 0.8) * CAP_H
            ligne = Image.new("RGBA", (EW, 60), (0, 0, 0, 0))
            dl = ImageDraw.Draw(ligne)
            for k in range(30):
                dl.line([(0, 30 - k), (EW, 30 - k)], fill=(*ORANGE, int(180 * (1 - k / 30) ** 2)))
                dl.line([(0, 30 + k), (EW, 30 + k)], fill=(*ORANGE, int(180 * (1 - k / 30) ** 2)))
            coller(img, ligne, EX, y - 30)
        if t >= 3.15:
            n = int(round(10 * sortie_cubique((t - 3.15) / 0.6)))
            self.bandeau_haut(img, f"{n} photos.", t, 3.15, ORANGE, 84, 105)
            if t >= 3.8:
                texte(img, "Retrouvées.", W / 2, 1810, 70, WHITE, opacite=clamp((t - 3.8) / 0.2))
        if t < 3.8:
            self.pastilles(img, 2, t)
        return img

    def panier(self, t):
        img = self.fond()
        self.telephone(img, "12-panier-paiement", t + 15)
        # le prix : 4 000 F barre, tampon -10 %, total qui roule jusqu'a 3 600 F
        if t >= 0.2:
            cx_av = W / 2 - 310
            texte(img, "4 000 F", cx_av, 110, 62, WHITE, opacite=clamp((t - 0.2) / 0.2))
            if t >= 0.6:
                p = sortie_cubique((t - 0.6) / 0.25)
                larg = police(F_DISPLAY, 62).getlength("4 000 F")
                d = ImageDraw.Draw(img)
                d.line([(cx_av - larg / 2 - 8, 118), (cx_av - larg / 2 - 8 + (larg + 16) * p, 104)], fill=ORANGE, width=9)
        if t >= 0.9:
            p = ressort((t - 0.9) / 0.3)
            tampon = Image.new("RGBA", (240, 110), (0, 0, 0, 0))
            ImageDraw.Draw(tampon).rounded_rectangle([0, 0, 239, 109], radius=22, fill=(*ORANGE, 255))
            f = police(F_DISPLAY, 58)
            ImageDraw.Draw(tampon).text((120, 55), "-10 %", font=f, fill=WHITE, anchor="mm")
            coller_centre(img, tampon, W / 2, 112, 1.8 - 0.8 * p, -8)
        if t >= 1.2:
            v = 4000 - 400 * sortie_cubique((t - 1.2) / 0.45)
            txt = f"{int(round(v / 100.0) * 100):,} F".replace(",", " ")
            texte(img, txt, W / 2 + 310, 110, 62, ORANGE)
        if 1.6 <= t < 2.9:
            texte(img, "Plus tu en prends, moins tu paies.", W / 2, 1810, 46, WHITE, chemin=F_BOLD,
                  opacite=clamp((t - 1.6) / 0.25) * clamp((2.9 - t) / 0.2))
        self.onde_a(img, self.points["P13"], t, 2.6)
        self.main.dessiner(img, self.points["P13"], t, 2.6, "gauche")
        if t >= 2.9:
            moyens = ["Wave", "Orange", "MTN", "Moov", "Espèces"]
            for i, m in enumerate(moyens):
                p = ressort((t - 2.9 - i * 0.07) / 0.3)
                if p > 0:
                    pastille(img, m, 140 + i * 200, 1810, m == "Wave", 28, clamp(p), p)
        return img

    def borne_monte(self, t):
        img = self.fond(bokeh=True)
        p = ressort(t / 0.9)
        y = (1 - p) * 1300 + 250
        if t > 0.9:
            q = sortie_cubique((t - 0.9) / 0.5)
            halo = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
            ImageDraw.Draw(halo).ellipse([150, 150, 550, 550], fill=(255, 236, 200, int(200 * q)))
            halo = halo.filter(ImageFilter.GaussianBlur(70))
            coller_centre(img, halo, self.anneau[0], self.anneau[1] + y)
        coller(img, self.borne["borne-face-accueil"], 0, y)
        etiquette(img, "Pas de téléphone ?", W / 2, 120, 58, WHITE, t, 0.5)
        etiquette(img, "La borne.", W / 2, 250, 70, ORANGE, t, 1.0)
        return img

    def borne_gros_plan(self, t):
        img = self.fond(bokeh=True)
        if t < 1.05:
            nom = "borne-gros-plan-accueil"
        elif t < 2.45:
            nom = "borne-gros-plan-impression"
        else:
            nom = "borne-gros-plan-especes"
        echelle = 1.0 + 0.012 * t
        coller_centre(img, self.borne[nom], W / 2, H / 2, echelle)
        for pid, tc in (("P14", 0.7), ("P15", 1.9), ("P16", 3.2)):
            self.onde_a(img, self.points[pid], t, tc)
            self.main.dessiner(img, self.points[pid], t, tc, "droite")
        if 1.05 <= t < 2.45:
            etiquette(img, "Tirage papier : + 500 F", W / 2, 1800, 54, WHITE, t, 1.1)
        if t >= 2.45:
            etiquette(img, "Espèces acceptées", W / 2, 1800, 60, ORANGE, t, 2.5)
        return img

    def tirage_sort(self, t):
        img = self.fond(bokeh=True)
        fente = self.points["P17"]
        if t < 1.3:
            coller(img, self.borne["borne-34-tirage"], 0, 0)
            pas = min(3, int(t / 0.3))
            sortie = (pas + doux((t - pas * 0.3) / 0.15) if pas < 3 else 3) / 3
            coller_centre(img, self.tirage, fente[0] - 40 * sortie, fente[1] + 70 * sortie, 0.12, 12)
            etiquette(img, "Tirage 10×15 en 20 secondes.", W / 2, 1810, 50, WHITE, t, 0.2)
        else:
            u = sortie_cubique((t - 1.3) / 0.7)
            fond = self.borne["borne-34-tirage"]
            coller_centre(img, fond, W / 2, H / 2, 1 + 0.6 * u, 0, 1 - u)
            x = fente[0] - 40 + (W / 2 - fente[0] + 40) * u
            y = fente[1] + 70 + (H / 2 - fente[1] - 70) * u
            coller_centre(img, self.tirage, x, y, 0.12 + 0.95 * u, 12 - 15 * u)
        return img

    def fin(self, t):
        img = self.fond(sable=True)
        if t < 0.9:
            coller_centre(img, self.tirage, W / 2, 760, 1.07 - 0.45 * sortie_cubique(t / 0.5), -3)
            if t > 0.3:
                p = sortie_cubique((t - 0.3) / 0.3)
                coller_centre(img, self.coins, W / 2, 760, 1.2 - 0.25 * p, 0, p)
        else:
            p = ressort((t - 0.9) / 0.45)
            coller_centre(img, self.logo_clair, W / 2, 640, 0.85 * p, 0, clamp((t - 0.9) / 0.15))
        mots = [("Scanne.", INK), ("Retrouve.", INK), ("Repars avec.", ORANGE)]
        for i, (m, col) in enumerate(mots):
            t0 = 1.2 + i * 0.5
            if t >= t0:
                p = ressort((t - t0) / 0.3)
                texte(img, m, W / 2, 950 + i * 150, 110, col, echelle=1.4 - 0.4 * p, opacite=clamp((t - t0) / 0.12),
                      ombre=False)
        if t >= 2.7:
            texte(img, "myfaceci.online  ·  07 58 50 94 03", W / 2, 1640, 44, INK, chemin=F_BOLD,
                  opacite=clamp((t - 2.7) / 0.3), ombre=False)
        return img

    def scenes(self):
        # durees en demi-secondes : a 120 BPM, chaque coupe tombe sur un temps
        # (les sons de sons.py reprennent ce decoupage)
        return [
            (2.0, self.accroche), (1.5, self.logo), (0.5, self.titre("Scanne.")), (3.0, self.accueil),
            (0.5, self.titre("Retrouve.")), (3.0, self.galerie), (4.5, self.visages), (5.0, self.selfie),
            (0.5, self.titre("Repars avec.")), (4.0, self.panier), (2.0, self.borne_monte),
            (4.0, self.borne_gros_plan), (2.0, self.tirage_sort), (3.5, self.fin),
        ]


def main():
    film = Film()
    scenes = film.scenes()
    total = sum(d for d, _ in scenes)
    ecrivain = cv2.VideoWriter(str(SORTIE), cv2.CAP_FFMPEG, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    n = 0
    for duree, scene in scenes:
        for k in range(int(round(duree * FPS))):
            img = scene(k / FPS)
            ecrivain.write(cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR))
            n += 1
            if n % 150 == 0:
                print(f"  {n / FPS:.0f} s / {total:.0f} s")
    ecrivain.release()
    print(f"{SORTIE}  {n} images, {n / FPS:.1f} s, {SORTIE.stat().st_size // 1024 // 1024} Mo")


if __name__ == "__main__":
    main()
