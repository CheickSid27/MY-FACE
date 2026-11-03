# -*- coding: utf-8 -*-
"""S3 « Un selfie » (15 s, statut WhatsApp et TikTok). Voir v6/STORYBOARD.md.

Message : un selfie, deux secondes, et l'IA sort toutes tes photos ; ton mysterieux puis
eclatant. Les photos et les visages sont les vrais resultats de l'IA de MYFACE sur
l'evenement de demonstration (le marie = personne 0, sur 10 photos).

    python marketing/motion-design/v6/film_s3.py [--images | --brouillon | --decoupage]
"""

import math
import random

from PIL import Image, ImageDraw

from moteur_v6 import (F_BOLD, F_DISPLAY, H, INK, ORANGE, WHITE, W, FilmV6, cam_cles, camera, clamp, coller,
                       coller_centre, coups, degrade_vertical, expo, io, lourd, masque_rond, mots_montants, o5,
                       pilule, police, principal, rond, texte, transformer, vif, voile)

MARIE = 0
COUPLE = "pexels-joshua-j-lewis-1577020288-27333351.jpg"


class FilmS3(FilmV6):
    NOM = "S3"
    VOIX = "S3-un-selfie"
    LIGNES = [
        ("selfie", 0.08, 0.76, 2.0, 0.25),
        ("scan", 2.02, 3.02, 2.0, 0.2),
        ("eventail", 3.96, 5.96, 3.0, 0.2),
        ("ia", 6.98, 10.62, 4.5, 0.25),
        ("fin", 11.52, 14.98, 4.5, 0.3),
    ]
    TRANSITIONS = {
        "eventail": ("iris", 0.35, {"cx": W / 2, "cy": 860}),
        "ia": ("fouet", 0.4, {"sens": 1}),
        "fin": ("masque_texte", 0.7, {"mot": "MYFACE"}),
    }
    DROP = "eventail"

    def __init__(self):
        super().__init__()
        rng = random.Random(33)
        self.siennes = self.photos_de(MARIE)                       # 10 photos
        toutes = sorted(self.visages)
        # le selfie : le visage du marie, en grand
        vis, _ = self.cadrer(COUPLE, 760, 760, MARIE, 430, (0.5, 0.5))
        self.img_selfie = rond(vis, 760)
        self.selfie_petit = rond(vis, 330, 10)
        # le mur de vignettes que l'IA balaie
        self.mur_cases = []
        cote, gap = 150, 12
        for r in range(12):
            for c in range(7):
                nom = toutes[(r * 7 + c * 3) % len(toutes)]
                x = c * (cote + gap) - 40 + (r % 2) * 40
                y = r * (cote + gap) + 10
                self.mur_cases.append({"nom": nom, "x": x, "y": y, "lui": nom in self.siennes,
                                       "img": self.cadrer(nom, cote, cote)[0], "d": rng.uniform(0, 0.1)})
        self.cote_mur = cote
        # l'eventail : les 10 photos, cadrees sur lui
        self.cartes = []
        for k, nom in enumerate(self.siennes):
            im, _ = self.cadrer(nom, 330, 440, MARIE, 120, (0.5, 0.36))
            self.cartes.append(self._carte(im))
        # l'IA : photos plein cadre, son visage toujours au meme endroit
        self.pleins, self.boites = [], []
        for nom in self.siennes:
            im, boite = self.cadrer(nom, W, H, MARIE, 300, (0.5, 0.40))
            self.pleins.append(im)
            self.boites.append(((boite[0] + boite[2]) / 2, (boite[1] + boite[3]) / 2, boite[2] - boite[0]))
        self.grille = [self._carte(self.cadrer(n, 300, 300, MARIE, 110, (0.5, 0.45))[0], 8) for n in self.siennes]

    @staticmethod
    def _carte(im, bord=12):
        out = Image.new("RGBA", (im.width + 2 * bord, im.height + 2 * bord), (0, 0, 0, 0))
        ImageDraw.Draw(out).rounded_rectangle([0, 0, out.width - 1, out.height - 1], radius=22, fill=(250, 247, 242, 255))
        m = Image.new("L", im.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=14, fill=255)
        out.paste(im, (bord, bord), m)
        return out

    # ------------------------------------------------------------ 1. le selfie
    def selfie(self, t):
        img = degrade_vertical((10, 26, 30), INK)
        c = (W / 2, 820)
        # le viseur : le visage vit un peu (respiration de la camera)
        dz = 1.0 + 0.015 * math.sin(t * 2.4)
        coller_centre(img, self.img_selfie, c[0] + 6 * math.sin(t * 1.3), c[1] + 4 * math.cos(t * 1.1), dz * (0.92 + 0.08 * o5(t / 0.6)))
        d = ImageDraw.Draw(img)
        r = 400
        for k in range(36):
            a0 = k * 10 + t * 30
            d.arc([c[0] - r, c[1] - r, c[0] + r, c[1] + r], a0, a0 + 5, fill=ORANGE, width=6)
        # le declencheur, le doigt
        bouton = (W / 2, 1480)
        presse = 1.35
        rb = 78 * (0.9 if presse <= t < presse + 0.12 else 1.0)
        d.ellipse([bouton[0] - 96, bouton[1] - 96, bouton[0] + 96, bouton[1] + 96], outline=WHITE, width=8)
        d.ellipse([bouton[0] - rb, bouton[1] - rb, bouton[0] + rb, bouton[1] + rb], fill=WHITE)
        self.main.dessiner(img, bouton, t, presse, "droite")
        mots_montants(img, "Un selfie…", W / 2, 1720, 92, WHITE, t, 0.25)
        # le flash : le blanc part du bouton et couvre tout
        if t >= presse + 0.05:
            q = expo((t - presse - 0.05) / 0.3)
            blanc = Image.new("RGBA", (W, H), (255, 255, 255, 255))
            from moteur_v6 import rayon_couvrant
            img.paste(blanc, (0, 0), masque_rond(*bouton, rayon_couvrant(*bouton) * q))
        return img

    # ------------------------------------------------------------ 2. deux secondes
    def scan(self, t):
        img = Image.new("RGBA", (W, H), (*INK, 255))
        y_ligne = -100 + (H + 200) * io(t / 1.7)
        dec = -40 * t
        for case in self.mur_cases:
            y = case["y"] + dec
            vue = y + self.cote_mur / 2 < y_ligne
            im = case["img"]
            if vue and case["lui"]:
                coller(img, im, case["x"], y)
                d = ImageDraw.Draw(img)
                d.rounded_rectangle([case["x"] - 4, y - 4, case["x"] + self.cote_mur + 4, y + self.cote_mur + 4],
                                    radius=10, outline=ORANGE, width=7)
            else:
                coller(img, im, case["x"], y, 0.16 if vue else 0.38)
        # la ligne de balayage
        coller(img, self.ligne_scan, 0, y_ligne - self.ligne_scan.height / 2)
        # le blanc du flash s'eteint
        if t < 0.25:
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - t / 0.25)))))
        # le selfie au centre et le chrono
        coller_centre(img, self.selfie_petit, W / 2, 860, 0.85 + 0.15 * vif(t))
        chrono = min(2.0, t * 2.0 / 1.8)
        bas = degrade_vertical((14, 36, 41), (14, 36, 41), 420)
        bas.putalpha(degrade_vertical((0, 0, 0), (235, 235, 235), 420).split()[0])
        img.alpha_composite(bas, (0, H - 420))
        haut = degrade_vertical((14, 36, 41), (14, 36, 41), 480)
        haut.putalpha(degrade_vertical((225, 225, 225), (0, 0, 0), 480).split()[0])
        img.alpha_composite(haut, (0, 0))
        texte(img, f"{chrono:.1f} s".replace(".", ","), W / 2, 300, 150, WHITE)
        mots_montants(img, "Deux secondes…", W / 2, 1720, 88, WHITE, t, 0.2)
        return img

    # ------------------------------------------------------------ 3. toutes tes photos (la musique tombe)
    def eventail(self, t):
        img = degrade_vertical((30, 52, 56), INK)
        img.alpha_composite(self.bokeh)
        c = (W / 2, 860)
        n = len(self.cartes)
        for k, carte in enumerate(self.cartes):
            p = lourd(t - 0.05 - k * 0.045)
            ang = (k - (n - 1) / 2) * 8.0
            rad = math.radians(ang)
            rr = 520
            x = c[0] + math.sin(rad) * rr * p
            y = c[1] + 560 - math.cos(rad) * rr * p - 180 * p
            coller_centre(img, carte, x, y, 0.4 + 0.6 * min(p, 1.05), -ang * p)
        coller_centre(img, self.selfie_petit, c[0], 1320, 0.62 * vif(t - 0.2))
        pilule(img, "10 photos retrouvées", W / 2, 1530, 46, ORANGE, WHITE, t, 0.9)
        mots_montants(img, "Toutes tes photos.", W / 2, 1720, 88, WHITE, t, 0.2, accent=["photos"])
        z = 1.18 - 0.18 * o5(t / 1.6) + coups(t, [0, 0.5, 1.0, 1.5, 2.0, 2.5], 0.014)
        return camera(img, z, W / 2, H / 2 + 40)

    # ------------------------------------------------------------ 4. l'IA (le cadre qui ne bouge pas)
    def ia(self, t):
        rev = 3.0                                   # la camera recule : les 10 photos en grille
        if t < rev:
            k = min(len(self.pleins) - 1, int(t / 0.5))
            img = self.pleins[k].copy()
            voile(img, INK, 0.25)
            img.alpha_composite(degrade_vertical((14, 36, 41, 255), (14, 36, 41, 0), 520).convert("RGBA").resize((W, 520)), (0, 0))
            # le cadre glisse (ressort) jusqu'au visage de chaque nouvelle photo : les vraies boites de l'IA
            x1, y1, c1 = self.boites[k]
            x0, y0, c0 = self.boites[max(0, k - 1)]
            q = vif(t - k * 0.5)
            fx, fy, fc = mix_(x0, x1, q), mix_(y0, y1, q), mix_(c0, c1, q)
            coller_centre(img, self.coins, fx, fy, fc * 1.35 / self.coins.width)
            pilule(img, "Personne 1", fx, fy + fc * 0.68 + 30, 34, ORANGE, WHITE, t, 0.15)
        else:
            u = t - rev
            img = degrade_vertical((24, 46, 50), INK)
            for i, g in enumerate(self.grille):
                r_, c_ = divmod(i, 3)
                if i == 9:
                    r_, c_ = 3, 1
                x = W / 2 + (c_ - 1) * 300
                y = 380 + r_ * 285
                p = vif(u - i * 0.03)
                coller_centre(img, g, mix_(W / 2, x, p), mix_(H * 0.40, y, p), (0.3 + 0.7 * p) * 0.84)
            pilule(img, "Personne 1 · 10 photos", W / 2, 1845, 40, ORANGE, WHITE, u, 0.2)
        pilule(img, "IA de reconnaissance faciale", W / 2, 1440 if t < rev else 150, 40, INK, WHITE, t, 0.1)
        mots_montants(img, "Elle te retrouve\nsur chaque photo.", W / 2, 1600 if t < rev else 1665, 72, WHITE, t, 0.6,
                      accent=["chaque"], sortie=rev - 0.25 if t < rev else None)
        return img

    # ------------------------------------------------------------ 5. la fin
    def fin(self, t):
        img = self.fond_sable_pagne.copy()
        img.alpha_composite(Image.new("RGBA", (W, H), (244, 239, 230, 175)))
        p = lourd(t - 0.05)
        coller_centre(img, self.logo_clair, W / 2, 560 - 8 * math.sin(t * 1.4), 0.78 * min(p, 1.04))
        for mot, t0, y, col in (("Scanne.", 0.3, 900, INK), ("Retrouve.", 1.68, 1060, INK), ("Repars avec.", 3.22, 1220, ORANGE)):
            if t >= t0:
                q = vif(t - t0)
                texte(img, mot, W / 2, y + 2 * math.sin(t * 2 + y), 110, col, echelle=1.35 - 0.35 * min(q, 1.0),
                      opacite=clamp((t - t0) / 0.08), ombre=False)
        texte(img, "myfaceci.online", W / 2, 1700, 44, (90, 100, 102), chemin=F_BOLD, opacite=clamp((t - 3.6) / 0.3), ombre=False)
        return camera(img, 1.0 + 0.035 * io(t / 4.5), W / 2, H / 2)


