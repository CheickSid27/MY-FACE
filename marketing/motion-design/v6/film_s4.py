# -*- coding: utf-8 -*-
"""S4 « Organisateurs » (35 s, vouvoiement). Voir v6/STORYBOARD.md.

Message : vos invites repartent avec leurs photos, sans que vous ayez a vous en occuper ;
ton rassurant et chaleureux. Trois arguments reels de l'appli : le QR code et l'IA, les
photos offertes par l'organisateur (aucune page de paiement), la borne qui imprime.
Visages : vraies boites trouvees par l'IA sur l'evenement de demonstration.

    python marketing/motion-design/v6/film_s4.py [--images | --brouillon | --decoupage]
"""

import math

from PIL import Image, ImageDraw

from film_s1 import FilmS1, ombre_douce
from moteur_v6 import (EH, EW, F_BOLD, F_DISPLAY, GREEN, H, INK, ORANGE, WHITE, W, FilmV6, cam_cles, camera, clamp,
                       coller, coller_centre, coups, degrade_vertical, expo, io, lourd, mots_montants, o5, pilule,
                       police, principal, rond, texte, vif, voile)
from moteur_v6 import ELE, etiquette

GROUPE = "pexels-joshua-j-lewis-1577020288-27333356.jpg"      # 7 visages
CREME = (245, 241, 234)
BLEU = (40, 92, 140)


def mix_(a, b, p):
    return a + (b - a) * p


