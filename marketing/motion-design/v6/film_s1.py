# -*- coding: utf-8 -*-
"""S1 « Tu as déjà vécu ça ? » (35 s, invites 18-40 ans). Voir v6/STORYBOARD.md.

Message : la frustration des photos introuvables, puis MYFACE qui la regle ; ton urgent
(la nuit, le groupe qui deborde, l'heure perdue) qui bascule en franc et eclatant au
moment ou la musique tombe (« Avec MyFace, c'est terminé »). Vrais ecrans de l'evenement
de demonstration (captures du 27/10) ; le QR code est un vrai code vers cet evenement.

    python marketing/motion-design/v6/film_s1.py [--images | --brouillon | --decoupage]
"""

import io as _io
import math
import random

import numpy as np
import segno
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from moteur_v6 import (EH, EW, F_BOLD, F_DISPLAY, GREEN, H, INK, ORANGE, WHITE, W, FilmV6, cam_cles, camera,
                       clamp, coller, coller_centre, coups, degrade_vertical, expo, grain, io, lourd, mots_montants,
                       o5, pilule, point_cap, police, principal, texte, vif, voile)
from moteur_v6 import ELE

MARIE = 0
COUPLE = "pexels-joshua-j-lewis-1577020288-27333351.jpg"
URL_DEMO = "https://app.myfaceci.online/event/6b3391d9-e2eb-4942-990b-ac1353cd170e"


def mix_(a, b, p):
    return a + (b - a) * p


