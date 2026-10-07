# -*- coding: utf-8 -*-
"""Motion design MYFACE, version 2 (50 s) : d'abord les problemes, puis les
reponses de MYFACE. Reprend les scenes de la version 1 (motion-design/
rendre_film.py, inchange) et ajoute :
- le tas de tirages fouille a deux mains ;
- le groupe de discussion qui deborde de photos floues ;
- la recherche qui echoue dans le mur de photos ;
- l'avant / apres sur la qualite d'origine.

    python motion-design/v2/rendre_film_v2.py   -> motion-design/v2/myface-motion-design-v2.mp4 (muet)
"""

import io
import math
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
from rendre_film import (DET, F_BOLD, F_DISPLAY, FPS, GREEN, H, INK, ORANGE, SAND, WHITE, W,  # noqa: E402
                         Film, charger, clamp, coller, coller_centre, doux, entree_cubique, etiquette,
                         police, ressort, sortie_cubique, texte, transformer)

SORTIE = ICI / "myface-motion-design-v2.mp4"
DEMO = ICI.parent.parent / "watched-photos" / "6b3391d9-e2eb-4942-990b-ac1353cd170e"
COUPLE = DEMO / "pexels-joshua-j-lewis-1577020288-27333351.jpg"
EX, EY, EW, EH = 220, 221, 640, 1478  # ecran du telephone dans l'image


def photos_demo(taille):
    out = []
    for p in sorted(DEMO.glob("*.jpg")):
        im = Image.open(p)
        im.draft("RGB", (taille, taille))
        out.append(im.convert("RGB"))
    return out


