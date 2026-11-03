# -*- coding: utf-8 -*-
"""Moteur commun des films v6 (les six scenarios de scenarios/scenarios.md, format 9:16).

Reprend la chaine v4 / v5 (images PIL, vrais ecrans, main dessinee) et y ajoute ce que
recommandent les deux competences de motion design (howseen-ai/claude-motion-design et
tugrawork-creator/saas-motion-kit) :
- ressorts amortis en forme fermee (amortissement >= 0,72, jamais de rebond de dessin anime) ;
- une camera par scene (zoom interpole en logarithme) et de petits coups sur les temps ;
- le texte qui monte dans un masque, mot par mot (55 ms d'ecart) ;
- des transitions narratives (iris, inondation, coupe avec arret sur image, fouet, bandes,
  masque de texte, objet porte d'une scene a l'autre), jamais deux fois la meme de suite ;
- le flou de mouvement seulement sur les mouvements rapides (sous-images melangees, obturateur 180 degres) ;
- coupes calees sur la grille de 0,5 s (120 BPM), musique qui « tombe » sur le moment cle ;
- encodage x264 BT.709 en plage TV, image de controle avant tout rendu complet.

Chaque film (film_s1.py ... film_s6.py) declare ses scenes, ses lignes de voix et ses
transitions ; son_v6.py fabrique la bande son a partir du meme decoupage.
"""

import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

ICI = Path(__file__).resolve().parent
MD = ICI.parent
for p in (MD, MD / "v2", MD / "v4", MD / "v5", ICI):
    sys.path.insert(0, str(p))
from rendre_film import (ELE, F_BOLD, F_DISPLAY, FPS, GREEN, H, INK, ORANGE, SAND, WHITE, W,  # noqa: E402,F401
                         clamp, coller, coller_centre, doux, entree_cubique, etiquette, pastille, police,
                         ressort, sortie_cubique, texte, transformer)
from rendre_film_v4 import (EH, EW, F_TXT, FilmV4, barre_etat, carte_blanche, ombre_de, rond,  # noqa: E402,F401
                            vignette)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOIX = MD / "scenarios" / "voix"
CAPS = ICI / "captures"
DEMO = ICI.parents[2] / "watched-photos" / "6b3391d9-e2eb-4942-990b-ac1353cd170e"
SORTIES = ICI / "films"
TEMPS = 0.5                     # un temps a 120 BPM
PHOTO_MAX = 2200                # plus grand cote des photos de la demo une fois chargees
GRIS = (120, 128, 130)
CREME = (245, 241, 234)
ECH_CAP = EH / 2796
ROGNE = (1290 * ECH_CAP - EW) / 2


# --------------------------------------------------------------------------
# Courbes
# --------------------------------------------------------------------------
def ressort_k(t, k=170.0, d=26.0):
    """Reponse d'un ressort (masse 1, raideur k, frottement d) de 0 vers 1, t en secondes.
    Presets : interface 320/30, conteneurs 170/26, titres et logos 120/24."""
    if t <= 0:
        return 0.0
    w0 = math.sqrt(k)
    z = d / (2 * w0)
    if z < 1:
        wd = w0 * math.sqrt(1 - z * z)
        return 1 - math.exp(-z * w0 * t) * (math.cos(wd * t) + z * w0 / wd * math.sin(wd * t))
    if z == 1:
        return 1 - math.exp(-w0 * t) * (1 + w0 * t)
    r1 = -w0 * (z - math.sqrt(z * z - 1))
    r2 = -w0 * (z + math.sqrt(z * z - 1))
    return 1 - (r2 * math.exp(r1 * t) - r1 * math.exp(r2 * t)) / (r2 - r1)


def vif(t):
    return ressort_k(t, 320, 30)


def lourd(t):
    return ressort_k(t, 120, 24)


def io(x):
    """Cubique entree-sortie."""
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def expo(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def expo_in(x):
    x = clamp(x)
    return 0.0 if x <= 0 else 2 ** (10 * x - 10)


def o5(x):
    return 1 - (1 - clamp(x)) ** 5


def mix(a, b, p):
    return a + (b - a) * p


def couleur_mix(c1, c2, p):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * p) for i in range(3))


