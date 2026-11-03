# -*- coding: utf-8 -*-
"""S5 « La borne » (25 s, invites sans smartphone et organisateurs). Voir v6/STORYBOARD.md.

Message : meme sans smartphone, on repart avec sa photo imprimee ; ton simple puis fier.
Vrais ecrans de la borne (detoure/borne-*) ; le prix dit par la voix (700 F photo et tirage
compris) est le prix par defaut de l'appli (backend/app/services/pricing.py,
print_bundle_price), regle pour chaque evenement : l'ecran le precise.

    python marketing/motion-design/v6/film_s5.py [--images | --brouillon | --decoupage]
"""

import math

from PIL import Image, ImageDraw, ImageFilter

from moteur_v6 import (EH, EW, F_BOLD, F_DISPLAY, GREEN, H, INK, ORANGE, WHITE, W, FilmV6, cam_cles, camera, clamp,
                       coller, coller_centre, coups, degrade_vertical, etiquette, expo, io, lourd, mots_montants, o5,
                       pilule, police, principal, rond, texte, vif, voile)

COUPLE = "pexels-joshua-j-lewis-1577020288-27333351.jpg"
ECRAN_BORNE = (202, 197, 878, 1416)      # trou de l'ecran dans borne-gros-plan-cadre.png (x0, y0, x1, y1)


def mix_(a, b, p):
    return a + (b - a) * p