def degrader(im, facteur=6, qualite=9, flou=1.2):
    """L'image telle qu'elle arrive dans un groupe : reduite, recompressee, floue."""
    w, h = im.size
    petit = im.resize((max(8, w // facteur), max(8, h // facteur)), Image.BILINEAR)
    buf = io.BytesIO()
    petit.save(buf, "JPEG", quality=qualite)
    petit = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    out = petit.resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(flou))
    return ImageEnhance.Color(out).enhance(0.8)


class FilmV2(Film):
    def __init__(self):
        super().__init__()
        rng = random.Random(11)
        sources = photos_demo(700)
        self.cadre_tel = charger(DET / "telephone-cadre.png")
        # -- les tirages du tas
        self.tirages_tas = []
        for k in range(24):
            ph = sources[k % len(sources)]
            portrait = ph.height >= ph.width
            pw, phh = (250, 330) if portrait else (330, 250)
            photo = ImageOps.fit(ph, (pw, phh), Image.LANCZOS)
            b = 14
            carte = Image.new("RGBA", (pw + 2 * b, phh + 2 * b + 18), (250, 247, 242, 255))
            carte.paste(photo, (b, b))
            self.tirages_tas.append({
                "img": carte,
                "x": rng.uniform(150, 930), "y": rng.uniform(560, 1650),
                "a": rng.uniform(-32, 32), "t0": 0.05 + k * 0.05 + rng.uniform(0, 0.12),
                "dx": rng.uniform(-1, 1), "dy": rng.uniform(-1, 1),
            })
        self.ombre_carte = {}
        self.table = self._table()
        # -- le groupe de discussion
        self.chat_corps = self._chat_corps(sources, rng)
        # -- l'avant / apres
        cp = Image.open(COUPLE)
        cp.draft("RGB", (1400, 2100))
        cp = ImageOps.fit(cp.convert("RGB"), (W, H), Image.LANCZOS, centering=(0.5, 0.42))
        self.net = cp.convert("RGBA")
        self.flou = degrader(cp, facteur=9, qualite=8, flou=2.0).convert("RGBA")

    # ------------------------------------------------------------- decors
    def _table(self):
        rng = random.Random(4)
        a = np.zeros((H + 60, W + 60, 3), np.float32)
        y = np.linspace(0, 1, H + 60)[:, None]
        base = np.array([66, 45, 31], np.float32) * (1 - 0.35 * y) + np.array([40, 27, 19], np.float32) * (0.35 * y)
        a[:] = base[:, None, :] if base.ndim == 2 else base
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        for _ in range(260):
            yy = rng.uniform(0, H + 60)
            c = rng.randint(-14, 14)
            col = (66 + c, 45 + c, 31 + c)
            d.line([(0, yy), (W + 60, yy + rng.uniform(-30, 30))], fill=col, width=rng.randint(1, 4))
        img = img.filter(ImageFilter.GaussianBlur(1.4))
        # vignette
        vx = np.linspace(-1, 1, W + 60)[None, :]
        vy = np.linspace(-1, 1, H + 60)[:, None]
        v = np.clip(1 - 0.55 * (vx ** 2 + vy ** 2), 0.25, 1)
        arr = np.asarray(img).astype(np.float32) * v[..., None]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")

    def _chat_corps(self, sources, rng):
        """Le fil du groupe, tres haut, qu'on fait defiler."""
        noms = [("Tantie Aya", (196, 76, 54)), ("Koffi", (40, 116, 160)), ("Mariam", (130, 70, 160)),
                ("Ibrahim", (20, 136, 90)), ("Cousin Serge", (190, 120, 20)), ("Awa", (176, 60, 110))]
        textes = ["Envoyez les photos en HD svp", "Moi je me vois nulle part dèh", "C'est flou ooh",
                  "Qui a celle avec la tantie ?", "Ça c'est pas moi hein", "Il manque les photos de la dot",
                  "Quelqu'un m'a vu ?", "Envoyez encore"]
        f_nom, f_txt, f_h = police(F_BOLD, 22), police("C:/Windows/Fonts/segoeui.ttf", 25), police("C:/Windows/Fonts/segoeui.ttf", 18)
        blocs = []
        for k in range(26):
            nom, col = noms[k % len(noms)]
            if k % 3 == 2:
                blocs.append(("texte", nom, col, textes[k % len(textes)]))
            else:
                n = rng.choice([1, 2, 4, 4])
                imgs = [degrader(ImageOps.fit(rng.choice(sources), (220, 220) if n > 1 else (440, 330)),
                                 facteur=rng.choice([5, 7, 9]), qualite=rng.choice([6, 9, 12]),
                                 flou=rng.choice([0.8, 1.6, 2.4])) for _ in range(n)]
                blocs.append(("photos", nom, col, imgs))
        hauteur = 40
        rendus = []
        for b in blocs:
            if b[0] == "texte":
                h = 110
            else:
                h = 70 + (330 if len(b[3]) == 1 else (220 if len(b[3]) == 2 else 450)) + 34
            rendus.append((b, hauteur, h))
            hauteur += h + 22
        img = Image.new("RGB", (EW, hauteur + 40), (233, 225, 212))
        d = ImageDraw.Draw(img)
        for yy in range(0, hauteur + 40, 46):
            for xx in range(0, EW, 46):
                d.ellipse([xx + 20, yy + 20, xx + 24, yy + 24], fill=(222, 212, 197))
        for (b, y, h) in rendus:
            gauche = 18
            if b[0] == "texte":
                w = int(min(520, d.textlength(b[3], font=f_txt) + 60))
                d.rounded_rectangle([gauche, y, gauche + w, y + h], radius=20, fill=(255, 255, 255))
                d.text((gauche + 20, y + 12), b[1], font=f_nom, fill=b[2])
                d.text((gauche + 20, y + 46), b[3], font=f_txt, fill=(30, 40, 44))
            else:
                w = 476
                d.rounded_rectangle([gauche, y, gauche + w, y + h], radius=20, fill=(255, 255, 255))
                d.text((gauche + 18, y + 12), b[1], font=f_nom, fill=b[2])
                imgs = b[3]
                if len(imgs) == 1:
                    img.paste(imgs[0], (gauche + 18, y + 52))
                else:
                    for i, im in enumerate(imgs):
                        img.paste(im, (gauche + 18 + (i % 2) * 222, y + 52 + (i // 2) * 222))
                    if len(imgs) == 4:
                        x0, y0 = gauche + 18 + 222, y + 52 + 222
                        voile = Image.new("RGBA", (220, 220), (0, 0, 0, 120))
                        img.paste(voile, (x0, y0), voile)
                        f_plus = police(F_DISPLAY, 46)
                        d.text((x0 + 110, y0 + 110), f"+{rng.randint(8, 40)}", font=f_plus, fill=WHITE, anchor="mm")
            d.text((gauche + w - 70, y + h - 30), f"21:{rng.randint(10, 59)}", font=f_h, fill=(140, 150, 152))
        return img.convert("RGBA")

    def _ecran_chat(self, t, defil, compteur):
        ecran = Image.new("RGBA", (EW, EH), (233, 225, 212, 255))
        coller(ecran, self.chat_corps, 0, 210 - defil)
        d = ImageDraw.Draw(ecran)
        # barre d'etat + entete du groupe
        d.rectangle([0, 0, EW, 210], fill=(22, 52, 58))
        d.text((44, 26), "21:47", font=police(F_BOLD, 24), fill=WHITE)
        d.text((40, 118), "‹", font=police(F_BOLD, 52), fill=WHITE, anchor="lm")
        d.ellipse([84, 92, 148, 156], fill=ORANGE)
        d.text((116, 124), "AK", font=police(F_BOLD, 24), fill=WHITE, anchor="mm")
        d.text((166, 92), "Mariage Awa & Koffi", font=police(F_BOLD, 28), fill=WHITE)
        d.text((166, 128), "312 participants", font=police("C:/Windows/Fonts/segoeui.ttf", 22), fill=(190, 210, 212))
        # barre de saisie
        d.rectangle([0, EH - 120, EW, EH], fill=(233, 225, 212))
        d.rounded_rectangle([20, EH - 104, EW - 110, EH - 40], radius=32, fill=WHITE)
        d.text((52, EH - 72), "Message", font=police("C:/Windows/Fonts/segoeui.ttf", 26), fill=(150, 158, 160), anchor="lm")
        d.ellipse([EW - 94, EH - 104, EW - 30, EH - 40], fill=(22, 52, 58))
        # badge des nouvelles photos
        txt = f"{compteur} nouvelles photos"
        f = police(F_BOLD, 26)
        w = d.textlength(txt, font=f) + 60
        x0 = (EW - w) / 2
        d.rounded_rectangle([x0, EH - 200, x0 + w, EH - 140], radius=30, fill=ORANGE)
        d.text((EW / 2, EH - 170), txt, font=f, fill=WHITE, anchor="mm")
        return ecran

    @staticmethod
    def degrade_haut(img, hauteur=560, alpha=210):
        g = Image.new("L", (1, hauteur))
        for y in range(hauteur):
            g.putpixel((0, y), int(alpha * (1 - y / hauteur) ** 1.6))
        voile = Image.new("RGBA", (W, hauteur), (*INK, 255))
        voile.putalpha(g.resize((W, hauteur)))
        img.alpha_composite(voile, (0, 0))

    # ------------------------------------------------------------- scenes
    def probleme_tas(self, t):
        sx = 5 * math.sin(t * 37) * clamp((t - 1.4) / 0.3)
        sy = 4 * math.sin(t * 29 + 1) * clamp((t - 1.4) / 0.3)
        img = Image.new("RGBA", (W, H))
        coller(img, self.table, -30 + sx, -30 + sy)
        # deux mains qui fouillent
        mains = []
        for cote, debut, cx, cy, ph in (("droite", 1.35, 640, 1180, 0.0), ("gauche", 1.65, 400, 1000, 1.7)):
            if t >= debut:
                e = sortie_cubique((t - debut) / 0.45)
                bx = cx + 160 * math.sin((t - debut) * 5.2 + ph)
                by = cy + 110 * math.sin((t - debut) * 7.6 + ph)
                im, ombre, pt, (dxs, dys) = self.main.versions[cote]
                fx, fy = bx + dxs * 900 * (1 - e), by + dys * 900 * (1 - e)
                mains.append((cote, fx, fy))
        for c in self.tirages_tas:
            if t < c["t0"]:
                continue
            u = (t - c["t0"]) / 0.55
            p = ressort(u)
            x, y = c["x"], -400 + (c["y"] + 400) * p
            a = c["a"] * (0.4 + 0.6 * clamp(u))
            for _, fx, fy in mains:
                dx, dy = x - fx, y - fy
                dist = math.hypot(dx, dy) + 1e-3
                if dist < 300:
                    pousse = (300 - dist) * 0.55
                    x += dx / dist * pousse
                    y += dy / dist * pousse
                    a += (300 - dist) * 0.06 * (1 if c["dx"] > 0 else -1)
            carte = transformer(c["img"], 1.0, a)
            ombre = Image.new("RGBA", carte.size, (0, 0, 0, 0))
            ombre.putalpha(carte.split()[3].point(lambda v: int(v * 0.45)))
            coller(img, ombre.filter(ImageFilter.GaussianBlur(9)), x - carte.width / 2 + 10 + sx, y - carte.height / 2 + 16 + sy)
            coller(img, carte, x - carte.width / 2 + sx, y - carte.height / 2 + sy)
        for cote, fx, fy in mains:
            im, ombre, pt, _ = self.main.versions[cote]
            coller(img, ombre, fx - pt[0] + 22 + sx, fy - pt[1] + 34 + sy)
            coller(img, im, fx - pt[0] + sx, fy - pt[1] + sy)
        img = ImageEnhance.Color(img.convert("RGB")).enhance(0.55).convert("RGBA")
        self.degrade_haut(img)
        if t >= 0.25:
            texte(img, "Des centaines de photos...", W / 2, 170, 66, WHITE, opacite=clamp((t - 0.25) / 0.25))
        if t >= 1.9:
            p = ressort((t - 1.9) / 0.35)
            texte(img, "...et tout le monde fouille.", W / 2, 270, 66, ORANGE, echelle=1.25 - 0.25 * p, opacite=clamp((t - 1.9) / 0.15))
        return img

    def probleme_groupe(self, t):
        img = self.fond()
        defil = 3600 * entree_cubique(t / 3.6) + 40 * t
        compteur = int(12 + 335 * clamp(t / 3.2) ** 1.5)
        ecran = self._ecran_chat(t, defil, compteur)
        flotte = 8 * math.sin(t * 2.4)
        entree = sortie_cubique(t / 0.5)
        calque = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        calque.alpha_composite(ecran, (EX, EY))
        calque.alpha_composite(self.cadre_tel)
        coller_centre(img, calque, W / 2, H / 2 + flotte + (1 - entree) * 400, 0.94 + 0.06 * entree, -6 * (1 - entree))
        mots = [("Floues.", 0.9), ("Compressées.", 1.55), ("Perdues.", 2.2)]
        f = police(F_DISPLAY, 46)
        largeurs = [f.getlength(m) for m, _ in mots]
        ecart = 44
        x = (W - sum(largeurs) - ecart * 2) / 2
        for (mot, t0), lg in zip(mots, largeurs):
            if t >= t0:
                p = ressort((t - t0) / 0.3)
                texte(img, mot, x + lg / 2, 112, 46, ORANGE if mot == "Perdues." else WHITE, echelle=1.3 - 0.3 * p, opacite=clamp((t - t0) / 0.12))
            x += lg + ecart
        if t >= 2.7:
            etiquette(img, "Dans le groupe du mariage", W / 2, 1830, 44, WHITE, t, 2.7)
        return img

    def probleme_perdu(self, t):
        img = self.fond()
        decal = -int(1400 + 900 * sortie_cubique(t / 1.8))
        coller(img, self.mur, 0, decal)
        img.alpha_composite(Image.new("RGBA", (W, H), (*INK, 150)))
        arrets = [(330, 760), (760, 1180), (420, 1420), (700, 640)]
        k = min(int(t / 0.42), len(arrets) - 1)
        (x0, y0), (x1, y1) = arrets[max(0, k - 1)], arrets[k]
        u = doux((t - k * 0.42) / 0.25) if k > 0 else 1
        cx, cy = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        if t < 2.2:
            secoue = 14 * math.sin(t * 60) * clamp((t - 1.65) / 0.1) if t > 1.65 else 0
            coller_centre(img, self.coins, cx + secoue, cy, 0.42, 0, 1 - clamp((t - 1.95) / 0.25))
        if t >= 0.1:
            texte(img, "2 347 photos.", W / 2, 230, 86, WHITE, opacite=clamp((t - 0.1) / 0.2))
        if t >= 1.25:
            p = ressort((t - 1.25) / 0.35)
            texte(img, "Et toi, t'es où ?", W / 2, H / 2 + 520, 92, ORANGE, echelle=1.3 - 0.3 * p, opacite=clamp((t - 1.25) / 0.15))
        if t > 2.55:
            img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * clamp((t - 2.55) / 0.45)))))
        return img

    def qualite(self, t):
        z = 1 + 0.05 * t / 4
        img = Image.new("RGBA", (W, H))
        coller_centre(img, self.flou, W / 2, H / 2, z)
        split = W * doux((t - 0.45) / 1.5)
        if split > 0:
            net = transformer(self.net, z)
            ox, oy = (net.width - W) / 2, (net.height - H) / 2
            morceau = net.crop((int(ox), int(oy), int(ox + split), int(oy + H)))
            img.alpha_composite(morceau, (0, 0))
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
        etiquette(img, "Qualité d'origine, le soir même", W / 2, 1700, 44, WHITE, t, 2.1)
        etiquette(img, "Photos offertes ? Gratuit pour tous", W / 2, 1810, 44, ORANGE, t, 2.8)
        return img

    def scenes(self):
        return [
            (4.0, self.probleme_tas), (4.0, self.probleme_groupe), (3.0, self.probleme_perdu),
            (2.0, self.logo), (0.5, self.titre("Scanne.")), (3.0, self.accueil),
            (0.5, self.titre("Retrouve.")), (3.0, self.galerie), (4.5, self.visages), (5.0, self.selfie),
            (0.5, self.titre("Repars avec.")), (4.0, self.panier), (2.0, self.borne_monte),
            (4.0, self.borne_gros_plan), (2.0, self.tirage_sort), (4.0, self.qualite), (4.0, self.fin),
        ]


def main(apercu=None):
    film = FilmV2()
    scenes = film.scenes()
    if apercu:
        # quelques images de controle : [(indice de scene, temps), ...]
        return [scenes[i][1](t) for i, t in apercu]
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
    main()
