# -*- coding: utf-8 -*-
"""Motion design MYFACE, version 5 (1 min) : pour les photographes.

Tourne sur l'evenement « MA SOUTENANCE » (photos et captures reelles, hors Git) :
- les milliers de photos publiees gratuitement sur les reseaux, ou personne ne se retrouve ;
- un seul lien, un selfie ; le compte photographe, le depot (meme en RAW) ;
- l'IA qui reconnait les visages et range les photos par personne (vrais groupes : 64, 8...) ;
- l'invite qui retrouve ses photos ; offertes ou payantes ; l'argent verse au photographe ;
- la notification de vente, MYFACE Pro, les packs, zero commission.
Le reseau social est dessine de facon generique (aucun logo, aucune marque).
Les durees viennent de v5/montage_v5.py (calees sur la voix Zephyr).

    python marketing/motion-design/v5/rendre_film_v5.py           -> v5/myface-motion-design-v5-muet.mp4
    python marketing/motion-design/v5/rendre_film_v5.py --apercu  -> v5/apercus/*.jpg (images de controle)
"""

import math
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI.parent / "v2"))
sys.path.insert(0, str(ICI.parent / "v4"))
sys.path.insert(0, str(ICI))
from rendre_film import (F_BOLD, F_DISPLAY, FPS, H, INK, ORANGE, WHITE, W,  # noqa: E402
                         clamp, coller, coller_centre, doux, entree_cubique, etiquette, pastille, police,
                         ressort, sortie_cubique, texte)
from rendre_film_v4 import EH, EW, F_TXT, FilmV4, carte_blanche, ombre_de, rond, vignette  # noqa: E402
import montage_v5  # noqa: E402

SORTIE = ICI / "myface-motion-design-v5-muet.mp4"
PHOTOS = ICI / "photos"
CAPS = ICI / "captures"
GRIS = (120, 128, 130)
FIL = (240, 242, 245)          # fond du fil d'actualite generique
# Capture 1290 x 2796 -> ecran du telephone 640 x 1478 (hauteur pleine, bords rognes)
ECH_CAP = EH / 2796
ROGNE = (1290 * ECH_CAP - EW) / 2
# Les visages sur la photo II4A9860 recadree en 1080 x 1920 : centre x, centre y, taille
VISAGES = [(425, 690, 270), (840, 745, 250)]
GROUPES = ["64 photos", "8 photos"]


def ecran_capture(chemin):
    im = Image.open(chemin).convert("RGBA")
    im = im.resize((round(im.width * ECH_CAP), EH), Image.LANCZOS)
    x0 = round((im.width - EW) / 2)
    return im.crop((x0, 0, x0 + EW, EH))


def point_cap(x, y):
    """Un point de la capture 1290 x 2796 -> le meme point sur l'ecran du telephone."""
    return x * ECH_CAP - ROGNE, y * ECH_CAP


def couvrir(im, w, h):
    return ImageOps.fit(im.convert("RGB"), (w, h), Image.LANCZOS).convert("RGBA")


def carte_arrondie(im, r=36):
    im = im.convert("RGBA")
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=r, fill=255)
    im.putalpha(m)
    return im


