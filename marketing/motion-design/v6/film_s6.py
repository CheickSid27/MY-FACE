# -*- coding: utf-8 -*-
"""S6 « Photographes » (28 s, vouvoiement). Voir v6/STORYBOARD.md.

Message : deposez vos photos, l'IA trie, un seul lien, vos invites paient par Mobile Money ;
ton direct, entre professionnels, energique sur la fin. Aucune vente reelle n'existe encore :
le graphique des ventes est marque « Exemple ». Visages : vraies boites de l'IA sur
l'evenement de demonstration ; la page d'inscription photographe est une capture du 27/10.

    python marketing/motion-design/v6/film_s6.py [--images | --brouillon | --decoupage]
"""

import math
import random

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from moteur_v6 import (EH, EW, F_BOLD, F_DISPLAY, GREEN, H, INK, ORANGE, WHITE, W, FilmV6, cam_cles, camera, clamp,
                       coller, coller_centre, coups, degrade_vertical, entree_cubique, etiquette, expo, io, lourd,
                       mots_montants, o5, pilule, police, principal, rond, sortie_cubique, texte, vif, voile)

GROUPE = "pexels-joshua-j-lewis-1577020288-27333350.jpg"      # 6 visages
CREME = (245, 241, 234)
GRIS = (120, 128, 130)


def mix_(a, b, p):
    return a + (b - a) * p


