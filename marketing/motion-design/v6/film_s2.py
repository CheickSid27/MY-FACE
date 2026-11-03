# -*- coding: utf-8 -*-
"""S2 « Tantie Aya » (sketch, 35 s, a partager). Voir v6/STORYBOARD.md.

Message : meme Tantie Aya retrouve ses photos du mariage avec un selfie ; ton joueur et
chaleureux. Deux personnages dessines (Tantie Aya, voix Sulafat ; Koffi, voix Puck), dont la
bouche suit l'energie reelle de leur voix, puis la signature par Zephyr. Les photos de la
tantie sont des dessins d'elle : aucune vraie personne n'est presentee comme Tantie Aya.

    python marketing/motion-design/v6/film_s2.py [--images | --brouillon | --decoupage]
"""

import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from moteur_v6 import (EH, EW, F_BOLD, F_DISPLAY, GREEN, H, INK, ORANGE, WHITE, W, FilmV6, camera, clamp, coller,
                       coller_centre, coups, degrade_vertical, expo, io, lire_voix, lourd, mots_montants, o5, pilule,
                       police, principal, texte, vif, voile)
from moteur_v6 import ELE

PEAU, PEAU_F = (104, 64, 44), (82, 50, 34)
ROUGE, OR = (204, 38, 44), (222, 178, 60)
S2X = 2                       # dessin en double resolution, puis reduit (bords nets)


def mix_(a, b, p):
    return a + (b - a) * p


def membre(d, x0, y0, angle, long, ep, col):
    """Bras ou jambe : un trait epais aux bouts arrondis. -> (x, y) du bout."""
    a = math.radians(angle)
    x1, y1 = x0 + long * math.sin(a), y0 + long * math.cos(a)
    d.line([(x0, y0), (x1, y1)], fill=col, width=int(ep))
    for x, y in ((x0, y0), (x1, y1)):
        d.ellipse([x - ep / 2, y - ep / 2, x + ep / 2, y + ep / 2], fill=col)
    return x1, y1