class FilmS1(FilmV6):
    NOM = "S1"
    VOIX = "S1-avez-vous-deja-vecu-ca"
    LIGNES = [
        ("soiree", 0.06, 5.42, 6.0, 0.2),
        ("groupe", 6.18, 11.28, 6.0, 0.2),
        ("heure", 12.10, 15.52, 4.0, 0.2),
        ("coupure", 16.34, 19.44, 4.0, 0.15),
        ("qr", 20.02, 23.94, 4.5, 0.2),
        ("ia", 24.42, 29.14, 5.5, 0.2),
        ("fin", 29.76, 33.06, 4.0, 0.3),
    ]
    TRANSITIONS = {
        "groupe": ("bandes", 0.5, {"n": 5, "vertical": False}),
        "ia": ("poussee", 0.45),
        "fin": ("iris", 0.4, {"cx": W / 2, "cy": 1500}),
    }
    DROP = "coupure"

    def __init__(self):
        super().__init__()
        rng = random.Random(11)
        noms = sorted(self.visages)
        # la nuit : photos de la fete assombries, chaudes, floues
        self.nuit = []
        for nom in (noms[2], noms[9], noms[5], noms[12]):
            im = self.cadrer(nom, W + 160, H + 160)[0].convert("RGB")
            im = ImageEnhance.Brightness(im).enhance(0.55)
            im = ImageEnhance.Color(im).enhance(0.8)
            arr = np.asarray(im).astype(np.float32)
            arr *= np.array([1.08, 0.92, 0.78])
            im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))
            self.nuit.append(im.convert("RGBA"))
        self.flashs = sorted(rng.uniform(1.6, 5.8) for _ in range(9))
        # le QR code (vrai lien vers l'evenement de demonstration)
        buf = _io.BytesIO()
        segno.make(URL_DEMO, error="m").save(buf, kind="png", scale=12, border=2, dark=(14, 36, 41), light="white")
        self.qr_img = Image.open(buf).convert("RGBA")
        self.chevalet = self._chevalet()
        # captures
        self.ecran_galerie = self.cap["02"]
        self.ecran_visages = self.cap["03"]
        self.ecran_personne = self.cap["04"]
        self.fond_pagne = Image.open(ELE / "fond-encre-pagne.png").convert("RGBA")

    def _chevalet(self):
        c = Image.new("RGBA", (560, 760), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle([0, 0, 559, 759], radius=34, fill=(250, 247, 242, 255))
        d.text((280, 70), "Vos photos", font=police(F_DISPLAY, 46), fill=INK, anchor="mm")
        d.text((280, 125), "Scannez-moi", font=police(F_BOLD, 32), fill=ORANGE, anchor="mm")
        q = self.qr_img.resize((440, 440), Image.NEAREST)
        c.alpha_composite(q, (60, 175))
        c.alpha_composite(self.logo_clair.resize((300, int(300 * self.logo_clair.height / self.logo_clair.width)), Image.LANCZOS),
                          (130, 650))
        return c

    # ------------------------------------------------------------ 1. la soiree (nuit, flashs)
    def soiree(self, t):
        if t < 1.25:
            img = Image.new("RGBA", (W, H), (8, 16, 18, 255))
            mots_montants(img, "Tu as déjà\nvécu ça ?", W / 2, H / 2, 128, WHITE, t, 0.0, ecart=0.07, accent=["ça"])
            if t < 0.25:      # un flash d'appareil photo des la premiere image
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 250, 240, int(235 * (1 - t / 0.25) ** 2))))
            return img
        u = t - 1.25
        k = min(len(self.nuit) - 1, int(u / 1.2))
        img = Image.new("RGBA", (W, H))
        dx = 40 * math.sin(u * 0.9) + 30 * k
        coller(img, self.nuit[k], -80 + dx * 0.5, -80 + 20 * math.cos(u * 1.1))
        # les flashs du photographe
        for f in self.flashs:
            if 0 <= t - f < 0.22:
                a = (1 - (t - f) / 0.22) ** 2
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 250, 240, int(230 * a))))
        mots_montants(img, "Le photographe a\nmitraillé toute la nuit…", W / 2, 1620, 64, WHITE, t, 1.5, accent=["mitraillé"])
        img = grain(img, t, 9)
        return camera(img, 1.04 + 0.03 * u / 4.7, W / 2, H / 2, 1.2 * math.sin(u * 0.7))

    # ------------------------------------------------------------ 2. le lendemain, le groupe
    def groupe(self, t):
        img = degrade_vertical((232, 226, 214), (214, 204, 188))
        rien = 2.3                       # « Rien. » puis le deluge
        if t < rien:                     # le groupe est vide : les messages sont encore sous l'ecran
            defil, compteur = -1500, 0
        else:
            u = t - rien
            defil = -1500 + 4100 * expo(u / 3.2) + 60 * u
            compteur = int(512 * clamp(u / 2.6) ** 1.4)
        ecran = self._ecran_chat(t, defil, compteur)
        cy = 1010 + 8 * math.sin(t * 2)
        self.telephone_ecran(img, ecran, W / 2, cy, 0.86, -2.5)
        mots_montants(img, "Le lendemain ?", W / 2, 150, 84, INK, t, 0.15, sortie=rien - 0.3, chemin=F_DISPLAY)
        if 1.2 <= t < rien:
            pilule(img, "Rien.", W / 2, 1010, 64, INK, WHITE, t, 1.25)
        if t >= rien:
            n = int(512 * clamp((t - rien) / 2.6) ** 1.4)
            texte(img, f"{n} photos", W / 2, 150, 104, INK, ombre=False, echelle=1 + coups(t, [rien + 2.6], 0.12))
            mots_montants(img, "Toutes floues.", W / 2, 1790, 84, ORANGE, t, rien + 1.2)
        return img

    # ------------------------------------------------------------ 3. une heure plus tard
    def heure(self, t):
        img = degrade_vertical((40, 44, 46), (16, 20, 22))
        defil = 2600 + 60 * 3 + 1600 * t
        ecran = self._ecran_chat(t, defil, 512)
        self.telephone_ecran(img, ecran, W / 2, 1060, 0.80)
        # le pouce qui fait defiler sans fin
        for k in range(8):
            t0 = 0.25 + k * 0.42
            pt = self.point_ecran(EW * 0.55, 1150, W / 2, 1060, 0.80)
            self.main.dessiner(img, pt, t, t0, "droite")
        # l'horloge : 60 minutes en quatre secondes
        c, r = (W / 2, 250), 120
        d = ImageDraw.Draw(img)
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(250, 247, 242), outline=ORANGE, width=10)
        m = 60 * clamp(t / 3.4)
        d.pieslice([c[0] - r + 18, c[1] - r + 18, c[0] + r - 18, c[1] + r - 18], -90, -90 + 6 * m, fill=(255, 210, 180))
        a = math.radians(6 * m - 90)
        d.line([c, (c[0] + 90 * math.cos(a), c[1] + 90 * math.sin(a))], fill=INK, width=8)
        d.ellipse([c[0] - 10, c[1] - 10, c[0] + 10, c[1] + 10], fill=INK)
        texte(img, f"{int(m)} min", W / 2, 440, 56, WHITE, chemin=F_BOLD)
        mots_montants(img, "…et toujours pas toi.", W / 2, 1830, 70, WHITE, t, 2.3, accent=["toi."])
        # la fin : l'image se fige et se decolore (arret sur image avant la coupure)
        fige = 3.65
        if t >= fige:
            gris = img.convert("L").convert("RGBA")
            img = Image.blend(img, gris, clamp((t - fige) / 0.15))
        return img

    # ------------------------------------------------------------ 4. la coupure (la musique tombe)
    def coupure(self, t):
        img = Image.new("RGBA", (W, H), (*INK, 255))
        p = lourd(t - 0.2)
        coller_centre(img, self.logo_fonce, W / 2, H / 2 - 40, 0.95 * min(p, 1.03) * (1 + coups(t, [0.2, 1.7], 0.03)))
        flood = 1.55
        if t >= flood:
            from moteur_v6 import masque_rond, rayon_couvrant
            q = expo((t - flood) / 0.35)
            plein = Image.new("RGBA", (W, H), (*ORANGE, 255))
            img.paste(plein, (0, 0), masque_rond(W / 2, H / 2 - 40, rayon_couvrant(W / 2, H / 2 - 40) * q))
            if t >= flood + 0.25:
                mots_montants(img, "C'est terminé.", W / 2, H / 2, 120, WHITE, t, flood + 0.25, ecart=0.08)
        return camera(img, 1.0 + 0.02 * io(t / 4), W / 2, H / 2)

    # ------------------------------------------------------------ 5. le QR code, « Trouver mon visage »
    def qr(self, t):
        img = degrade_vertical((250, 140, 70), ORANGE)
        bascule = 1.9                         # le telephone passe de l'appareil photo a la galerie
        z = 1.0 + 0.06 * io(t / bascule) if t < bascule else 1.0
        coller_centre(img, ombre_douce(self.chevalet), W / 2 + 14, 640 + 30, z)
        coller_centre(img, self.chevalet, W / 2, 640, z, -3 + 1.5 * math.sin(t))
        # le telephone arrive et vise le QR
        e = vif(t - 0.15)
        cx, cy, ech = W / 2 + 120 * (1 - e), 1420 + 600 * (1 - e) - 400 * io((t - bascule) / 0.5), 0.72
        if t < bascule:
            ecran = Image.new("RGBA", (EW, EH), (20, 20, 20, 255))
            vue = self.chevalet.resize((int(560 * 0.9), int(760 * 0.9)), Image.LANCZOS)
            coller_centre(ecran, vue, EW / 2, EH / 2 - 80, 1.0)
            coller_centre(ecran, self.coins, EW / 2, EH / 2 - 60, 0.5 * (1 + 0.05 * math.sin(t * 8)))
            if t > 1.3:
                pilule(ecran, "Galerie de l'événement", EW / 2, EH - 220, 30, WHITE, INK, t, 1.3)
        else:
            ecran = self.ecran_galerie.copy()
        self.telephone_ecran(img, ecran, cx, cy, ech, 0, clamp((t - 0.1) / 0.2))
        tap = 3.55
        if t >= bascule:
            pt = self.toucher(img, *point_cap(933, 280), cx, cy, ech, t, tap)
            if t >= tap:
                pilule(img, "Trouver mon visage", pt[0], pt[1] - 120, 40, INK, WHITE, t, tap)
        mots_montants(img, "Scanne le QR code", W / 2, 150, 76, WHITE, t, 0.3, sortie=bascule + 0.4)
        return img

    # ------------------------------------------------------------ 6. l'IA sort tes photos, qualite d'origine
    def ia(self, t):
        if t < 2.9:
            img = degrade_vertical((24, 48, 52), INK)
            cx, cy, ech = W / 2, 1010, 0.84
            tap = 0.9
            ecran = self.ecran_visages if t < tap + 0.25 else self.ecran_personne
            self.telephone_ecran(img, ecran, cx, cy, ech)
            face = point_cap(266, 722)
            if t < tap + 0.25:
                pt = self.point_ecran(*face, cx, cy, ech)
                coller_centre(img, self.coins, *pt, 0.2 * (1 + 0.08 * math.sin(t * 9)))
            self.toucher(img, *face, cx, cy, ech, t, tap)
            pilule(img, "IA de reconnaissance faciale", W / 2, 150, 40, ORANGE, WHITE, t, 0.1)
            mots_montants(img, "Toutes tes photos.", W / 2, 1830, 80, WHITE, t, 1.3, accent=["photos."])
            z, x, y = cam_cles(t, [(0, 1.0, W / 2, H / 2), (0.8, 1.08, W / 2 - 60, H / 2 - 120), (1.4, 1.0, W / 2, H / 2)])
            return camera(img, z, x, y)
        u = t - 2.9
        img = Image.new("RGBA", (W, H))
        coller_centre(img, self.flou, W / 2, H / 2, 1.04)
        split = W * io(u / 1.3)
        if split > 0:
            img.alpha_composite(self.net.crop((0, 0, int(split), H)).resize((int(split), H)), (0, 0))
            d = ImageDraw.Draw(img)
            if split < W - 2:
                d.rectangle([split - 4, 0, split + 4, H], fill=ORANGE)
                d.ellipse([split - 38, H / 2 - 38, split + 38, H / 2 + 38], fill=ORANGE)
        self.degrade_haut(img, 420, 180)
        pilule(img, "Qualité d'origine", W / 2, 170, 52, ORANGE, WHITE, u, 0.5)
        return img

    # ------------------------------------------------------------ 7. la fin
    def fin(self, t):
        img = self.fond_pagne.copy()
        voile(img, INK, 0.55)
        coller_centre(img, self.logo_fonce, W / 2, 520 + 6 * math.sin(t * 1.3), 0.82 * min(lourd(t - 0.1), 1.03))
        for mot, t0, y, col in (("Scanne.", 1.32, 860, WHITE), ("Retrouve.", 2.10, 1020, WHITE), ("Repars avec.", 2.90, 1180, ORANGE)):
            mots_montants(img, mot, W / 2, y, 112, col, t, t0 - 0.08, duree=0.35)
        pilule(img, "Trouver mon visage", W / 2, 1480, 46, ORANGE, WHITE, t, 3.2)
        texte(img, "myfaceci.online", W / 2, 1640, 42, (200, 210, 212), chemin=F_BOLD, opacite=clamp((t - 3.3) / 0.3))
        return camera(img, 1.0 + 0.03 * io(t / 4), W / 2, H / 2)