def mix_(a, b, p):
    return a + (b - a) * p


def sons(a):
    """Bruitages : (nom, instant du film, gain[, pan[, duree]])."""
    out = [("declencheur", a("selfie", 1.35), 0.55), ("scintille", a("selfie", 1.4), 0.25),
           ("balayage", a("scan", 0.0), 0.18, 0.0, 1.7)]
    out += [("tic", a("scan", 0.25 * k), 0.12) for k in range(1, 8)]
    out += [("bip", a("scan", t), 0.12, 0.3) for t in (0.5, 0.85, 1.2, 1.5)]
    out += [("envolee", a("eventail", 0.05), 0.25)]
    out += [("pop", a("eventail", 0.2 + k * 0.045), 0.09, (k - 4.5) / 6) for k in range(10)]
    out += [("pop", a("eventail", 0.9), 0.2)]
    out += [("envolee", a("ia", 0.0), 0.3)] + [("coup", a("ia", 0.5 * k), 0.28) for k in range(1, 6)]
    out += [("envolee", a("ia", 3.0), 0.2)] + [("pop", a("ia", 3.1 + i * 0.03), 0.07, (i % 3 - 1) * 0.4) for i in range(10)]
    out += [("envolee", a("fin", 0.0), 0.2), ("scintille", a("fin", 0.15), 0.3)]
    out += [("coup", a("fin", t), 0.4) for t in (0.3, 1.68, 3.22)]
    return out


if __name__ == "__main__":
    principal(FilmS3)