def personnage(qui, bouche=0.0, yeux="ouverts", bras=("bas", "bas"), telephone=False, foulard=0.0):
    """Tantie Aya ou Koffi, de face, 620 x 1180 (avant reduction). bouche de 0 a 1.
    bras : pose de chaque bras ('bas', 'tendu', 'haut', 'hanche', 'danse')."""
    s = S2X
    L, Hh = 620 * s, 1180 * s
    im = Image.new("RGBA", (L, Hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    aya = qui == "aya"
    cx = L / 2
    tete_y = 330 * s
    rt = (150 if aya else 128) * s
    # --- le corps
    if aya:
        corps = [(cx - 190 * s, 560 * s), (cx + 190 * s, 560 * s), (cx + 250 * s, 1180 * s), (cx - 250 * s, 1180 * s)]
        d.polygon(corps, fill=(28, 44, 96))
        for yy in range(600, 1180, 64):
            for xx in range(-230, 240, 64):
                x, y = cx + xx * s + (yy // 64 % 2) * 32 * s, yy * s
                d.ellipse([x - 11 * s, y - 11 * s, x + 11 * s, y + 11 * s], fill=ORANGE)
                d.polygon([(x + 32 * s, y + 4 * s), (x + 46 * s, y + 22 * s), (x + 32 * s, y + 40 * s), (x + 18 * s, y + 22 * s)],
                          outline=(244, 239, 230), width=3 * s)
        d.rounded_rectangle([cx - 200 * s, 540 * s, cx + 200 * s, 640 * s], radius=50 * s, fill=(28, 44, 96))
        epaule, couleur_bras = 175, PEAU
    else:
        d.rounded_rectangle([cx - 165 * s, 540 * s, cx + 165 * s, 1180 * s], radius=80 * s, fill=GREEN)
        d.rounded_rectangle([cx - 165 * s, 1000 * s, cx + 165 * s, 1180 * s], radius=10 * s, fill=(32, 40, 60))
        d.text((cx, 760 * s), "CI", font=police(F_DISPLAY, 90 * s), fill=(255, 255, 255, 200), anchor="mm")
        epaule, couleur_bras = 150, PEAU
    # --- les bras
    poses = {"bas": (8, 330), "tendu": (-78, 360), "haut": (-160, 330), "hanche": (40, 200), "danse": (-130, 330)}
    bouts = []
    for i, cote in enumerate((-1, 1)):
        pose = bras[i]
        ang, lg = poses[pose]
        x0, y0 = cx + cote * epaule * s, 600 * s
        if pose == "hanche":
            coude = membre(d, x0, y0, cote * -40, 190 * s, 70 * s, couleur_bras)
            bout = membre(d, *coude, cote * 60 + (180 if True else 0), 0.1, 70 * s, couleur_bras)
            bout = coude
        else:
            bout = membre(d, x0, y0, -cote * ang, lg * s, 70 * s, couleur_bras)
        bouts.append(bout)
        d.ellipse([bout[0] - 44 * s, bout[1] - 44 * s, bout[0] + 44 * s, bout[1] + 44 * s], fill=PEAU)
    if telephone:
        x, y = bouts[1]
        d.rounded_rectangle([x - 52 * s, y - 120 * s, x + 52 * s, y + 70 * s], radius=16 * s, fill=(20, 22, 26))
        d.rounded_rectangle([x - 42 * s, y - 108 * s, x + 42 * s, y + 58 * s], radius=10 * s, fill=(90, 160, 200))
    if foulard and aya:
        x, y = bouts[0]
        pts = []
        for k in range(14):
            u = k / 13
            pts.append((x + (-40 - 260 * u) * s * (1 if foulard > 0 else -1) * 0 + (-30 + 30 * math.sin(foulard * 6 + u * 5)) * s * 2,
                        y + (-30 - 300 * u + 40 * math.sin(foulard * 5 + u * 7)) * s))
        d.line(pts, fill=ROUGE, width=46 * s, joint="curve")
    # --- le cou et la tete
    d.rounded_rectangle([cx - 50 * s, tete_y + rt - 40 * s, cx + 50 * s, 580 * s], radius=20 * s, fill=PEAU_F)
    d.ellipse([cx - rt, tete_y - rt * 1.08, cx + rt, tete_y + rt * 1.08], fill=PEAU)
    # oreilles, boucles d'oreille
    for cote in (-1, 1):
        ox = cx + cote * rt * 0.98
        d.ellipse([ox - 24 * s, tete_y - 10 * s, ox + 24 * s, tete_y + 50 * s], fill=PEAU_F)
        if aya:
            d.ellipse([ox - 30 * s, tete_y + 40 * s, ox + 30 * s, tete_y + 110 * s], outline=OR, width=10 * s)
    # coiffure : foulard noue (Aya) ou casquette (Koffi)
    if aya:
        d.chord([cx - rt * 1.12, tete_y - rt * 1.75, cx + rt * 1.12, tete_y + rt * 0.25], 180, 360, fill=ROUGE)
        d.ellipse([cx - rt * 0.95, tete_y - rt * 1.9, cx + rt * 0.75, tete_y - rt * 0.85], fill=ROUGE)
        d.ellipse([cx + rt * 0.45, tete_y - rt * 1.75, cx + rt * 1.2, tete_y - rt * 1.0], fill=(230, 70, 60))
        for k in range(4):
            y = tete_y - rt * (0.4 + 0.28 * k)
            d.arc([cx - rt * 1.0, y - 40 * s, cx + rt * 1.0, y + 40 * s], 200, 340, fill=(160, 24, 30), width=6 * s)
    else:
        d.chord([cx - rt * 1.05, tete_y - rt * 1.25, cx + rt * 1.05, tete_y + rt * 0.1], 180, 360, fill=INK)
        d.rounded_rectangle([cx - rt * 1.05, tete_y - rt * 0.42, cx + rt * 1.55, tete_y - rt * 0.24], radius=12 * s, fill=INK)
        d.ellipse([cx - 12 * s, tete_y - rt * 1.2, cx + 12 * s, tete_y - rt * 1.05], fill=ORANGE)
    # yeux
    ey = tete_y - rt * 0.05
    for cote in (-1, 1):
        ex = cx + cote * rt * 0.38
        if yeux == "fermes":
            d.arc([ex - 30 * s, ey - 18 * s, ex + 30 * s, ey + 22 * s], 20, 160, fill=(30, 18, 12), width=7 * s)
        elif yeux == "joie":
            d.arc([ex - 30 * s, ey - 4 * s, ex + 30 * s, ey + 40 * s], 200, 340, fill=(30, 18, 12), width=8 * s)
        else:
            d.ellipse([ex - 30 * s, ey - 24 * s, ex + 30 * s, ey + 24 * s], fill=(250, 248, 244))
            d.ellipse([ex - 14 * s, ey - 14 * s, ex + 14 * s, ey + 14 * s], fill=(30, 18, 12))
            d.ellipse([ex - 4 * s, ey - 10 * s, ex + 4 * s, ey - 2 * s], fill=WHITE)
        d.line([(ex - 32 * s, ey - 46 * s), (ex + 30 * s, ey - 52 * s + cote * 4 * s)], fill=(30, 18, 12), width=8 * s)
    # joues, nez, bouche
    if aya:
        for cote in (-1, 1):
            d.ellipse([cx + cote * rt * 0.6 - 26 * s, ey + 40 * s, cx + cote * rt * 0.6 + 26 * s, ey + 70 * s], fill=(150, 70, 60))
    d.ellipse([cx - 22 * s, ey + 30 * s, cx + 22 * s, ey + 62 * s], fill=PEAU_F)
    my = tete_y + rt * 0.5
    ouv = (6 + 48 * bouche) * s
    lg = (50 + 10 * bouche) * s
    d.ellipse([cx - lg, my - ouv / 2, cx + lg, my + ouv / 2 + 6 * s], fill=(70, 20, 22))
    if bouche > 0.25:
        d.rectangle([cx - lg * 0.7, my - ouv / 2 + 2 * s, cx + lg * 0.7, my - ouv / 2 + 12 * s], fill=WHITE)
    d.arc([cx - lg - 4 * s, my - ouv / 2 - 6 * s, cx + lg + 4 * s, my + ouv / 2 + 10 * s], 0, 180,
          fill=(150, 40, 50) if aya else (90, 40, 34), width=8 * s)
    return im.resize((L // s, Hh // s), Image.LANCZOS)


def bulle(txt, larg=760, fond=WHITE, couleur=INK, taille=50, queue="gauche"):
    """Bulle de BD avec le texte coupe en lignes ; queue vers le personnage qui parle."""
    f = police(F_BOLD, taille)
    lignes, ligne = [], ""
    for m in txt.split(" "):
        essai = (ligne + " " + m).strip()
        if f.getlength(essai) > larg - 80 and ligne:
            lignes.append(ligne)
            ligne = m
        else:
            ligne = essai
    lignes.append(ligne)
    hl = int(taille * 1.25)
    w = int(max(f.getlength(l) for l in lignes)) + 80
    h = hl * len(lignes) + 60
    im = Image.new("RGBA", (w + 20, h + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 10, w + 10, h + 10], radius=40, fill=fond)
    qx = 90 if queue == "gauche" else w - 70
    d.polygon([(qx, h), (qx + 60, h), (qx + (0 if queue == "gauche" else 70), h + 70)], fill=fond)
    for i, l in enumerate(lignes):
        d.text((50, 40 + i * hl), l, font=f, fill=couleur)
    return im


class FilmS2(FilmV6):
    NOM = "S2"
    VOIX = "S2-tantie-aya"
    LIGNES = [
        ("demande", 0.04, 4.22, 4.5, 0.2),
        ("defile", 4.74, 7.76, 3.5, 0.2),
        ("foulard", 8.42, 11.28, 3.5, 0.2),
        ("scan", 11.88, 18.36, 6.5, 0.2),
        ("resultats", 19.04, 22.82, 4.0, 0.2),
        ("laisser", 23.52, 26.62, 3.5, 0.2),
        ("fin", 27.60, 33.46, 6.0, 0.3),
    ]
    QUI = {"demande": "aya", "defile": "koffi", "foulard": "aya", "scan": "koffi", "resultats": "aya", "laisser": "koffi"}
    TRANSITIONS = {
        "defile": ("fouet", 0.4, {"sens": 1}),
        "foulard": ("fouet", 0.4, {"sens": -1}),
        "resultats": ("inondation", 0.6, {"cx": W / 2, "cy": 900}),
        "fin": ("bandes", 0.55, {"n": 4}),
    }
    DROP = "resultats"

    def __init__(self):
        super().__init__()
        x, sr = lire_voix(self.VOIX)
        k = sr // 100
        env = np.sqrt(np.mean(x[: len(x) // k * k].reshape(-1, k) ** 2, 1))
        self.env = np.clip(env / (np.percentile(env, 95) + 1e-9), 0, 1)
        self.cache = {}
        self.salon = self._salon()
        # les « photos » de la tantie : des dessins d'elle, dans des cadres
        rng = random.Random(22)
        self.polas = []
        fonds = [(250, 190, 120), (120, 190, 200), (240, 140, 120), (180, 200, 120), (200, 160, 220), (250, 220, 140),
                 (140, 170, 230), (230, 180, 200), (170, 220, 190)]
        poses = [("joie", ("haut", "haut")), ("ouverts", ("danse", "bas")), ("ouverts", ("bas", "bas")),
                 ("joie", ("hanche", "haut")), ("ouverts", ("tendu", "bas")), ("joie", ("danse", "haut")),
                 ("fermes", ("bas", "bas")), ("ouverts", ("haut", "bas")), ("joie", ("bas", "danse"))]
        for i, (yeux, bras) in enumerate(poses):
            p = personnage("aya", 0.3 if yeux == "joie" else 0.0, yeux, bras, foulard=1.0 if "danse" in bras else 0.0)
            cadre = Image.new("RGBA", (300, 360), (250, 247, 242, 255))
            fond = Image.new("RGBA", (270, 270), (*fonds[i], 255))
            coller_centre(fond, p, 135, 210, 0.34)
            cadre.alpha_composite(fond, (15, 15))
            self.polas.append({"img": cadre, "a": rng.uniform(-8, 8)})
        self.idx_fermes = 6

    def _salon(self):
        img = degrade_vertical((246, 214, 170), (232, 190, 140))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 1420, W, H], fill=(196, 140, 96))
        for x in range(-200, W + 200, 120):
            d.line([(x, 1420), (x + 220, H)], fill=(180, 126, 84), width=6)
        # fenetre et plante, pour le decor
        d.rounded_rectangle([90, 230, 430, 640], radius=24, fill=(170, 210, 230), outline=(250, 244, 232), width=18)
        d.line([(260, 230), (260, 640)], fill=(250, 244, 232), width=12)
        d.rounded_rectangle([780, 1180, 940, 1430], radius=20, fill=ORANGE)
        for k in range(6):
            a = math.radians(-60 + k * 24)
            d.ellipse([860 + 160 * math.sin(a) - 50, 1150 - 160 * math.cos(a) - 24, 860 + 160 * math.sin(a) + 50,
                       1150 - 160 * math.cos(a) + 24], fill=(40, 130, 80))
        return img

    # ---- les personnages qui parlent
    def bouche(self, scene, t):
        """Ouverture de la bouche de celui qui parle, d'apres l'energie de sa voix."""
        for (nom, d, du), (a, b, deb) in zip(self.scenes_, self.voix_):
            if nom == scene:
                tw = a + (self.debut[scene] + t - deb)
                if a - 0.02 <= tw <= b:
                    return float(self.env[min(len(self.env) - 1, int(tw * 100))])
        return 0.0

    def perso(self, qui, bouche=0.0, yeux="ouverts", bras=("bas", "bas"), telephone=False, foulard=0.0):
        cle = (qui, round(bouche * 4) / 4, yeux, bras, telephone, round(foulard * 8) / 8)
        if cle not in self.cache:
            if len(self.cache) > 220:
                self.cache.clear()
            self.cache[cle] = personnage(qui, cle[1], yeux, bras, telephone, cle[5])
        return self.cache[cle]

    def clignement(self, t, decal=0.0):
        return "fermes" if (t + decal) % 3.1 < 0.12 else "ouverts"

    def poser_bulle(self, img, txt, x, y, t, t0, queue="gauche", fond=WHITE, couleur=INK, taille=50):
        if t < t0:
            return
        b = bulle(txt, fond=fond, couleur=couleur, taille=taille, queue=queue)
        p = vif(t - t0)
        coller_centre(img, b, x, y + 30 * (1 - min(p, 1)), 0.6 + 0.4 * min(p, 1.04), 0, clamp((t - t0) / 0.12))

    # ------------------------------------------------------------ 1. la demande
    def demande(self, t):
        img = self.salon.copy()
        b = self.bouche("demande", t)
        coller_centre(img, self.perso("koffi", 0, self.clignement(t, 1), ("bas", "bas")), 790, 1290, 0.86)
        coller_centre(img, self.perso("aya", b, self.clignement(t), ("bas", "tendu"), True), 330, 1250 + 6 * math.sin(t * 3), 0.92)
        self.poser_bulle(img, "Koffi !", 330, 420, t, 0.2, taille=70)
        self.poser_bulle(img, "Trouve-moi ma photo du mariage là !", 560, 650, t, 1.1)
        return camera(img, 1.04 + 0.04 * io(t / 4.5), 450, H / 2 + 60)

    # ------------------------------------------------------------ 2. Koffi fait defiler
    def defile(self, t):
        img = degrade_vertical((120, 180, 200), (60, 120, 150))
        b = self.bouche("defile", t)
        coller_centre(img, self.perso("koffi", b, self.clignement(t), ("bas", "bas")), 300, 1400, 0.8)
        defil = 1800 * expo(t / 3.0) + 200 * t
        ecran = self._ecran_chat(t, defil, int(800 * clamp(t / 2.2)))
        self.telephone_ecran(img, ecran, 720, 1000, 0.62, 6)
        texte(img, f"{int(800 * clamp(t / 2.2))} photos", 720, 260, 96, WHITE)
        self.poser_bulle(img, "Tantie, y a 800 photos dans le groupe dèh…", 470, 520, t, 0.4, queue="gauche", taille=46)
        return img

    # ------------------------------------------------------------ 3. le foulard rouge (la danse)
    def foulard(self, t):
        img = degrade_vertical((250, 200, 120), (240, 150, 90))
        img.alpha_composite(self.bokeh)
        b = self.bouche("foulard", t)
        balance = math.sin(t * 2 * math.pi * 1.0)
        bras = ("danse", "haut") if balance > 0 else ("haut", "danse")
        p = self.perso("aya", b, "joie" if t > 1.4 else "ouverts", bras, foulard=t)
        coller_centre(img, p, W / 2 + 60 * balance, 1250 - 30 * abs(balance), 1.0, 7 * balance)
        self.poser_bulle(img, "Je veux celle où je danse avec mon foulard rouge !", W / 2, 360, t, 0.3, taille=50)
        return camera(img, 1.0 + coups(t, [0.5 * k for k in range(8)], 0.02), W / 2, H / 2)

    # ------------------------------------------------------------ 4. MYFACE, le QR, le selfie
    def scan(self, t):
        img = self.salon.copy()
        b = self.bouche("scan", t)
        idee = 0.9                      # « MyFace. » : l'idee
        coller_centre(img, self.perso("aya", 0, self.clignement(t, 0.5), ("hanche", "bas")), 300, 1280, 0.86)
        coller_centre(img, self.perso("koffi", b, self.clignement(t, 2), ("bas", "tendu"), True), 790, 1290, 0.86)
        if t >= idee:
            p = lourd(t - idee)
            coller_centre(img, self.logo_clair, 760, 470 - 10 * math.sin(t * 2), 0.5 * min(p, 1.03))
        self.poser_bulle(img, "Attends…", 690, 300, t, 0.1, queue="droite", taille=56) if t < idee else None
        # le telephone de Koffi en grand : le QR, puis le selfie de la tantie
        etapes = [(2.6, "QR"), (4.4, "selfie")]
        if t >= 2.6:
            e = vif(t - 2.6)
            ecran = Image.new("RGBA", (EW, EH), (24, 24, 26, 255))
            if t < 4.4:
                from film_s1 import URL_DEMO
                import segno
                import io as _io
                if not hasattr(self, "_qr"):
                    buf = _io.BytesIO()
                    segno.make(URL_DEMO, error="m").save(buf, kind="png", scale=12, border=2)
                    self._qr = Image.open(buf).convert("RGBA").resize((420, 420), Image.NEAREST)
                coller_centre(ecran, self._qr, EW / 2, EH / 2 - 60)
                coller_centre(ecran, self.coins, EW / 2, EH / 2 - 60, 0.48 * (1 + 0.04 * math.sin(t * 9)))
                pilule(ecran, "On scanne le QR code…", EW / 2, EH - 260, 30, WHITE, INK, t, 2.8)
            else:
                ecran = Image.new("RGBA", (EW, EH), (250, 200, 140, 255))
                coller_centre(ecran, self.perso("aya", 0.2, "joie", ("bas", "bas")), EW / 2, EH / 2 + 380, 0.95)
                d = ImageDraw.Draw(ecran)
                d.ellipse([EW / 2 - 70, EH - 230, EW / 2 + 70, EH - 90], outline=WHITE, width=10)
                pilule(ecran, "Un selfie…", EW / 2, 160, 34, INK, WHITE, t, 4.5)
            self.telephone_ecran(img, ecran, W / 2, 1080 + (1 - min(e, 1)) * 1200, 0.78)
            if t >= 5.8:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * clamp(1 - (t - 5.8) / 0.3)))))
                mots_montants(img, "Voilà !", W / 2, 1760, 130, ORANGE, t, 5.85)
        return img

    # ------------------------------------------------------------ 5. toutes ses photos (la musique tombe)
    def resultats(self, t):
        img = degrade_vertical((250, 150, 80), ORANGE)
        b = self.bouche("resultats", t)
        saut = abs(math.sin(t * math.pi * 2)) * 50 if t < 2.0 else 0
        coller_centre(img, self.perso("aya", b, "joie", ("haut", "haut")), W / 2, 1580 - saut, 0.74)
        for i, pl in enumerate(self.polas):
            r_, c_ = divmod(i, 3)
            x, y = W / 2 + (c_ - 1) * 320, 250 + r_ * 300
            p = lourd(t - 0.1 - i * 0.06)
            coller_centre(img, pl["img"], mix_(W / 2, x, p), mix_(1300, y, p), 0.3 + 0.62 * min(p, 1.04), pl["a"] * p)
        pilule(img, "Retrouvées par l'IA", W / 2, 1060, 44, INK, WHITE, t, 0.9)
        self.poser_bulle(img, "Ehhh ! Toutes mes photos !", W / 2, 1230, t, 0.3, fond=INK, couleur=WHITE, taille=50) if t < 1.9 else None
        if t >= 2.0:
            self.poser_bulle(img, "Même celle-là où je ferme les yeux…", W / 2, 1230, t, 2.0, fond=INK, couleur=WHITE, taille=46)
            i = self.idx_fermes
            r_, c_ = divmod(i, 3)
            d = ImageDraw.Draw(img)
            x, y = W / 2 + (c_ - 1) * 320, 250 + r_ * 300
            q = vif(t - 2.3)
            if q > 0:
                rr = 200 * min(q, 1.05)
                d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=WHITE, width=10)
        # confettis de la musique qui tombe
        d = ImageDraw.Draw(img)
        for c in self.confettis:
            v = t - c["d"]
            if 0 < v < 2.2:
                x = W / 2 + c["vx"] * v
                y = 700 + c["vy"] * v + 1300 * v * v
                a = math.radians(c["rot"] * v)
                dx, dy = c["w"] / 2 * math.cos(a), c["w"] / 2 * math.sin(a)
                d.line([(x - dx, y - dy), (x + dx, y + dy)], fill=c["col"], width=c["h"])
        return img

    # ------------------------------------------------------------ 6. « celle-là, on va la laisser »
    def laisser(self, t):
        img = self.salon.copy()
        b = self.bouche("laisser", t)
        coller_centre(img, self.perso("aya", 0, "ouverts", ("hanche", "hanche")), 300, 1280, 0.86)
        coller_centre(img, self.perso("koffi", b, self.clignement(t), ("bas", "tendu")), 790, 1290, 0.86)
        pl = self.polas[self.idx_fermes]
        geste = 1.9
        if t < geste:
            coller_centre(img, pl["img"], W / 2, 640 + 8 * math.sin(t * 3), 1.2, -4)
        else:
            u = t - geste
            coller_centre(img, pl["img"], W / 2 + 1500 * o5(u / 0.6), 640 - 500 * u + 900 * u * u, 1.2 - 0.4 * u, -4 - 400 * u,
                          clamp(1 - u / 0.8))
        self.poser_bulle(img, "Tantie, celle-là, on va la laisser.", 640, 260, t, 0.2, queue="droite", taille=48)
        return img

    # ------------------------------------------------------------ 7. la signature
    def fin(self, t):
        img = self.fond_sable_pagne.copy()
        img.alpha_composite(Image.new("RGBA", (W, H), (244, 239, 230, 170)))
        coller_centre(img, self.logo_clair, W / 2, 420 - 6 * math.sin(t * 1.3), 0.8 * min(lourd(t - 0.25), 1.03))
        mots_montants(img, "Un selfie, et l'IA\nretrouve toutes\ntes photos.", W / 2, 860, 82, INK, t, 1.9, accent=["IA", "photos."])
        coller_centre(img, self.perso("aya", 0.0, "joie", ("haut", "bas") if math.sin(t * 4) > 0 else ("bas", "haut")), 240, 1560 - 14 * abs(math.sin(t * 4)), 0.42, 4 * math.sin(t * 4))
        coller_centre(img, self.perso("koffi", 0.0, self.clignement(t), ("bas", "haut") if math.sin(t * 4 + 1.5) > 0 else ("haut", "bas")), 860, 1570 - 14 * abs(math.sin(t * 4 + 1.5)), 0.42, -4 * math.sin(t * 4 + 1.5))
        tampon = 5.3                      # « Y a pas drap. » : le coup de tampon
        if t >= tampon:
            q = lourd(t - tampon)
            f = police(F_DISPLAY, 96)
            txt = "Y A PAS DRAP."
            bb = f.getbbox(txt)
            tp = Image.new("RGBA", (bb[2] - bb[0] + 90, bb[3] - bb[1] + 80), (0, 0, 0, 0))
            d = ImageDraw.Draw(tp)
            d.rounded_rectangle([6, 6, tp.width - 6, tp.height - 6], radius=24, outline=(*ORANGE, 255), width=10)
            d.text((45 - bb[0], 40 - bb[1]), txt, font=f, fill=(*ORANGE, 255))
            coller_centre(img, tp, W / 2, 1280, 2.2 - 1.2 * min(q, 1.02), -8, clamp((t - tampon) / 0.06))
        z = 1.0 + 0.03 * io(t / 6) + coups(t, [tampon + 0.08], 0.03, 0.1)
        return camera(img, z, W / 2, H / 2)


def sons(a):
    out = [("pop", a("demande", 0.2), 0.25), ("pop", a("demande", 1.1), 0.2)]
    out += [("envolee", a("defile", 0.0), 0.3), ("pop", a("defile", 0.4), 0.2)]
    t, pas = a("defile", 0.3), 0.3
    while t < a("defile", 3.2):
        out.append(("notif", t, 0.1, 0.3))
        t += pas
        pas = max(0.08, pas * 0.85)
    out += [("envolee", a("foulard", 0.0), 0.3), ("pop", a("foulard", 0.3), 0.2)]
    out += [("scintille", a("scan", 0.9), 0.35), ("envolee", a("scan", 2.6), 0.25), ("bip", a("scan", 3.6), 0.3),
            ("pop", a("scan", 4.4), 0.25), ("declencheur", a("scan", 5.8), 0.5)]
    out += [("pop", a("resultats", 0.1 + i * 0.06), 0.12, (i % 3 - 1) * 0.5) for i in range(9)]
    out += [("scintille", a("resultats", 0.2), 0.3), ("pop", a("resultats", 0.9), 0.2), ("coup", a("resultats", 2.3), 0.3)]
    out += [("froissement", a("laisser", 1.9), 0.4), ("envolee", a("laisser", 1.95), 0.3)]
    out += [("envolee", a("fin", 0.0), 0.25), ("scintille", a("fin", 0.3), 0.3), ("impact", a("fin", 5.3), 0.5)]
    return out


if __name__ == "__main__":
    principal(FilmS2)