def ombre_douce(im):
    o = Image.new("RGBA", im.size, (0, 0, 0, 0))
    o.putalpha(im.split()[3].point(lambda a: int(a * 0.35)))
    return o.filter(ImageFilter.GaussianBlur(18))


def sons(a):
    out = [("notif", a("soiree", 0.05), 0.12)]
    out += [("declencheur", f, 0.35, (k % 3 - 1) * 0.5) for k, f in enumerate(FilmS1.FLASHS)]
    out += [("papier", a("groupe", 0.0), 0.3), ("coup", a("groupe", 1.25), 0.35)]
    t, pas = a("groupe", 2.3), 0.45
    while t < a("groupe", 5.6):
        out.append(("notif", t, 0.14, 0.3 * math.sin(t * 7)))
        t += pas
        pas = max(0.09, pas * 0.86)
    out += [("toucher", a("heure", 0.25 + k * 0.42), 0.25) for k in range(8)]
    out += [("tic", a("heure", k * 0.25), 0.12) for k in range(14)]
    out += [("erreur", a("heure", 2.35), 0.25)]
    out += [("scintille", a("coupure", 0.25), 0.35), ("envolee", a("coupure", 1.55), 0.35), ("coup", a("coupure", 1.8), 0.4)]
    out += [("envolee", a("qr", 0.15), 0.25), ("bip", a("qr", 1.2), 0.3), ("pop", a("qr", 1.9), 0.25),
            ("toucher", a("qr", 3.55), 0.4)]
    out += [("toucher", a("ia", 0.9), 0.4), ("envolee", a("ia", 1.1), 0.25)]
    out += [("pop", a("ia", 1.2 + k * 0.05), 0.07) for k in range(10)]
    out += [("balayage", a("ia", 2.9), 0.2, 0.0, 1.3), ("scintille", a("ia", 4.2), 0.3)]
    out += [("coup", a("fin", t), 0.4) for t in (1.32, 2.10, 2.90)] + [("pop", a("fin", 3.2), 0.25)]
    return out


# instants des flashs en temps du film (la scene « soiree » commence a 0)
FilmS1.FLASHS = sorted(random.Random(11).uniform(1.6, 5.8) for _ in range(9))

if __name__ == "__main__":
    principal(FilmS1)