def coups(t, temps_forts, force=0.012, demi_vie=0.12):
    """Petit coup de zoom qui decroit apres chaque temps fort."""
    return sum(force * math.exp(-(t - b) / demi_vie) for b in temps_forts if 0 <= t - b < 1.2)


# --------------------------------------------------------------------------
# Camera : une transformation sur toute l'image
# --------------------------------------------------------------------------
def camera(img, zoom=1.0, cx=W / 2, cy=H / 2, angle=0.0):
    """Le point (cx, cy) de la scene vient au centre, grossi de zoom."""
    if abs(zoom - 1) < 1e-4 and abs(cx - W / 2) < 0.5 and abs(cy - H / 2) < 0.5 and not angle:
        return img
    a = math.radians(angle)
    c, s = math.cos(a) / zoom, math.sin(a) / zoom
    # image de sortie (x, y) -> scene (x', y')
    ox, oy = W / 2, H / 2
    coeffs = (c, s, cx - c * ox - s * oy, -s, c, cy + s * ox - c * oy)
    fond = img.getpixel((2, 2))
    return img.transform((W, H), Image.AFFINE, coeffs, resample=Image.BICUBIC, fillcolor=fond)


def cam_cles(t, cles):
    """cles [(t, zoom, x, y)] -> (zoom, x, y), zoom interpole en logarithme, segments adoucis."""
    if t <= cles[0][0]:
        return cles[0][1:]
    for (t0, z0, x0, y0), (t1, z1, x1, y1) in zip(cles, cles[1:]):
        if t0 <= t <= t1:
            p = io((t - t0) / (t1 - t0))
            return math.exp(mix(math.log(z0), math.log(z1), p)), mix(x0, x1, p), mix(y0, y1, p)
    return cles[-1][1:]


# --------------------------------------------------------------------------
# Texte
# --------------------------------------------------------------------------
def mots_montants(base, phrase, cx, cy, taille, couleur, t, t0, chemin=F_DISPLAY, accent=None,
                  couleur_accent=ORANGE, ecart=0.055, duree=0.5, sortie=None, interligne=1.12):
    """Chaque mot monte dans sa fente (masque), avec une petite rotation qui se redresse.
    phrase peut tenir sur plusieurs lignes (\\n). accent : mots en couleur d'accent.
    sortie : instant ou les mots redescendent et disparaissent."""
    if t < t0:
        return
    f = police(chemin, int(taille))
    lignes = phrase.split("\n")
    esp = f.getlength(" ")
    hl = taille * interligne
    k = 0
    for i, ligne in enumerate(lignes):
        mots = ligne.split(" ")
        larg = [f.getlength(m) for m in mots]
        x = cx - (sum(larg) + esp * (len(mots) - 1)) / 2
        y = cy + (i - (len(lignes) - 1) / 2) * hl
        for m, lg in zip(mots, larg):
            p = expo((t - t0 - k * ecart) / duree)
            if sortie is not None and t >= sortie:
                p = 1 - expo_in((t - sortie - k * 0.03) / 0.3)
            k += 1
            if p <= 0:
                x += lg + esp
                continue
            bb = f.getbbox(m)
            marge = int(taille * 0.25)
            hauteur = int(taille * 1.35)
            fente = Image.new("RGBA", (int(lg) + 2 * marge, hauteur), (0, 0, 0, 0))
            mot = Image.new("RGBA", fente.size, (0, 0, 0, 0))
            col = couleur_accent if accent and m.strip(",.!?:;«»") in accent else couleur
            ImageDraw.Draw(mot).text((marge, int(taille * 0.12)), m, font=f, fill=(*col, 255))
            if p < 1:
                mot = mot.rotate(5 * (1 - p), resample=Image.BICUBIC, center=(0, hauteur))
            # le mot monte depuis le bas de sa fente : ce qui depasse est coupe (le masque)
            fente.paste(mot, (0, int(hauteur * 1.05 * (1 - p))), mot)
            coller(base, fente, x - marge, y - hauteur / 2)
            x += lg + esp