class FilmV5(FilmV4):
    def __init__(self):
        super().__init__()
        rng = random.Random(55)
        noms = sorted(PHOTOS.glob("*.jpg"))
        self.ph = {f.stem: Image.open(f).convert("RGB") for f in noms}
        liste = list(self.ph.values())
        # -- le fil d'actualite generique, tres long, que l'on fait defiler
        self.fil = self._fil(liste)
        # -- captures (ecrans du telephone)
        self.cap = {f.stem[:2]: ecran_capture(f) for f in CAPS.glob("0[0-6]-*.png")}
        self.pro_evt = carte_arrondie(Image.open(CAPS / "07-pro-evenement.jpg"), 30)
        self.pro_vis = carte_arrondie(Image.open(CAPS / "08-pro-visages.jpg"), 30)
        self.qr = Image.open(CAPS / "qr-soutenance.png").convert("RGBA")
        # -- depot : les photos de la soutenance qui volent vers MYFACE
        self.cartes_depot = []
        for k in range(22):
            ph = liste[(k * 7) % len(liste)]
            self.cartes_depot.append({
                "img": vignette(ph, 220, 300, 10, 8),
                "x0": rng.uniform(60, 1020), "a0": rng.uniform(-35, 35),
                "cote": rng.uniform(-380, 380), "t0": 0.25 + k * 0.13,
            })
        # -- l'IA : photo de groupe, visages, groupes
        self.net5 = couvrir(self.ph["II4A9860"], W, H)
        self.avatars5 = []
        for cx, cy, s in VISAGES:
            c = s * 0.62
            self.avatars5.append(rond(self.net5.crop((int(cx - c), int(cy - c), int(cx + c), int(cy + c))), 250, 9))
        solo = ["II4A9899", "II4A9874", "II4A9878", "II4A9896", "II4A9876", "II4A9890", "II4A9893", "II4A9886", "II4A9872"]
        amie = ["II4A9857", "II4A9858", "II4A9859", "II4A9860"]
        self.groupes5 = [[vignette(self.ph[n], 132, 132, 16) for n in solo],
                         [vignette(self.ph[n], 132, 132, 16) for n in amie]]
        # -- la photo imprimee de la fin
        self.tirage = self._tirage(self.ph["II4A9899"])
        self.selfie_rond = rond(self.net5.crop((300, 560, 550, 810)), 150, 6)

    # ------------------------------------------------------------ elements
    @staticmethod
    def _tirage(ph):
        im = couvrir(ph, 620, 900)
        out = Image.new("RGBA", (680, 1000), (250, 247, 242, 255))
        out.alpha_composite(im, (30, 30))
        return out

    @staticmethod
    def _fil(liste):
        """Ecran 640 de large d'un reseau social generique : un album de 2 347 photos."""
        cote, gap = 208, 8
        rangs = 48
        haut = 300 + rangs * (cote + gap)
        im = Image.new("RGBA", (EW, haut), (*FIL, 255))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, EW, 120], fill=WHITE)
        d.text((32, 64), "Fil d'actualité", font=police(F_BOLD, 34), fill=INK)
        d.rectangle([0, 128, EW, 292], fill=WHITE)
        d.ellipse([28, 152, 108, 232], fill=ORANGE)
        d.rounded_rectangle([50, 178, 86, 206], radius=6, outline=WHITE, width=4)
        d.ellipse([60, 183, 76, 199], outline=WHITE, width=3)
        d.text((126, 156), "Studio Photo", font=police(F_BOLD, 30), fill=INK)
        d.text((126, 196), "Album : Soutenance · 2 347 photos", font=police(F_TXT, 24), fill=GRIS)
        d.text((32, 248), "J'aime        Commenter        Partager", font=police(F_BOLD, 22), fill=GRIS)
        for k in range(rangs * 3):
            r, c = divmod(k, 3)
            ph = liste[(k * 5 + r) % len(liste)]
            v = ImageOps.fit(ph, (cote, cote), Image.LANCZOS)
            im.paste(v, (gap + c * (cote + gap) - 4, 300 + r * (cote + gap)))
        return im

    def ecran_fil(self, decalage):
        y = int(decalage) % (self.fil.height - EH - 400)
        ecran = Image.new("RGBA", (EW, EH), (*FIL, 255))
        ecran.alpha_composite(self.fil.crop((0, 300 + y, EW, 300 + y + EH)), (0, 0))
        d = ImageDraw.Draw(ecran)
        d.rectangle([0, 0, EW, 120], fill=WHITE)
        d.text((32, 64), "Fil d'actualité", font=police(F_BOLD, 34), fill=INK)
        return ecran

    def telephone_cap(self, img, ecran, cx, cy, echelle, t_scene=0.0, entree=False):
        if entree and t_scene < 0.6:
            p = ressort(t_scene / 0.6)
            self.telephone_ecran(img, ecran, cx, cy + (1 - p) * 500, echelle * (0.7 + 0.3 * p), 15 * (1 - p),
                                 clamp(t_scene / 0.2))
        else:
            self.telephone_ecran(img, ecran, cx, cy + 6 * math.sin(t_scene * 2.1), echelle)

    def toucher(self, img, x, y, cx, cy, echelle, t, t0, cote="droite"):
        pt = self.point_ecran(x, y, cx, cy, echelle)
        self.onde_a(img, pt, t, t0)
        self.main.dessiner(img, pt, t, t0, cote)

    # ------------------------------------------------------------ scenes
    def reseaux(self, t):
        img = self.fond()
        cx, cy, e = W / 2, H / 2 + 150, 0.78
        self.telephone_cap(img, self.ecran_fil(180 * t ** 1.5), cx, cy, e, t, entree=True)
        texte(img, "2 347 photos", W / 2, 150, 104, WHITE, opacite=clamp((t - 0.3) / 0.25))
        if t >= 1.4:
            texte(img, "publiées gratuitement sur les réseaux", W / 2, 260, 44, ORANGE, chemin=F_BOLD,
                  opacite=clamp((t - 1.4) / 0.3))
        for t0 in (2.4, 3.4, 4.4):
            self.toucher(img, 420, 1150, cx, cy, e, t, t0)
        return img

    def cherche(self, t):
        img = self.fond()
        cx, cy, e = W / 2, H / 2 + 150, 0.78
        dep = 180 * (6.0 ** 1.5) + 900 * t + 260 * t ** 2
        self.telephone_cap(img, self.ecran_fil(dep), cx, cy, e, t + 6)
        for t0 in (0.5, 1.3, 2.1, 2.9):
            self.toucher(img, 420, 1150, cx, cy, e, t, t0)
        reste = max(0, 2186 - int(380 * t))
        texte(img, f"Encore {reste:,} photos…".replace(",", " "), W / 2, 160, 62, WHITE)
        if t >= 2.3:
            p = ressort((t - 2.3) / 0.35)
            texte(img, "Et vous, vous êtes où ?", W / 2, 280, 70, ORANGE, echelle=1.3 - 0.3 * p,
                  opacite=clamp((t - 2.3) / 0.15))
        if t > len_scene("cherche") - 0.4:
            img.alpha_composite(Image.new("RGBA", (W, H), (*INK, int(255 * clamp((t - len_scene("cherche") + 0.4) / 0.4)))))
        return img

    def lien(self, t):
        if t < 1.5:
            return self.logo(t)
        u = t - 1.5
        img = self.fond(bokeh=True)
        coller_centre(img, self.logo_fonce, W / 2, 230, 0.32)
        # le lien unique
        f = police(F_BOLD, 40)
        txt = "app.myfaceci.online/e/TZ6K4DFM"
        bb = f.getbbox(txt)
        pil = Image.new("RGBA", (bb[2] - bb[0] + 80, 96), (0, 0, 0, 0))
        dp = ImageDraw.Draw(pil)
        dp.rounded_rectangle([0, 0, pil.width - 1, pil.height - 1], radius=48, fill=WHITE)
        dp.text((40 - bb[0], (96 - (bb[3] - bb[1])) / 2 - bb[1]), txt, font=f, fill=INK)
        p = ressort(u / 0.4)
        coller_centre(img, pil, W / 2, 470, 0.7 + 0.3 * p, 0, clamp(u / 0.15))
        if u >= 0.8:
            p = ressort((u - 0.8) / 0.4)
            carte = carte_blanche(440, 440, 40)
            carte.alpha_composite(self.qr.resize((400, 400), Image.NEAREST), (20, 20))
            coller_centre(img, ombre_de(carte), W / 2 + 10, 880, 0.6 + 0.4 * p, 0, clamp((u - 0.8) / 0.2))
            coller_centre(img, carte, W / 2, 870, 0.6 + 0.4 * p, 0, clamp((u - 0.8) / 0.2))
        if u >= 1.8:
            p = ressort((u - 1.8) / 0.35)
            texte(img, "1 seul lien", W / 2, 1240, 110, ORANGE, echelle=1.3 - 0.3 * p, opacite=clamp((u - 1.8) / 0.15))
        if u >= 3.0:
            p = ressort((u - 3.0) / 0.35)
            coller_centre(img, self.selfie_rond, W / 2 - 300, 1470, p)
            texte(img, "1 selfie", W / 2 + 60, 1430, 86, WHITE, opacite=clamp((u - 3.0) / 0.2))
            texte(img, "chacun retrouve ses photos", W / 2 + 60, 1520, 40, WHITE, chemin=F_BOLD,
                  opacite=clamp((u - 3.2) / 0.25))
        return img

    def compte(self, t):
        bascule = 2.6
        if t < bascule:
            img = self.fond(bokeh=True)
            cx, cy, e = W / 2, H / 2 + 120, 0.8
            self.telephone_cap(img, self.cap["06"], cx, cy, e, t, entree=True)
            pastille(img, "Votre compte en 1 minute", W / 2, 130, True, 38, clamp((t - 0.2) / 0.25))
            return img
        u = t - bascule
        img = self.fond(bokeh=True)
        centre = (W / 2, 840)
        arrivees = [c["t0"] + 0.85 for c in self.cartes_depot]
        recues = sum(1 for a in arrivees if u >= a)
        pouls = max([math.exp(-(u - a) / 0.12) for a in arrivees if u >= a] + [0.0])
        apparition = sortie_cubique(u / 0.4)
        coller_centre(img, self.halo, *centre, 0.8 + 0.25 * pouls, 0, 0.55 * apparition + 0.45 * pouls)
        d = ImageDraw.Draw(img)
        r = 230 * (0.6 + 0.4 * ressort(u / 0.5)) * (1 + 0.04 * pouls)
        d.ellipse([centre[0] - r, centre[1] - r, centre[0] + r, centre[1] + r], fill=(*INK, 255), outline=ORANGE, width=8)
        coller_centre(img, self.logo_fonce, *centre, 0.36 * apparition)
        for c in self.cartes_depot:
            v = (u - c["t0"]) / 0.85
            if not 0 <= v <= 1:
                continue
            e = entree_cubique(v) * 0.35 + sortie_cubique(v) * 0.65
            x0, y0 = c["x0"], 2080
            xc, yc = (x0 + centre[0]) / 2 + c["cote"], 1500
            x = (1 - e) ** 2 * x0 + 2 * (1 - e) * e * xc + e ** 2 * centre[0]
            y = (1 - e) ** 2 * y0 + 2 * (1 - e) * e * yc + e ** 2 * centre[1]
            coller_centre(img, c["img"], x, y, 1.0 - 0.85 * e, c["a0"] * (1 - e), 1 - clamp((v - 0.82) / 0.18))
        n = int(round(64 * recues / len(self.cartes_depot)))
        if u >= 0.5:
            texte(img, f"{n} photos", W / 2, 1200, 96, WHITE, opacite=clamp((u - 0.5) / 0.2))
        self.bandeau_haut(img, "Déposez vos photos", u, 0.1, WHITE, 60, 150)
        etiquette(img, "JPEG, PNG, même RAW", W / 2, 1390, 50, ORANGE, u, 1.2)
        etiquette(img, "Gratuit pour commencer", W / 2, 1530, 50, WHITE, u, 2.4)
        return img

    def ia(self, t):
        bascule = 3.4
        if t < bascule:
            z = 1.0 + 0.05 * t / bascule
            img = Image.new("RGBA", (W, H))
            coller_centre(img, self.net5, W / 2, H / 2, z)
            self.degrade_haut(img, 560, 215)

            def place(x, y):
                return W / 2 + (x - W / 2) * z, H / 2 + (y - H / 2) * z

            if 0.4 <= t <= 2.3:
                y = 260 + 1300 * doux((t - 0.4) / 1.9)
                coller(img, self.ligne_scan, 0, y - self.ligne_scan.height / 2)
            for i, (cx, cy, s) in enumerate(VISAGES):
                tp = 0.95 + 0.25 * i
                if t >= tp:
                    p = ressort((t - tp) / 0.35)
                    x, y = place(cx, cy)
                    coller_centre(img, self.coins, x, y, (s * z / 1036) * (1.6 - 0.6 * p), 0, clamp((t - tp) / 0.12))
                    if t >= tp + 0.3:
                        pastille(img, f"Personne {i + 1}", x, y + s * z * 0.62, True, 26, clamp((t - tp - 0.3) / 0.2))
            pastille(img, "IA de reconnaissance faciale", W / 2, 120, True, 34, clamp((t - 0.15) / 0.25),
                     0.8 + 0.2 * ressort(clamp((t - 0.15) / 0.35)))
            if t >= 0.5:
                texte(img, "Chaque visage est reconnu", W / 2, 240, 56, WHITE, opacite=clamp((t - 0.5) / 0.25))
            if t > bascule - 0.45:
                img.alpha_composite(Image.new("RGBA", (W, H), (*INK, int(255 * clamp((t - bascule + 0.45) / 0.45)))))
            return img
        u = t - bascule
        img = self.fond()
        self.bandeau_haut(img, "Rangées par personne", u, 0.1, WHITE, 56, 170)
        for i, (cx, cy, s) in enumerate(VISAGES):
            cible = (W / 2 - 240 if i == 0 else W / 2 + 240, 430)
            p = sortie_cubique(u / 0.6)
            x, y = cx + (cible[0] - cx) * p, cy + (cible[1] - cy) * p
            coller_centre(img, self.avatars5[i], x, y, 0.8 + 0.2 * p)
            if u >= 0.4:
                pastille(img, f"Personne {i + 1}", cible[0], 600, True, 28, clamp((u - 0.4) / 0.2))
            for k, v in enumerate(self.groupes5[i]):
                t0 = 0.55 + k * 0.08 + i * 0.05
                if u >= t0:
                    r, c = divmod(k, 3)
                    coller_centre(img, v, cible[0] - 146 + c * 146, 760 + r * 146, ressort((u - t0) / 0.3))
            if u >= 1.5:
                texte(img, GROUPES[i], cible[0], 1300, 58, ORANGE, opacite=clamp((u - 1.5) / 0.2))
        if u >= 1.9:
            p = ressort((u - 1.9) / 0.35)
            texte(img, "Chaque invité, ses photos.", W / 2, 1600, 64, WHITE, echelle=1.25 - 0.25 * p,
                  opacite=clamp((u - 1.9) / 0.15))
        return img

    def invite(self, t):
        img = self.fond(bokeh=True)
        cx, cy, e = W / 2, H / 2 + 80, 0.84
        etapes = [(0.0, "01", "Le QR code de l'événement"), (1.35, "02", "La galerie"),
                  (2.7, "03", "« Trouver mon visage »"), (4.05, "04", "Toutes ses photos !")]
        cle, legende = "01", etapes[0][2]
        for t0, c, lg in etapes:
            if t >= t0:
                cle, legende = c, lg
        self.telephone_cap(img, self.cap[cle], cx, cy, e, t, entree=True)
        for t0, (x, y) in ((1.15, (645, 1398)), (2.5, (909, 281)), (3.85, (268, 731))):
            self.toucher(img, *point_cap(x, y), cx, cy, e, t, t0)
        debut = max(t0 for t0, *_ in etapes if t >= t0)
        pastille(img, legende, W / 2, 110, True, 36, clamp((t - debut) / 0.2))
        if t >= 4.3:
            etiquette(img, "64 photos retrouvées", W / 2, 1830, 50, ORANGE, t, 4.3)
        return img

    def choix(self, t):
        if t < 2.6:
            img = self.fond(bokeh=True)
            cx, cy, e = W / 2, H / 2 + 80, 0.84
            ecran = self.cap["05"]
            if t >= 1.0:
                z = 1 + 1.1 * sortie_cubique((t - 1.0) / 0.45)
                fx, fy = EW / 2, EH * 0.43
                ecran = ecran.resize((int(EW * z), int(EH * z)), Image.LANCZOS)
                x0, y0 = int(fx * z - fx), int(fy * z - fy)
                ecran = ecran.crop((x0, y0, x0 + EW, y0 + EH))
            self.telephone_cap(img, ecran, cx, cy, e, t)
            self.toucher(img, EW / 2, EH * 0.43, cx, cy, e, t, 0.75)
            if 0.85 <= t < 1.0:
                self.onde_a(img, self.point_ecran(EW / 2, EH * 0.43, cx, cy, e), t, 0.9)
            pastille(img, "Zoom au doigt, filigrane du studio", W / 2, 110, True, 34, clamp((t - 0.2) / 0.25))
            return img
        u = t - 2.6
        img = self.fond(bokeh=True)
        texte(img, "C'est vous qui choisissez", W / 2, 200, 62, WHITE, opacite=clamp(u / 0.25))
        actif_payantes = u >= 0.9
        pastille(img, "Offertes", W / 2 - 200, 360, not actif_payantes, 46, clamp((u - 0.15) / 0.2))
        pastille(img, "Payantes", W / 2 + 200, 360, actif_payantes, 46, clamp((u - 0.25) / 0.2))
        if u >= 1.4:
            texte(img, "Paiement en ligne", W / 2, 560, 54, WHITE, opacite=clamp((u - 1.4) / 0.25))
            lignes = [("Wave", 250, 690), ("Orange Money", 610, 690), ("MTN", 330, 800), ("Carte", 620, 800)]
            for i, (m, x, y) in enumerate(lignes):
                t0 = 1.6 + i * 0.12
                if u >= t0:
                    pastille(img, m, x, y, False, 38, clamp((u - t0) / 0.2), 0.8 + 0.2 * ressort((u - t0) / 0.3))
        if u >= 2.4:
            d = ImageDraw.Draw(img)
            p = sortie_cubique((u - 2.4) / 0.5)
            y1 = 900 + 260 * p
            d.line([(W / 2, 900), (W / 2, y1)], fill=ORANGE, width=10)
            if p > 0.95:
                d.polygon([(W / 2 - 34, y1 - 6), (W / 2 + 34, y1 - 6), (W / 2, y1 + 40)], fill=ORANGE)
        if u >= 2.8:
            p = ressort((u - 2.8) / 0.35)
            carte = carte_blanche(620, 220, 40)
            dc = ImageDraw.Draw(carte)
            dc.rounded_rectangle([40, 60, 160, 160], radius=24, fill=ORANGE)
            dc.rectangle([60, 92, 140, 104], fill=WHITE)
            dc.text((190, 62), "Votre compte", font=police(F_BOLD, 46), fill=INK)
            dc.text((190, 124), "Mobile Money ou banque", font=police(F_TXT, 32), fill=GRIS)
            coller_centre(img, carte, W / 2, 1330, 0.7 + 0.3 * p, 0, clamp((u - 2.8) / 0.15))
        if u >= 3.4:
            texte(img, "Directement chez vous", W / 2, 1580, 60, ORANGE, opacite=clamp((u - 3.4) / 0.25))
        return img

    def _ecran_notif(self):
        ecran = Image.new("RGBA", (EW, EH), (0, 0, 0, 255))
        fond = couvrir(self.ph["II4A9874"], EW, EH).filter(ImageFilter.GaussianBlur(18))
        ecran.alpha_composite(fond)
        ecran.alpha_composite(Image.new("RGBA", (EW, EH), (0, 0, 0, 90)))
        d = ImageDraw.Draw(ecran)
        f = police(F_TXT, 150)
        bb = f.getbbox("21:47")
        d.text(((EW - (bb[2] - bb[0])) / 2 - bb[0], 170), "21:47", font=f, fill=WHITE)
        return ecran

    def _notif(self):
        n = carte_blanche(580, 230, 34, (250, 250, 250, 240))
        d = ImageDraw.Draw(n)
        n.alpha_composite(self.logo_clair.resize((64, 64), Image.LANCZOS), (26, 26))
        d.text((104, 30), "MYFACE Pro", font=police(F_BOLD, 26), fill=GRIS)
        d.text((470, 30), "à l'instant", font=police(F_TXT, 22), fill=GRIS)
        d.text((26, 104), "Nouvelle vente : 1 000 F", font=police(F_BOLD, 32), fill=INK)
        d.text((26, 150), "Payée en ligne, MA SOUTENANCE.", font=police(F_TXT, 26), fill=INK)
        d.text((26, 184), "Les photos sont déjà envoyées à l'invité.", font=police(F_TXT, 26), fill=INK)
        return n

    def vente(self, t):
        img = self.fond(bokeh=True)
        cx, cy, e = W / 2, H / 2 + 90, 0.84
        ecran = self._ecran_notif() if not hasattr(self, "_ecran_n") else self._ecran_n
        self._ecran_n = ecran
        if t >= 0.35:
            ecran = ecran.copy()
            if not hasattr(self, "_notif_img"):
                self._notif_img = self._notif()
            p = ressort((t - 0.35) / 0.4)
            ecran.alpha_composite(self._notif_img, (30, int(470 - 200 * (1 - p))))
        vibre = 0.35 <= t < 1.3 or 1.6 <= t < 2.2
        dx = 12 * math.sin(t * 95) if vibre else 0
        self.telephone_ecran(img, ecran, cx + dx, cy, e)
        if vibre:
            d = ImageDraw.Draw(img)
            for s in (-1, 1):
                for k in range(3):
                    x = cx + s * (330 + k * 34)
                    d.arc([x - 30, cy - 120 - k * 30, x + 30, cy + 120 + k * 30], 300 if s > 0 else 120,
                          60 if s > 0 else 240, fill=ORANGE, width=8)
        self.bandeau_haut(img, "Chaque vente, en direct", t, 0.1, WHITE, 60, 140)
        return img

    def pro(self, t):
        img = self.fond(bokeh=True)
        pastille(img, "MYFACE Pro", W / 2, 120, True, 44, clamp(t / 0.25))
        p = sortie_cubique(t / 0.6)
        a = self.pro_evt
        e = 760 / a.width
        coller_centre(img, ombre_de(a), 440 + 600 * (1 - p) + 14, 820 + 20, e, 0, p)
        coller_centre(img, a, 440 + 600 * (1 - p), 820, e, 0, p)
        if t >= 1.3:
            q = sortie_cubique((t - 1.3) / 0.6)
            b = self.pro_vis
            e2 = 600 / b.width
            coller_centre(img, ombre_de(b), 700 - 700 * (1 - q) + 14, 1210 + 20, e2, 3, q)
            coller_centre(img, b, 700 - 700 * (1 - q), 1210, e2, 3, q)
        if t >= 2.6:
            for i, m in enumerate(("Téléphone", "Tablette", "Ordinateur")):
                pastille(img, m, 230 + i * 310, 1810, i != 1, 34, clamp((t - 2.6 - i * 0.12) / 0.2))
        return img

    def packs(self, t):
        img = self.fond(bokeh=True)
        self.bandeau_haut(img, "Les packs MYFACE", t, 0.1, WHITE, 64, 150)
        packs = [("Découverte", "10 photos", "Gratuit"), ("Événement", "500 photos", "Petit prix"),
                 ("Pro", "2 000 photos", "Petit prix")]
        actif = 0 if t < 2.0 else (1 if t < 3.0 else 2)
        for i, (nom, nb, prix) in enumerate(packs):
            t0 = 0.3 + i * 0.35
            if t < t0:
                continue
            p = ressort((t - t0) / 0.35)
            c = carte_blanche(860, 200, 36, (255, 255, 255, 255) if i == actif else (255, 255, 255, 215))
            d = ImageDraw.Draw(c)
            if i == actif:
                d.rounded_rectangle([0, 0, 859, 199], radius=36, outline=ORANGE, width=8)
            d.text((44, 38), nom, font=police(F_DISPLAY, 50), fill=INK)
            d.text((44, 118), nb, font=police(F_BOLD, 38), fill=GRIS)
            f = police(F_BOLD, 40)
            bb = f.getbbox(prix)
            d.text((816 - (bb[2] - bb[0]), 80), prix, font=f, fill=ORANGE)
            coller_centre(img, c, W / 2, 420 + i * 240, 0.7 + 0.3 * p, 0, clamp((t - t0) / 0.15))
        if 2.0 <= t < 3.4:
            etiquette(img, "Passez au pack supérieur", W / 2, 1150, 46, WHITE, t, 2.0)
        if t >= 3.6:
            p = ressort((t - 3.6) / 0.4)
            texte(img, "0 %", W / 2, 1400, 230, ORANGE, echelle=1.4 - 0.4 * p, opacite=clamp((t - 3.6) / 0.15))
            texte(img, "de commission sur vos ventes", W / 2, 1600, 54, WHITE, opacite=clamp((t - 3.9) / 0.25))
        return img

    def fin(self, t):
        img = self.fond(sable=True)
        if t < 0.9:
            coller_centre(img, self.tirage, W / 2, 760, 0.95 - 0.4 * sortie_cubique(t / 0.5), -3)
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
            texte(img, "myfaceci.online/photographes", W / 2, 1640, 50, INK, chemin=F_BOLD,
                  opacite=clamp((t - 2.7) / 0.3), ombre=False)
        return img

    # ------------------------------------------------------------ montage
    def scenes(self):
        decoupe, _, _ = montage_v5.decoupage()
        return [(d, getattr(self, nom)) for nom, _, d in decoupe]


def len_scene(nom):
    for n, _, d in montage_v5.decoupage()[0]:
        if n == nom:
            return d
    return 0.0


def apercu():
    film = FilmV5()
    dossier = ICI / "apercus"
    dossier.mkdir(exist_ok=True)
    points = {"reseaux": [0.8, 3.0], "cherche": [1.5, 3.5], "lien": [1.0, 3.0, 6.0], "compte": [1.5, 4.5, 6.0],
              "ia": [2.0, 5.5], "invite": [0.8, 2.0, 3.3, 5.0], "choix": [0.5, 2.0, 4.5, 6.5], "vente": [1.0, 2.5],
              "pro": [1.0, 4.0], "packs": [1.5, 2.5, 6.0], "fin": [3.5]}
    for nom, ts in points.items():
        for t in ts:
            im = getattr(film, nom)(t).convert("RGB")
            im.resize((W // 2, H // 2), Image.LANCZOS).save(dossier / f"{nom}-{t:.1f}.jpg", quality=85)
            print(f"  {nom} {t:.1f} s", flush=True)


def main():
    film = FilmV5()
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