class FilmS6(FilmV6):
    NOM = "S6"
    VOIX = "S6-photographes"
    LIGNES = [
        ("invendus", 0.18, 4.72, 5.0, 0.2),
        ("depot", 5.72, 8.08, 3.0, 0.2),
        ("ia", 8.48, 11.82, 4.0, 0.15),
        ("lien", 12.48, 14.92, 3.0, 0.2),
        ("paie", 15.68, 20.10, 5.0, 0.2),
        ("ventes", 20.86, 24.46, 4.0, 0.2),
        ("fin", 25.22, 27.48, 3.0, 0.25),
    ]
    TRANSITIONS = {
        "depot": ("inondation", 0.55, {"cx": W / 2, "cy": 900, "couleur": ORANGE}),
        "lien": ("poussee", 0.45),
        "paie": ("bandes", 0.45, {"n": 4, "vertical": False}),
        "fin": ("iris", 0.4, {"cx": W / 2, "cy": 1500}),
    }
    DROP = "depot"

    def __init__(self):
        super().__init__()
        rng = random.Random(66)
        self.chutes = []
        noms = sorted(self.visages)
        for k in range(26):
            nom = noms[k % len(noms)]
            ph = self.photo(nom)
            w, h = (300, 220) if ph.width > ph.height else (220, 300)
            im = self.cadrer(nom, w, h)[0]
            carte = Image.new("RGBA", (w + 24, h + 40), (250, 247, 242, 255))
            carte.alpha_composite(im, (12, 12))
            self.chutes.append({"img": carte, "x": rng.uniform(170, 910), "y": rng.uniform(900, 1580),
                                "a": rng.uniform(-35, 35), "t0": -0.3 + k * 0.11, "nom": nom})
        # l'IA : la photo de groupe, les vraies boites, les visages
        self.groupe_img = self.cadrer(GROUPE, W, H)[0]
        ph = self.photo(GROUPE)
        e = max(W / ph.width, H / ph.height)
        x0, y0 = (ph.width * e - W) / 2, (ph.height * e - H) / 2
        self.boites = []
        for f in sorted(self.visages[GROUPE]["visages"], key=lambda f: f["x1"]):
            cx, cy, c = (f["x1"] + f["x2"]) / 2 * e - x0, (f["y1"] + f["y2"]) / 2 * e - y0, (f["x2"] - f["x1"]) * e
            if 0 < cx < W:
                vis = self.groupe_img.crop((int(cx - c * 0.7), int(cy - c * 0.7), int(cx + c * 0.7), int(cy + c * 0.7)))
                self.boites.append((cx, cy, c, rond(vis, 150, 6), f["personne"]))
        self.ecran_inscription = self.cap["06"]

    # ------------------------------------------------------------ 1. les invendus
    def invendus(self, t):
        img = Image.new("RGBA", (W, H))
        coller(img, self.table, -30, -30)
        for c in self.chutes:
            if t < c["t0"]:
                continue
            p = lourd(t - c["t0"])
            y = -300 + (c["y"] + 300) * min(p, 1.02)
            coller_centre(img, c["img"], c["x"], y, 1.0, c["a"] * (0.5 + 0.5 * min(p, 1)))
        img = ImageEnhance.Color(img.convert("RGB")).enhance(0.5).convert("RGBA")
        self.degrade_haut(img, 620, 225)
        mots_montants(img, "Photographes,", W / 2, 150, 70, ORANGE, t, 0.1)
        mots_montants(img, "combien de photos\nvous restent sur les bras ?", W / 2, 330, 62, WHITE, t, 1.2)
        if t >= 3.4:
            q = lourd(t - 3.4)
            f = police(F_DISPLAY, 110)
            bb = f.getbbox("INVENDUES")
            tp = Image.new("RGBA", (bb[2] - bb[0] + 80, bb[3] - bb[1] + 70), (0, 0, 0, 0))
            d = ImageDraw.Draw(tp)
            d.rounded_rectangle([6, 6, tp.width - 6, tp.height - 6], radius=20, outline=(214, 60, 50, 255), width=10)
            d.text((40 - bb[0], 35 - bb[1]), "INVENDUES", font=f, fill=(214, 60, 50, 255))
            coller_centre(img, tp, W / 2, 1250, 2.0 - 1.0 * min(q, 1.02), -10, clamp((t - 3.4) / 0.06))
        return camera(img, 1.0 + 0.04 * io(t / 5) + coups(t, [3.45], 0.025, 0.1), W / 2, H / 2)

    # ------------------------------------------------------------ 2. le depot (la musique tombe)
    def depot(self, t):
        img = self.fond(bokeh=True)
        centre = (W / 2, 900)
        arrivees = [c["t0"] * 0.75 + 0.7 for c in self.cartes_depot]
        pouls = max([math.exp(-(t - a) / 0.12) for a in arrivees if t >= a] + [0.0])
        coller_centre(img, self.halo, *centre, 0.8 + 0.25 * pouls, 0, 0.5 + 0.45 * pouls)
        d = ImageDraw.Draw(img)
        r = 230 * (1 + 0.04 * pouls) * min(vif(t), 1.03)
        d.ellipse([centre[0] - r, centre[1] - r, centre[0] + r, centre[1] + r], fill=(*INK, 255), outline=ORANGE, width=8)
        coller_centre(img, self.logo_fonce, *centre, 0.36 * min(vif(t - 0.05), 1.03))
        for c in self.cartes_depot:
            u = (t - c["t0"] * 0.75) / 0.7
            if not 0 <= u <= 1:
                continue
            e = entree_cubique(u) * 0.35 + sortie_cubique(u) * 0.65
            x0, y0 = c["x0"], 2080
            xc, yc = (x0 + centre[0]) / 2 + c["cote"], 1500
            x = (1 - e) ** 2 * x0 + 2 * (1 - e) * e * xc + e ** 2 * centre[0]
            y = (1 - e) ** 2 * y0 + 2 * (1 - e) * e * yc + e ** 2 * centre[1]
            coller_centre(img, c["img"], x, y, 1.0 - 0.85 * e, c["a0"] * (1 - e), 1 - clamp((u - 0.82) / 0.18))
        mots_montants(img, "Déposez vos photos.", W / 2, 230, 80, WHITE, t, 0.15, accent=["Déposez"])
        pilule(img, "Aucun tri à faire", W / 2, 1450, 50, ORANGE, WHITE, t, 1.6)
        return img

    # ------------------------------------------------------------ 3. l'IA reconnait chaque visage
    def ia(self, t):
        img = self.groupe_img.copy()
        voile(img, INK, 0.2 + 0.4 * clamp((t - 2.0) / 0.5))
        n = len(self.boites)
        for k, (x, y, c, rv, pers) in enumerate(self.boites):
            t0 = 0.25 + k * 0.15
            if t < t0:
                continue
            if t < 2.0:
                p = vif(t - t0)
                coller_centre(img, self.coins, x, y, c * 1.4 / self.coins.width * (1.5 - 0.5 * min(p, 1)), 0, clamp((t - t0) / 0.1))
            else:
                # chaque visage file a sa place dans la rangee des personnes
                q = vif(t - 2.0 - k * 0.06)
                tx = W / 2 + (k - (n - 1) / 2) * 165
                ty = 1420
                coller_centre(img, rv, mix_(x, tx, min(q, 1)), mix_(y, ty, min(q, 1)), mix_(c * 1.4 / 150, 1.0, min(q, 1)))
                if q > 0.9:
                    texte(img, f"{k + 1}", tx, ty + 110, 34, WHITE, chemin=F_BOLD)
        pilule(img, "IA de reconnaissance faciale", W / 2, 150, 44, ORANGE, WHITE, t, 0.15)
        if t >= 2.4:
            mots_montants(img, "Chaque visage reconnu.", W / 2, 1720, 70, WHITE, t, 2.4, accent=["reconnu."])
        return img

    # ------------------------------------------------------------ 4. un seul lien
    def lien(self, t):
        img = degrade_vertical((232, 226, 214), (214, 204, 188))
        ecran = self._ecran_chat(t, 900, 0)
        d = ImageDraw.Draw(ecran)
        envoi = 0.9
        if t >= envoi:
            p = vif(t - envoi)
            y = 1060 - 40 * (1 - min(p, 1))
            carte = Image.new("RGBA", (500, 200), (0, 0, 0, 0))
            dc = ImageDraw.Draw(carte)
            dc.rounded_rectangle([0, 0, 499, 199], radius=26, fill=(220, 248, 198))
            dc.rounded_rectangle([18, 18, 120, 120], radius=18, fill=INK)
            carte.alpha_composite(self.logo_fonce.resize((90, int(90 * self.logo_fonce.height / self.logo_fonce.width))), (24, 50))
            dc.text((140, 30), "Vos photos du mariage", font=police(F_BOLD, 26), fill=INK)
            dc.text((140, 72), "app.myfaceci.online/e/…", font=police(F_BOLD, 22), fill=(40, 116, 160))
            dc.text((140, 150), "21:48 ✓✓", font=police(F_BOLD, 20), fill=GRIS)
            coller(ecran, carte, EW - 520, y, clamp((t - envoi) / 0.1))
        self.telephone_ecran(img, ecran, W / 2, 1060 + 8 * math.sin(t * 2), 0.84)
        texte(img, "1", W / 2 - 250, 190, 210, ORANGE, ombre=False, echelle=1.2 - 0.2 * min(lourd(t - 0.1), 1.0))
        mots_montants(img, "seul lien", W / 2 + 110, 200, 96, INK, t, 0.2)
        return img

    # ------------------------------------------------------------ 5. un selfie, Mobile Money
    def paie(self, t):
        img = self.fond(bokeh=True)
        coller_centre(img, self.tel["12-panier-paiement"], W / 2, H / 2 + 160 + 8 * math.sin(t * 2), 0.82)
        moyens = [("Wave", (29, 200, 238)), ("Orange Money", (255, 121, 0)), ("MTN Money", (255, 204, 0)), ("Moov Money", (0, 91, 170))]
        for i, (m, col) in enumerate(moyens):
            t0 = 2.3 + i * 0.18
            x, y = (290, 760) if i % 2 == 0 else (790, 760)
            y = 260 + (i // 2) * 130
            x = 300 if i % 2 == 0 else 780
            pilule(img, m, x, y, 42, col, INK if m == "MTN Money" else WHITE, t, t0)
        if t < 2.2:
            sel = self.boites[0][3] if self.boites else None
            if sel is not None:
                coller_centre(img, sel, W / 2, 330, 1.4 * min(vif(t - 0.1), 1.03))
            pilule(img, "Un selfie", W / 2, 520, 44, ORANGE, WHITE, t, 0.3)
        from rendre_film_v4 import etiquette_coche
        etiquette_coche(img, "Paiement Mobile Money", W / 2, 1830, 48, t, 3.4, self.coche)
        return img

    # ------------------------------------------------------------ 6. vous vendez plus
    def ventes(self, t):
        img = degrade_vertical((30, 56, 60), INK)
        oy = 600                    # marge transparente au-dessus de la carte : la barre qui creve y monte
        carte = Image.new("RGBA", (900, 1000 + oy), (0, 0, 0, 0))
        d = ImageDraw.Draw(carte)
        d.rounded_rectangle([0, oy, 899, oy + 999], radius=40, fill=CREME)
        d.text((50, oy + 50), "Ventes de photos", font=police(F_BOLD, 44), fill=INK)
        d.rounded_rectangle([520, oy + 46, 730, oy + 100], radius=27, fill=(226, 220, 210))
        d.text((625, oy + 73), "Exemple", font=police(F_BOLD, 28), fill=GRIS, anchor="mm")
        hauteurs = [0.22, 0.3, 0.28, 0.42, 0.5, 0.48, 0.66, 0.78, 1.0]
        creve = 2.3                 # la surprise : la derniere barre creve le haut de la carte
        for k, hb in enumerate(hauteurs):
            q = lourd(t - 0.3 - k * 0.12)
            x0 = 70 + k * 90
            haut = 640 * hb * min(max(q, 0), 1.02)
            if k == len(hauteurs) - 1 and t >= creve:
                haut = 640 + 520 * min(lourd(t - creve), 1.03)
            d.rounded_rectangle([x0, oy + 900 - haut, x0 + 62, oy + 900], radius=14,
                                fill=ORANGE if k == len(hauteurs) - 1 else (246, 170, 120))
        coller_centre(img, carte, W / 2, 900 - oy / 2, 0.96 + 0.04 * min(vif(t), 1))
        mots_montants(img, "Plus de ventes.\nZéro tri.", W / 2, 1620, 88, WHITE, t, 1.4, accent=["Zéro", "tri."])
        return camera(img, 1.0 + 0.03 * io(t / 4), W / 2, H / 2)

    # ------------------------------------------------------------ 7. ouvrez votre compte
    def fin(self, t):
        img = self.fond_sable_pagne.copy()
        img.alpha_composite(Image.new("RGBA", (W, H), (244, 239, 230, 165)))
        self.telephone_ecran(img, self.ecran_inscription, W / 2, 1150 + 8 * math.sin(t * 2), 0.6)
        coller_centre(img, self.logo_clair, W / 2, 200, 0.62 * min(lourd(t - 0.05), 1.03))
        mots_montants(img, "Ouvrez votre\ncompte photographe.", W / 2, 470, 74, INK, t, 0.6, accent=["photographe."])
        texte(img, "myfaceci.online", W / 2, 1840, 42, (90, 100, 102), chemin=F_BOLD, ombre=False, opacite=clamp((t - 1.5) / 0.3))
        return camera(img, 1.0 + 0.03 * io(t / 3), W / 2, H / 2)


def sons(a):
    out = [("papier", a("invendus", max(0.0, -0.3 + k * 0.11 + 0.3)), 0.12, (k % 5 - 2) * 0.2) for k in range(26)]
    out += [("impact", a("invendus", 3.4), 0.45)]
    out += [("pop", a("depot", c * 0.75 + 0.7), 0.07, (i % 5 - 2) * 0.2)
            for i, c in enumerate(0.35 + k * 0.155 for k in range(22))]
    out += [("pop", a("depot", 1.6), 0.25)]
    out += [("bip", a("ia", 0.25 + k * 0.15), 0.18) for k in range(6)]
    out += [("envolee", a("ia", 2.0), 0.3)] + [("pop", a("ia", 2.1 + k * 0.06), 0.1) for k in range(6)]
    out += [("envolee", a("lien", 0.0), 0.25), ("notif", a("lien", 0.9), 0.35)]
    out += [("pop", a("paie", 0.1), 0.25), ("declencheur", a("paie", 0.3), 0.3)]
    out += [("pop", a("paie", 2.3 + i * 0.18), 0.18, (i - 1.5) * 0.4) for i in range(4)]
    out += [("caisse", a("paie", 3.4), 0.4)]
    out += [("pop", a("ventes", 0.3 + k * 0.12), 0.1) for k in range(9)] + [("scintille", a("ventes", 1.4), 0.3)]
    out += [("impact", a("ventes", 2.3), 0.4)]
    out += [("envolee", a("fin", 0.0), 0.25), ("coup", a("fin", 0.6), 0.35)]
    return out


if __name__ == "__main__":
    principal(FilmS6)