def pilule(base, txt, cx, cy, taille, fond, couleur, t, t0, ouvrir=0.35, opacite=1.0):
    """Etiquette dont la pilule s'etire depuis le centre, puis le texte apparait."""
    if t < t0:
        return
    f = police(F_BOLD, int(taille))
    bb = f.getbbox(txt)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    m = int(taille * 0.7)
    w_plein, h = tw + 2 * m, th + int(taille * 1.1)
    p = vif(t - t0)
    w = max(h, int(w_plein * min(1.0, p)))
    im = Image.new("RGBA", (w_plein + 4, h + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0 = (w_plein - w) / 2 + 2
    d.rounded_rectangle([x0, 2, x0 + w, h + 2], radius=h // 2, fill=(*fond, 255))
    a = clamp((t - t0 - ouvrir * 0.6) / 0.2)
    if a > 0:
        d.text((2 + m - bb[0], 2 + (h - th) / 2 - bb[1]), txt, font=f, fill=(*couleur, int(255 * a)))
    coller_centre(base, im, cx, cy, 1.0, 0, opacite)


# --------------------------------------------------------------------------
# Transitions (p de 0 a 1) : a = image qui part, b = image qui arrive
# --------------------------------------------------------------------------
def rayon_couvrant(cx, cy):
    return 1.05 * max(math.hypot(cx - x, cy - y) for x in (0, W) for y in (0, H))


def masque_rond(cx, cy, r):
    m = Image.new("L", (W, H), 0)
    if r > 0:
        ImageDraw.Draw(m).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    return m


def t_iris(a, b, p, cx=W / 2, cy=H / 2):
    """Iris : b s'ouvre dans un cercle qui part d'un point precis (la cause)."""
    r = rayon_couvrant(cx, cy) * expo(p)
    out = a.copy()
    out.paste(b, (0, 0), masque_rond(cx, cy, r).filter(ImageFilter.GaussianBlur(2)))
    return out


def t_inondation(a, b, p, cx, cy, couleur=ORANGE):
    """La couleur deborde d'un objet jusqu'au coin le plus loin, puis se retire sur b."""
    if p < 0.5:
        q = expo(p / 0.5)
        out = a.copy()
        out.paste(Image.new("RGBA", (W, H), (*couleur, 255)), (0, 0), masque_rond(cx, cy, rayon_couvrant(cx, cy) * q))
        return out
    q = io((p - 0.5) / 0.5)
    out = b.copy()
    m = Image.new("L", (W, H), 255)
    r = rayon_couvrant(W / 2, H / 2) * q
    ImageDraw.Draw(m).ellipse([W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r], fill=0)
    out.paste(Image.new("RGBA", (W, H), (*couleur, 255)), (0, 0), m)
    return out


def t_fouet(a, b, p, sens=1):
    """Panoramique fouette : les deux images filent ensemble, floues dans le sens du mouvement."""
    q = io(p)
    dx = int(W * q) * sens
    out = Image.new("RGBA", (W, H), (*INK, 255))
    coller(out, a, -dx, 0)
    coller(out, b, W * sens - dx, 0)
    force = math.sin(math.pi * p)
    k = int(2 + 120 * force)
    if k > 2:
        arr = cv2.blur(np.asarray(out), (k, 1))
        out = Image.fromarray(arr)
    return out


def t_bandes(a, b, p, n=4, vertical=True):
    """Bandes decalees (split stack) : chaque bande de b glisse a son tour."""
    out = a.copy()
    for i in range(n):
        q = io((p - i * 0.08) / (1 - (n - 1) * 0.08))
        if q <= 0:
            continue
        if vertical:
            x0, x1 = int(i * W / n), int((i + 1) * W / n)
            dec = int((1 - q) * H) * (1 if i % 2 == 0 else -1)
            bande = b.crop((x0, 0, x1, H))
            coller(out, bande, x0, dec)
        else:
            y0, y1 = int(i * H / n), int((i + 1) * H / n)
            dec = int((1 - q) * W) * (1 if i % 2 == 0 else -1)
            coller(out, b.crop((0, y0, W, y1)), dec, y0)
    return out


def t_masque_texte(a, b, p, mot, taille=430):
    """b apparait a travers les lettres d'un mot qui grossit jusqu'a couvrir l'image."""
    f = police(F_DISPLAY, taille)
    bb = f.getbbox(mot)
    m = Image.new("L", (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), 0)
    ImageDraw.Draw(m).text((20 - bb[0], 20 - bb[1]), mot, font=f, fill=255)
    e = 0.6 * math.exp(math.log(30 / 0.6) * entree_cubique(p))
    # sortie (x, y) -> masque ((x - W/2) / e + mw/2, ...) : jamais d'image geante
    mw, mh = m.size
    plein = m.transform((W, H), Image.AFFINE, (1 / e, 0, mw / 2 - W / 2 / e, 0, 1 / e, mh / 2 - H / 2 / e),
                        resample=Image.BILINEAR, fillcolor=0)
    if p > 0.8:
        plein = Image.blend(plein, Image.new("L", (W, H), 255), (p - 0.8) / 0.2)
    out = a.copy()
    out.paste(b, (0, 0), plein)
    return out


def t_fondu(a, b, p):
    return Image.blend(a, b, io(p))


def t_poussee(a, b, p, sens=1):
    """Plongee a travers a (zoom) pendant que b arrive de petit a plein."""
    q = io(p)
    za = math.exp(math.log(3.2) * entree_cubique(p))
    out = camera(a, za)
    bb = camera(b, mix(0.6, 1.0, o5(p)))
    return Image.blend(out, bb, clamp((p - 0.25) / 0.45)) if q > 0 else out


TRANSITIONS = {"iris": t_iris, "inondation": t_inondation, "fouet": t_fouet, "bandes": t_bandes,
               "masque_texte": t_masque_texte, "fondu": t_fondu, "poussee": t_poussee}


# --------------------------------------------------------------------------
# Ecrans et petits elements
# --------------------------------------------------------------------------
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


def voile(img, couleur=INK, alpha=0.5):
    img.alpha_composite(Image.new("RGBA", (W, H), (*couleur, int(255 * clamp(alpha)))))


def degrade_vertical(haut, bas, h=H, w=W):
    g = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(haut)[None, None] * (1 - g) + np.array(bas)[None, None] * g).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, w, axis=1)).convert("RGBA")