def icone(nom, taille=260, col=WHITE):
    """Icones plates dessinees : alliances, toque de diplome, verres."""
    s = 3
    L = taille * s
    im = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    e = 16 * s
    if nom == "mariage":
        d.ellipse([L * 0.12, L * 0.3, L * 0.6, L * 0.78], outline=col, width=e)
        d.ellipse([L * 0.4, L * 0.3, L * 0.88, L * 0.78], outline=col, width=e)
        d.polygon([(L * 0.36, L * 0.3), (L * 0.28, L * 0.18), (L * 0.36, L * 0.1), (L * 0.44, L * 0.18)], fill=col)
    elif nom == "diplomes":
        d.polygon([(L * 0.5, L * 0.18), (L * 0.95, L * 0.38), (L * 0.5, L * 0.58), (L * 0.05, L * 0.38)], fill=col)
        d.rounded_rectangle([L * 0.27, L * 0.46, L * 0.73, L * 0.72], radius=30 * s, fill=col)
        d.line([(L * 0.86, L * 0.42), (L * 0.86, L * 0.72)], fill=col, width=e // 2)
        d.ellipse([L * 0.82, L * 0.7, L * 0.9, L * 0.8], fill=col)
    else:
        for x0, a in ((0.22, -12), (0.56, 12)):
            v = Image.new("RGBA", (L, L), (0, 0, 0, 0))
            dv = ImageDraw.Draw(v)
            dv.polygon([(L * x0, L * 0.12), (L * (x0 + 0.26), L * 0.12), (L * (x0 + 0.2), L * 0.45), (L * (x0 + 0.06), L * 0.45)],
                       outline=col, width=e)
            dv.line([(L * (x0 + 0.13), L * 0.45), (L * (x0 + 0.13), L * 0.8)], fill=col, width=e)
            dv.line([(L * (x0 + 0.02), L * 0.82), (L * (x0 + 0.24), L * 0.82)], fill=col, width=e)
            im.alpha_composite(v.rotate(a, center=(L * (x0 + 0.13), L * 0.45), resample=Image.BICUBIC))
        for k in range(3):
            a = math.radians(-50 + k * 50)
            d.line([(L * 0.5 + L * 0.08 * math.sin(a), L * 0.1 - L * 0.04 * math.cos(a)),
                    (L * 0.5 + L * 0.16 * math.sin(a), L * 0.1 - L * 0.12 * math.cos(a))], fill=col, width=e // 2)
    return im.resize((taille, taille), Image.LANCZOS)


class FilmS4(FilmV6):
    NOM = "S4"
    VOIX = "S4-organisateurs"
    LIGNES = [
        ("types", 0.04, 4.24, 4.5, 0.2),
        ("plaintes", 5.26, 10.62, 5.5, 0.2),
        ("qr", 11.66, 16.38, 5.0, 0.2),
        ("ia", 16.76, 19.80, 3.5, 0.15),
        ("offertes", 20.68, 27.20, 7.0, 0.2),
        ("impression", 27.98, 30.44, 3.0, 0.2),
        ("fin", 31.30, 34.38, 3.5, 0.25),
    ]
    TRANSITIONS = {
        "plaintes": ("bandes", 0.5, {"n": 3}),
        "ia": ("iris", 0.45, {"cx": W / 2, "cy": 700}),
        "offertes": ("fouet", 0.4, {"sens": -1}),
        "fin": ("inondation", 0.6, {"cx": W / 2, "cy": 1300, "couleur": ORANGE}),
    }
    DROP = "qr"

    def __init__(self):
        super().__init__()
        self.icones = {n: icone(n) for n in ("mariage", "diplomes", "gala")}
        from film_s1 import URL_DEMO
        import io as _io
        import segno
        buf = _io.BytesIO()
        segno.make(URL_DEMO, error="m").save(buf, kind="png", scale=12, border=2, dark=(14, 36, 41), light="white")
        self.qr_img = Image.open(buf).convert("RGBA")
        self.chevalet = FilmS1._chevalet(self)
        self.groupe_img, _ = self.cadrer(GROUPE, W, H)
        ph = self.photo(GROUPE)
        e = max(W / ph.width, H / ph.height)
        x0, y0 = (ph.width * e - W) / 2, (ph.height * e - H) / 2
        self.boites = [((f["x1"] + f["x2"]) / 2 * e - x0, (f["y1"] + f["y2"]) / 2 * e - y0, (f["x2"] - f["x1"]) * e)
                       for f in self.visages[GROUPE]["visages"]]
        self.boites.sort(key=lambda b: b[0])
        # trois invites et leurs photos (personnes 0, 1 et 2 de la demo)
        self.invites = []
        for pers in (0, 1, 2):
            noms = self.photos_de(pers)[:6]
            ecran = Image.new("RGBA", (EW, EH), (*CREME, 255))
            d = ImageDraw.Draw(ecran)
            d.text((EW / 2, 120), f"{len(self.photos_de(pers))} photos", font=police(F_BOLD, 44), fill=INK, anchor="mm")
            for k, n in enumerate(noms):
                r_, c_ = divmod(k, 2)
                v = self.cadrer(n, 280, 280, pers, 110, (0.5, 0.45))[0]
                m = Image.new("L", v.size, 0)
                ImageDraw.Draw(m).rounded_rectangle([0, 0, 279, 279], radius=22, fill=255)
                ecran.paste(v, (30 + c_ * 300, 200 + r_ * 300), m)
            f0 = self.visage(noms[0], pers)
            vis = self.cadrer(noms[0], 200, 200, pers, 110, (0.5, 0.5))[0]
            self.invites.append({"ecran": ecran, "visage": rond(vis, 130, 6)})

    # ------------------------------------------------------------ 1. mariage, diplomes, gala
    def types(self, t):
        img = Image.new("RGBA", (W, H), (*INK, 255))
        mots_montants(img, "Vous organisez…", W / 2, H / 2, 96, WHITE, t, 0.0, sortie=0.75)
        cles = [("mariage", "Un mariage", 1.0, (176, 60, 70)), ("diplomes", "Une remise\nde diplômes", 2.3, BLEU),
                ("gala", "Un gala", 3.6, (190, 120, 30))]
        for i, (nom, mot, t0, col) in enumerate(cles):
            q = io((t - t0 + 0.6) / 0.5)
            if q <= 0:
                continue
            y0 = int(i * H / 3)
            band = Image.new("RGBA", (W, H // 3 + 1), (*col, 255))
            coller_centre(band, self.icones[nom], 260, H / 6, 0.9 + 0.1 * vif(t - t0 + 0.3))
            mots_montants(band, mot, 690, H / 6, 72, WHITE, t, t0 - 0.25)
            coller(img, band, (1 - q) * W * (1 if i % 2 == 0 else -1), y0)
        if t > 4.0:
            img.alpha_composite(Image.new("RGBA", (W, H), (*INK, int(150 * clamp((t - 4.0) / 0.4)))))
        return img

    # ------------------------------------------------------------ 2. « Et les photos ? »
    def plaintes(self, t):
        img = degrade_vertical((236, 230, 220), (220, 210, 196))
        msgs = [("Awa", "Et les photos ??", 0.4), ("Serge", "On les aura quand ?", 1.0), ("Mariam", "Toujours rien ?", 1.6),
                ("Ibrahim", "Et les photos du gala ?", 2.4), ("Tantie Aya", "Je me cherche encore dèh", 3.1),
                ("Koffi", "Allô ? Les photos ?", 3.8), ("Awa", "Bon…", 4.4)]
        cols = [(196, 76, 54), (190, 120, 20), (130, 70, 160), (20, 136, 90), (176, 60, 110), (40, 116, 160), (196, 76, 54)]
        y = 1720
        visibles = [m for m in msgs if t >= m[2]]
        for k, (nom, txt, t0) in enumerate(reversed(visibles)):
            p = vif(t - t0)
            f = police(F_BOLD, 40)
            w = int(f.getlength(txt)) + 170
            carte = Image.new("RGBA", (w, 140), (0, 0, 0, 0))
            d = ImageDraw.Draw(carte)
            d.rounded_rectangle([0, 0, w - 1, 139], radius=36, fill=WHITE)
            c = cols[msgs.index((nom, txt, t0))]
            d.ellipse([20, 30, 100, 110], fill=c)
            d.text((60, 70), nom[0], font=police(F_BOLD, 38), fill=WHITE, anchor="mm")
            d.text((120, 22), nom, font=police(F_BOLD, 26), fill=c)
            d.text((120, 60), txt, font=f, fill=INK)
            x = 90 + (k % 2) * 60
            coller(img, carte, x, y - 170 * k - 40 * (1 - min(p, 1)), clamp((t - t0) / 0.12))
        # le calendrier : les semaines passent
        sem = 1 + int(clamp((t - 2.6) / 2.4) * 3)
        if t >= 2.6:
            cal = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
            d = ImageDraw.Draw(cal)
            d.rounded_rectangle([0, 30, 299, 299], radius=30, fill=WHITE)
            d.rounded_rectangle([0, 30, 299, 110], radius=30, fill=ORANGE)
            d.rectangle([0, 80, 299, 110], fill=ORANGE)
            d.text((150, 70), "Semaine", font=police(F_BOLD, 34), fill=WHITE, anchor="mm")
            d.text((150, 205), str(sem), font=police(F_DISPLAY, 120), fill=INK, anchor="mm")
            coller_centre(img, cal, W - 220, 300, vif(t - 2.6) * (1 + coups(t, [2.6 + 0.8 * k for k in range(4)], 0.06, 0.08)), 6)
        mots_montants(img, "Et vous en entendez\nparler des semaines.", 400, 260, 56, INK, t, 2.7, accent=["semaines."])
        return img

    # ------------------------------------------------------------ 3. le QR code : chacun ses photos (la musique tombe)
    def qr(self, t):
        img = degrade_vertical((30, 56, 60), INK)
        img.alpha_composite(self.bokeh)
        c = (W / 2, 640)
        coller_centre(img, ombre_douce(self.chevalet), c[0] + 14, c[1] + 30, 0.8)
        coller_centre(img, self.chevalet, c[0], c[1], 0.8 * min(lourd(t), 1.02), -2 + math.sin(t))
        pos = [(200, 1430, -8), (W / 2, 1520, 0), (W - 200, 1430, 8)]
        for i, (x, y, a) in enumerate(pos):
            t0 = 1.3 + i * 0.45
            if t < t0:
                continue
            # le rayon du QR vers chaque telephone (une perle qui file)
            u = clamp((t - t0) / 0.5)
            d = ImageDraw.Draw(img)
            x0, y0 = c[0], c[1] + 260
            d.line([(x0, y0), (mix_(x0, x, u), mix_(y0, y - 300, u))], fill=(*ORANGE, 255), width=6)
            if u < 1:
                bx, by = mix_(x0, x, u), mix_(y0, y - 300, u)
                d.ellipse([bx - 14, by - 14, bx + 14, by + 14], fill=WHITE)
            p = vif(t - t0 - 0.35)
            if p > 0:
                inv = self.invites[i]
                self.telephone_ecran(img, inv["ecran"], x, y + (1 - min(p, 1)) * 500, 0.38, a)
                coller_centre(img, inv["visage"], x, y - 330, 0.9 * min(p, 1.04))
        pilule(img, "1 QR code. Chacun ses photos.", W / 2, 150, 48, ORANGE, WHITE, t, 0.3)
        return camera(img, 1.0 + coups(t, [0, 1.3, 1.75, 2.2], 0.012), W / 2, H / 2)

    # ------------------------------------------------------------ 4. l'IA de reconnaissance faciale
    def ia(self, t):
        img = self.groupe_img.copy()
        voile(img, INK, 0.25)
        for k, (x, y, c) in enumerate(self.boites):
            t0 = 0.3 + k * 0.18
            if t >= t0:
                p = vif(t - t0)
                coller_centre(img, self.coins, x, y, c * 1.4 / self.coins.width * (1.5 - 0.5 * min(p, 1)), 0,
                              clamp((t - t0) / 0.1))
        pilule(img, "IA de reconnaissance faciale", W / 2, 1640, 48, ORANGE, WHITE, t, 0.2)
        n = sum(1 for k in range(len(self.boites)) if t >= 0.3 + k * 0.18)
        if n:
            texte(img, f"{n} visage{'s' if n > 1 else ''}", W / 2, 1780, 64, WHITE)
        return camera(img, 1.06 - 0.06 * io(t / 3.5), W / 2, H / 2)

    # ------------------------------------------------------------ 5. offrez-les (photos offertes)
    def offertes(self, t):
        img = FilmV6.offertes(self, max(0.0, t - 0.3))
        mots_montants(img, "Envie de faire plaisir ?", W / 2, 640, 64, WHITE, t, 0.15, sortie=2.6)
        mots_montants(img, "Offrez-les.", W / 2, 1800, 96, WHITE, t, 1.75, accent=["Offrez-les."])
        return img

    # ------------------------------------------------------------ 6. la borne imprime
    def impression(self, t):
        img = self.tirage_sort(min(t * 0.75, 2.2))
        etiquette(img, "Impression sur place", W / 2, 150, 60, ORANGE, t, 0.3)
        return img

    # ------------------------------------------------------------ 7. WhatsApp
    def fin(self, t):
        img = degrade_vertical((30, 56, 60), INK)
        coller_centre(img, self.logo_fonce, W / 2, 520 + 6 * math.sin(t * 1.3), 0.82 * min(lourd(t - 0.05), 1.03))
        mots_montants(img, "Parlons de\nvotre événement.", W / 2, 900, 88, WHITE, t, 1.1, accent=["événement."])
        bouton = (W / 2, 1300)
        if t >= 1.6:
            p = vif(t - 1.6)
            b = Image.new("RGBA", (760, 150), (0, 0, 0, 0))
            d = ImageDraw.Draw(b)
            appui = 2.6
            col = (18, 150, 80) if t < appui else (10, 120, 60)
            d.rounded_rectangle([0, 0, 759, 149], radius=75, fill=col)
            d.ellipse([40, 35, 120, 115], outline=WHITE, width=8)
            d.polygon([(52, 112), (58, 92), (74, 104)], fill=WHITE)
            d.text((430, 75), "Discuter sur WhatsApp", font=police(F_BOLD, 44), fill=WHITE, anchor="mm")
            coller_centre(img, b, *bouton, (0.6 + 0.4 * min(p, 1.03)) * (0.97 if appui <= t < appui + 0.12 else 1.0))
            self.onde_a(img, bouton, t, appui)
            self.main.dessiner(img, (bouton[0] + 120, bouton[1]), t, appui, "droite")
        texte(img, "myfaceci.online", W / 2, 1640, 42, (200, 210, 212), chemin=F_BOLD, opacite=clamp((t - 2.0) / 0.3))
        return camera(img, 1.0 + 0.03 * io(t / 3.5), W / 2, H / 2)


def sons(a):
    out = [("envolee", a("types", t), 0.25) for t in (0.5, 1.8, 3.1)]
    out += [("coup", a("types", t), 0.3) for t in (1.0, 2.3, 3.6)]
    out += [("notif", a("plaintes", t), 0.2, 0.3) for t in (0.4, 1.0, 1.6, 2.4, 3.1, 3.8, 4.4)]
    out += [("papier", a("plaintes", 2.6 + 0.8 * k), 0.3) for k in range(4)]
    out += [("scintille", a("qr", 0.1), 0.3)] + [("bip", a("qr", 1.3 + i * 0.45), 0.25, (i - 1) * 0.5) for i in range(3)]
    out += [("pop", a("qr", 1.65 + i * 0.45), 0.2, (i - 1) * 0.5) for i in range(3)]
    out += [("balayage", a("ia", 0.2), 0.15, 0.0, 1.4)] + [("bip", a("ia", 0.3 + k * 0.18), 0.15) for k in range(7)]
    out += [("envolee", a("offertes", 0.0), 0.3), ("toucher", a("offertes", 1.25), 0.35), ("pop", a("offertes", 2.0), 0.25),
            ("toucher", a("offertes", 3.8), 0.35), ("scintille", a("offertes", 3.9), 0.4)]
    out += [("imprimante", a("impression", 0.1), 0.4), ("scintille", a("impression", 1.9), 0.3)]
    out += [("envolee", a("fin", 0.0), 0.25), ("pop", a("fin", 1.6), 0.25), ("toucher", a("fin", 2.6), 0.4)]
    return out


if __name__ == "__main__":
    principal(FilmS4)