class FilmS5(FilmV6):
    NOM = "S5"
    VOIX = "S5-la-borne"
    LIGNES = [
        ("sans_tel", 0.06, 2.28, 2.5, 0.2),
        ("selfie", 3.02, 5.66, 3.0, 0.2),
        ("photos", 6.10, 9.64, 4.0, 0.2),
        ("imprimer", 10.34, 12.46, 2.5, 0.15),
        ("especes", 13.04, 16.60, 4.0, 0.15),
        ("sortie", 17.26, 20.96, 4.5, 0.2),
        ("fin", 21.60, 25.08, 4.0, 0.25),
    ]
    TRANSITIONS = {
        "selfie": ("poussee", 0.5),
        "photos": ("iris", 0.4, {"cx": W / 2, "cy": 860}),
        "especes": ("bandes", 0.45, {"n": 4}),
        "fin": ("masque_texte", 0.7, {"mot": "MYFACE"}),
    }
    DROP = "sortie"

    def __init__(self):
        super().__init__()
        from rendre_film import DET, charger
        self.borne_img = dict(self.borne)
        self.borne_img["borne-gros-plan-cadre"] = charger(DET / "borne-gros-plan-cadre.png")
        vis, _ = self.cadrer(COUPLE, 520, 520, 0, 260, (0.5, 0.5))
        self.visage_rond = rond(vis, 520)
        self.cartes = [self._polaroid(n) for n in self.photos_de(0)[:6]]
        self.grand_tirage = self._polaroid(COUPLE, 620, 820)

    def _polaroid(self, nom, w=250, h=320):
        im = self.cadrer(nom, w, h, 0, w * 0.32, (0.5, 0.4))[0]
        c = Image.new("RGBA", (w + 30, h + 80), (250, 247, 242, 255))
        c.alpha_composite(im, (15, 15))
        return c

    def ecran_borne(self, img, contenu, nom="borne-gros-plan-cadre", echelle=1.0, cx=W / 2, cy=H / 2):
        """La borne en gros plan, avec un contenu dessine dans son ecran."""
        base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        x0, y0, x1, y1 = ECRAN_BORNE
        base.alpha_composite(contenu.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))
        base.alpha_composite(self.borne_img[nom])
        coller_centre(img, base, cx, cy, echelle)

    # ------------------------------------------------------------ 1. pas de smartphone
    def sans_tel(self, t):
        img = degrade_vertical((30, 56, 60), INK)
        # le telephone barre
        c = (W / 2, 900)
        tel = Image.new("RGBA", (300, 560), (0, 0, 0, 0))
        d = ImageDraw.Draw(tel)
        d.rounded_rectangle([10, 10, 290, 550], radius=46, outline=WHITE, width=16)
        d.rounded_rectangle([110, 34, 190, 54], radius=10, fill=WHITE)
        p = vif(t - 0.1)
        coller_centre(img, tel, *c, 0.8 + 0.2 * min(p, 1.03), -8 * (1 - min(p, 1)))
        barre = clamp((t - 0.6) / 0.25)
        if barre > 0:
            d2 = ImageDraw.Draw(img)
            a, b = (c[0] - 200, c[1] - 260), (c[0] + 200, c[1] + 260)
            d2.line([a, (mix_(a[0], b[0], barre), mix_(a[1], b[1], barre))], fill=ORANGE, width=34)
        mots_montants(img, "Pas de smartphone ?", W / 2, 1420, 80, WHITE, t, 0.15)
        mots_montants(img, "Pas de souci.", W / 2, 1580, 96, ORANGE, t, 1.5)
        return img

    # ------------------------------------------------------------ 2. le selfie a la borne
    def selfie(self, t):
        img = self.fond(bokeh=True)
        cam = Image.new("RGBA", (444, 795), (20, 24, 26, 255))
        coller_centre(cam, self.visage_rond, 222, 330, 0.75 + 0.01 * math.sin(t * 3))
        coller_centre(cam, self.coins, 222, 330, 0.42 * (1 + 0.04 * math.sin(t * 8)))
        d = ImageDraw.Draw(cam)
        d.rounded_rectangle([60, 640, 384, 720], radius=40, fill=ORANGE)
        d.text((222, 680), "Prendre la photo", font=police(F_BOLD, 30), fill=WHITE, anchor="mm")
        z, x, y = cam_cles(t, [(0, 1.0, W / 2, H / 2), (2.2, 1.18, W / 2, H / 2 - 120)])
        self.ecran_borne(img, cam)
        flash = 2.2
        pt = ((ECRAN_BORNE[0] + ECRAN_BORNE[2]) / 2, ECRAN_BORNE[1] + 680 * (ECRAN_BORNE[3] - ECRAN_BORNE[1]) / 795)
        self.onde_a(img, pt, t, flash)
        self.main.dessiner(img, pt, t, flash, "droite")
        if t >= flash + 0.1:
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(220 * clamp(1 - (t - flash - 0.1) / 0.35)))))
        etiquette(img, "Un selfie à la borne", W / 2, 150, 58, WHITE, t, 0.3)
        return camera(img, z, x, y)

    # ------------------------------------------------------------ 3. l'IA retrouve tes photos
    def photos(self, t):
        img = self.fond(bokeh=True)
        ecran = Image.new("RGBA", (444, 795), (245, 241, 234, 255))
        d = ImageDraw.Draw(ecran)
        d.text((222, 50), "10 photos trouvées", font=police(F_BOLD, 34), fill=INK, anchor="mm")
        for k, carte in enumerate(self.cartes):
            r_, c_ = divmod(k, 2)
            p = vif(t - 0.4 - k * 0.12)
            if p > 0:
                v = carte.resize((180, 230), Image.LANCZOS)
                coller_centre(ecran, v, 120 + c_ * 205, 200 + r_ * 245, min(p, 1.04))
        self.ecran_borne(img, ecran, echelle=1.0 + 0.02 * t)
        pilule(img, "IA de reconnaissance faciale", W / 2, 105, 44, ORANGE, WHITE, t, 0.2)
        mots_montants(img, "Toutes tes photos\nde la soirée.", W / 2, 1640, 72, INK, t, 2.0, accent=["photos"])
        return img

    # ------------------------------------------------------------ 4. coche « Imprimer »
    def imprimer(self, t):
        img = self.fond(bokeh=True)
        coller_centre(img, self.borne_img["borne-gros-plan-impression"], W / 2, H / 2, 1.04 + 0.02 * t)
        pt = self.points["P15"]
        tap = 1.1
        self.onde_a(img, pt, t, tap)
        self.main.dessiner(img, pt, t, tap, "droite")
        if t >= tap:
            pilule(img, "Imprimer", pt[0], pt[1] - 110, 46, ORANGE, WHITE, t, tap)
        return img

    # ------------------------------------------------------------ 5. espèces : 700 F
    def especes(self, t):
        img = self.fond(bokeh=True)
        coller_centre(img, self.borne_img["borne-gros-plan-especes"], W / 2, H / 2 + 80, 0.92)
        pt = self.points["P16"]
        pt = (W / 2 + (pt[0] - W / 2) * 0.92, H / 2 + 80 + (pt[1] - H / 2) * 0.92)
        self.onde_a(img, pt, t, 0.6)
        self.main.dessiner(img, pt, t, 0.6, "droite")
        pilule(img, "Espèces", W / 2, 140, 54, INK, WHITE, t, 0.3)
        if t >= 1.3:
            voile(img, INK, 0.45 * clamp((t - 1.3) / 0.3))
            p = lourd(t - 1.4)
            carte = Image.new("RGBA", (860, 470), (0, 0, 0, 0))
            dc = ImageDraw.Draw(carte)
            dc.rounded_rectangle([0, 0, 859, 469], radius=44, fill=(*INK, 245))
            coller_centre(img, carte, W / 2, 860, 0.85 + 0.15 * min(p, 1.02), 0, clamp((t - 1.3) / 0.12))
            texte(img, "700 F", W / 2, 790, 190, ORANGE, echelle=1.3 - 0.3 * min(p, 1.0), opacite=clamp((t - 1.4) / 0.1))
            texte(img, "la photo, tirage compris", W / 2, 960, 50, WHITE, chemin=F_BOLD, opacite=clamp((t - 2.6) / 0.25))
        pilule(img, "Prix fixé pour chaque événement", W / 2, 1830, 32, INK, WHITE, t, 2.0)
        return img

    # ------------------------------------------------------------ 6. 20 secondes, la photo sort (la musique tombe)
    def sortie(self, t):
        img = self.tirage_sort(min(t * 0.7, 2.0))
        # le chrono : 20 secondes en un tour
        c, r = (W - 180, 250), 110
        d = ImageDraw.Draw(img)
        q = clamp(t / 1.4)
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(*INK, 230))
        d.arc([c[0] - r + 10, c[1] - r + 10, c[0] + r - 10, c[1] + r - 10], -90, -90 + 360 * q, fill=ORANGE, width=16)
        d.text(c, f"{int(round(20 * q))} s", font=police(F_DISPLAY, 58), fill=WHITE, anchor="mm")
        if t >= 2.6:
            mots_montants(img, "En vrai papier.", W / 2, 1780, 96, WHITE, t, 2.7, accent=["papier."])
        return camera(img, 1.0 + coups(t, [0, 0.5, 1.0, 1.5, 2.0], 0.012), W / 2, H / 2)

    # ------------------------------------------------------------ 7. personne ne repart les mains vides
    def fin(self, t):
        img = self.fond_sable_pagne.copy()
        img.alpha_composite(Image.new("RGBA", (W, H), (244, 239, 230, 160)))
        coller_centre(img, self.grand_tirage, W / 2, 820 + 8 * math.sin(t * 1.5), 0.86, -4 + 2 * math.sin(t))
        coller_centre(img, self.logo_clair, W / 2, 200, 0.62 * min(lourd(t - 0.1), 1.03))
        mots_montants(img, "Personne ne repart\nles mains vides.", W / 2, 1560, 80, INK, t, 1.6, accent=["vides."])
        return camera(img, 1.0 + 0.03 * io(t / 4), W / 2, H / 2)


def sons(a):
    out = [("pop", a("sans_tel", 0.1), 0.25), ("erreur", a("sans_tel", 0.6), 0.3), ("scintille", a("sans_tel", 1.5), 0.3)]
    out += [("envolee", a("selfie", 0.0), 0.3), ("toucher", a("selfie", 2.2), 0.4), ("declencheur", a("selfie", 2.25), 0.5)]
    out += [("balayage", a("photos", 0.2), 0.18, 0.0, 0.6)] + [("pop", a("photos", 0.4 + k * 0.12), 0.15) for k in range(6)]
    out += [("toucher", a("imprimer", 1.1), 0.4), ("bip", a("imprimer", 1.15), 0.25)]
    out += [("toucher", a("especes", 0.6), 0.4), ("caisse", a("especes", 1.4), 0.4)]
    out += [("imprimante", a("sortie", 0.05), 0.5), ("scintille", a("sortie", 1.5), 0.35)]
    out += [("tic", a("sortie", 0.1 * k), 0.08) for k in range(14)]
    out += [("envolee", a("fin", 0.0), 0.25), ("scintille", a("fin", 0.2), 0.3), ("coup", a("fin", 1.6), 0.35)]
    return out


if __name__ == "__main__":
    principal(FilmS5)