def grain(img, t, force=7):
    """Grain de pellicule fixe par image (determinste : graine = numero d'image)."""
    rng = np.random.default_rng(int(t * FPS) + 7)
    n = rng.normal(0, force, (H // 2, W // 2)).astype(np.int16)
    n = cv2.resize(n.astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST)
    arr = np.asarray(img.convert("RGB")).astype(np.float32) + n[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


def flou_gaussien(img, r):
    return img.filter(ImageFilter.GaussianBlur(r)) if r > 0.3 else img


# --------------------------------------------------------------------------
# Decoupage : scenes sur la grille, voix posees au debut de chaque scene
# --------------------------------------------------------------------------
def demi(x):
    return math.ceil(x * 2 - 1e-6) / 2


def decoupage(lignes, avance=0.25, queue=0.35):
    """lignes [(scene, debut_voix, fin_voix, duree_min, avance)] (secondes dans le wav d'origine).
    -> scenes [(nom, debut, duree)], voix [(debut_dans_wav, fin_dans_wav, debut_dans_film)], total."""
    scenes, voix, t = [], [], 0.0
    for nom, a, b, base, av in lignes:
        av = avance if av is None else av
        d = max(base, demi(av + (b - a) + queue))
        scenes.append((nom, t, d))
        voix.append((a, b, t + av))
        t += d
    return scenes, voix, t


def lire_voix(nom):
    with wave.open(str(VOIX / f"{nom}.wav")) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768, w.getframerate()


# --------------------------------------------------------------------------
# Le film de base
# --------------------------------------------------------------------------
class FilmV6(FilmV4):
    NOM = "S0"
    VOIX = ""
    LIGNES = []           # voir decoupage()
    TRANSITIONS = {}      # scene qui arrive -> (nom, duree, parametres)
    RAPIDE = []           # [(debut, fin)] en temps du film : flou de mouvement
    DROP = None           # scene ou la musique tombe

    def __init__(self):
        super().__init__()
        self.scenes_, self.voix_, self.total = decoupage(self.LIGNES)
        self.debut = {n: d for n, d, _ in self.scenes_}
        self.duree = {n: du for n, _, du in self.scenes_}
        self.cap = {f.stem[:2]: ecran_capture(f) for f in CAPS.glob("0[0-6]-*.png")}
        self.visages = json.loads((ICI / "visages_demo.json").read_text(encoding="utf-8"))
        self._photos = {}
        # les photos sont gardees a 2 200 px au plus (largement assez pour une video 1080) :
        # les boites des visages sont mises a la meme echelle
        self._ech = {}
        for nom, v in self.visages.items():
            e = min(1.0, PHOTO_MAX / max(v["taille"]))
            self._ech[nom] = e
            for f in v["visages"]:
                for k in ("x1", "y1", "x2", "y2"):
                    f[k] *= e

    def verifier(self):
        """Un attribut qui porte le nom d'une scene la cache : on le signale tout de suite."""
        for nom, _, _ in self.scenes_:
            if not callable(getattr(self, nom)):
                raise TypeError(f"l'attribut self.{nom} cache la scene « {nom} »")

    # ---- photos de la demo et visages trouves par l'IA
    def photo(self, nom):
        if nom not in self._photos:
            im = ImageOps.exif_transpose(Image.open(DEMO / nom))
            e = self._ech.get(nom, min(1.0, PHOTO_MAX / max(im.size)))
            if e < 1:
                im = im.resize((round(im.width * e), round(im.height * e)), Image.LANCZOS)
            self._photos[nom] = im.convert("RGB")
        return self._photos[nom]

    def photos_de(self, personne):
        return [n for n, v in sorted(self.visages.items()) if any(f["personne"] == personne for f in v["visages"])]

    def visage(self, nom, personne):
        for f in self.visages[nom]["visages"]:
            if f["personne"] == personne:
                return f
        return None

    def cadrer(self, nom, w, h, personne=None, cote_visage=None, centre=(0.5, 0.42)):
        """Photo recadree en w x h. Avec une personne : son visage tombe sur centre (fractions)
        avec un cote de cote_visage pixels. -> (image RGBA, boite du visage dans l'image ou None)."""
        ph = self.photo(nom)
        f = self.visage(nom, personne) if personne is not None else None
        if f is None:
            return couvrir(ph, w, h), None
        fx, fy, fc = (f["x1"] + f["x2"]) / 2, (f["y1"] + f["y2"]) / 2, f["x2"] - f["x1"]
        e = max((cote_visage or fc) / fc, w / ph.width, h / ph.height)
        x0 = clamp(fx * e - centre[0] * w, 0, ph.width * e - w)
        y0 = clamp(fy * e - centre[1] * h, 0, ph.height * e - h)
        crop = ph.crop((x0 / e, y0 / e, (x0 + w) / e, (y0 + h) / e)).resize((w, h), Image.LANCZOS).convert("RGBA")
        boite = (fx * e - x0 - fc * e / 2, fy * e - y0 - fc * e / 2, fx * e - x0 + fc * e / 2, fy * e - y0 + fc * e / 2)
        return crop, boite

    # ---- utilitaires de scene
    def a(self, nom, t):
        """Temps du film d'un instant de scene."""
        return self.debut[nom] + t

    def toucher(self, img, x, y, cx, cy, echelle, t, t0, cote="droite"):
        pt = self.point_ecran(x, y, cx, cy, echelle)
        self.onde_a(img, pt, t, t0)
        self.main.dessiner(img, pt, t, t0, cote)
        return pt

    # ---- l'image a l'instant t du film
    def scene_en(self, t):
        for i, (nom, d, du) in enumerate(self.scenes_):
            if t < d + du or i == len(self.scenes_) - 1:
                return i, nom, t - d
        raise ValueError(t)

    def image(self, t):
        i, nom, u = self.scene_en(t)
        img = getattr(self, nom)(u)
        tr = self.TRANSITIONS.get(nom)
        if tr and i > 0:
            fn, dt, kw = tr[0], tr[1], (tr[2] if len(tr) > 2 else {})
            if u < dt:
                prec, dp, dup = self.scenes_[i - 1]
                a = getattr(self, prec)(dup + u)
                img = TRANSITIONS[fn](a.convert("RGBA"), img.convert("RGBA"), u / dt, **kw)
        return self.final(img, t)

    def final(self, img, t):
        return img

    def sous_images(self, t):
        for a, b in self.RAPIDE:
            if a <= t < b:
                return 5
        i, nom, u = self.scene_en(t)
        tr = self.TRANSITIONS.get(nom)
        if tr and tr[0] in ("fouet", "poussee") and u < tr[1]:
            return 5
        return 1

    def rendu(self, t):
        """Image finale RGB (avec flou de mouvement si le moment est rapide)."""
        n = self.sous_images(t)
        if n == 1:
            return np.asarray(self.image(t).convert("RGB"))
        acc = np.zeros((H, W, 3), np.float32)
        for k in range(n):
            acc += np.asarray(self.image(t + (k / n - 0.5) * 0.5 / FPS).convert("RGB"), np.float32)
        return (acc / n).astype(np.uint8)


# --------------------------------------------------------------------------
# Rendu, images de controle, planche
# --------------------------------------------------------------------------
def encodeur(chemin, w=W, h=H, fps=FPS, crf=17):
    cmd = [FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps),
           "-i", "-", "-vf", "scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p",
           "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-color_range", "tv",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", str(chemin)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def rendre(film, debut=0.0, fin=None, sortie=None, brouillon=False):
    fin = film.total if fin is None else fin
    SORTIES.mkdir(exist_ok=True)
    sortie = sortie or SORTIES / f"{film.NOM}-{'brouillon' if brouillon else 'muet'}.mp4"
    fps = 15 if brouillon else FPS
    w, h = (W // 2, H // 2) if brouillon else (W, H)
    enc = encodeur(sortie, w, h, fps, 23 if brouillon else 17)
    n0, n1 = int(round(debut * fps)), int(round(fin * fps))
    for k in range(n0, n1):
        t = k / fps
        arr = np.asarray(film.image(t).convert("RGB")) if brouillon else film.rendu(t)
        if brouillon:
            arr = cv2.resize(arr, (w, h), interpolation=cv2.INTER_AREA)
        enc.stdin.write(np.ascontiguousarray(arr).tobytes())
        if (k - n0) % (fps * 5) == 0:
            print(f"  {film.NOM} {t:5.1f} / {fin:.1f} s", flush=True)
    enc.stdin.close()
    enc.wait()
    print(f"{sortie}  {(n1 - n0) / fps:.1f} s")
    return sortie


def planche(film, temps, chemin, cols=4, largeur=270):
    """Images de controle reduites, avec l'instant ecrit dessous."""
    h = int(largeur * H / W)
    lignes = (len(temps) + cols - 1) // cols
    p = Image.new("RGB", (cols * (largeur + 8), lignes * (h + 30)), (20, 20, 20))
    d = ImageDraw.Draw(p)
    for i, t in enumerate(temps):
        im = Image.fromarray(film.rendu(t)).resize((largeur, h), Image.LANCZOS)
        x, y = (i % cols) * (largeur + 8), (i // cols) * (h + 30)
        p.paste(im, (x, y))
        _, nom, u = film.scene_en(t)
        d.text((x + 4, y + h + 6), f"{t:.2f}s {nom} +{u:.2f}", fill=(255, 220, 120), font=police(F_BOLD, 16))
    p.save(chemin, quality=88)
    return chemin


def principal(classe):
    """Ligne de commande commune :
    film_sN.py                 -> films/SN-muet.mp4 (rendu complet)
    film_sN.py --brouillon     -> films/SN-brouillon.mp4 (moitie de taille, 15 i/s, sans flou)
    film_sN.py --images        -> apercus/SN-planche.jpg (une image par scene, plus les transitions)
    film_sN.py --images 1.2 4  -> ces instants seulement
    film_sN.py --decoupage     -> affiche les scenes et les voix (json)"""
    args = sys.argv[1:]
    film = classe()
    film.verifier()
    if "--decoupage" in args:
        print(json.dumps({"scenes": film.scenes_, "voix": film.voix_, "total": film.total}, indent=1))
        return
    if "--images" in args:
        valeurs = [float(x) for x in args[args.index("--images") + 1:]]
        if not valeurs:
            for nom, d, du in film.scenes_:
                valeurs += [d + 0.12, d + du * 0.55, d + du - 0.1]
        (ICI / "apercus").mkdir(exist_ok=True)
        print(planche(film, valeurs, ICI / "apercus" / f"{film.NOM}-planche.jpg"))
        return
    rendre(film, brouillon="--brouillon" in args)
