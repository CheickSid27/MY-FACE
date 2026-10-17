# -*- coding: utf-8 -*-
"""Le decoupage du motion design v4 (2 min), calcule a partir de la voix.

Chaque phrase de v4/voix/texte.txt ouvre une section (une ou plusieurs scenes). La
section dure au moins sa duree de base, et assez pour que la phrase finisse avant la
suivante. Les durees tombent sur des demi-secondes (un temps a 120 BPM), comme dans
la v1 et la v2, pour que les coupes restent dans le rythme de la musique.

Les trois scenes des problemes et le logo gardent les durees de la v2 : la bande son
de l'ouverture (v2/sons_v2.py) est calee dessus.

    python motion-design/v4/montage_v4.py   -> affiche le decoupage
"""

import math
import wave
from pathlib import Path

ICI = Path(__file__).resolve().parent
VOIX = ICI / "voix"
CIBLE = 120.0       # au moins deux minutes
QUEUE = 0.7         # silence garde apres chaque phrase

# (section = scene de texte.txt, [(scene, duree de base)], debut de la voix, duree figee)
SECTIONS = [
    ("probleme_tas", [("probleme_tas", 4.0)], 0.2, True),
    ("probleme_groupe", [("probleme_groupe", 4.0)], 0.1, True),
    ("probleme_perdu", [("probleme_perdu", 3.0)], 0.1, True),
    ("logo", [("logo", 2.0)], 0.0, True),
    ("depot", [("depot", 4.5)], 0.3, False),
    ("ia", [("ia", 6.5)], 0.3, False),
    ("scanne", [("titre_scanne", 0.5), ("accueil", 3.0)], 0.2, False),
    ("retrouve", [("titre_retrouve", 0.5), ("galerie", 3.0), ("visages", 4.5)], 0.2, False),
    ("selfie", [("selfie", 5.0)], 0.0, False),
    ("confiance", [("confiance", 5.5)], 0.3, False),
    ("repars", [("titre_repars", 0.5), ("panier", 4.0)], 0.2, False),
    ("telechargement", [("telechargement", 6.0)], 0.3, False),
    ("borne_monte", [("borne_monte", 2.0)], 0.0, False),
    ("borne_gros_plan", [("borne_gros_plan", 4.0)], 0.3, False),
    ("tirage_sort", [("tirage_sort", 2.0)], 0.3, False),
    ("qualite", [("qualite", 4.0)], 0.3, False),
    ("offertes", [("offertes", 5.5)], 0.3, False),
    ("tableau", [("tableau", 5.5)], 0.3, False),
    ("preuve", [("preuve", 6.5)], 0.3, False),
    ("partout", [("partout", 6.5)], 0.3, False),
    ("ivoirienne", [("ivoirienne", 5.0)], 0.3, False),
    ("fin", [("fin", 6.5)], 0.05, False),
]
# ou ajouter des demi-secondes pour atteindre la cible (les nouvelles scenes respirent)
RESPIRATIONS = ["ia", "preuve", "partout", "telechargement", "offertes", "tableau", "depot",
                "confiance", "ivoirienne", "fin"]


def duree_wav(chemin):
    with wave.open(str(chemin)) as w:
        return w.getnframes() / w.getframerate()


def phrases():
    out = {}
    for l in (VOIX / "texte.txt").read_text(encoding="utf-8").splitlines():
        if l.strip() and not l.startswith("#"):
            ident, scene, _ = l.split("|", 2)
            out[scene] = ident
    return out


def demi(x):
    return math.ceil(x * 2 - 1e-6) / 2


def decoupage():
    """-> (scenes [(nom, debut, duree)], voix [(ident, debut)], total)"""
    idents = phrases()
    durees = []
    for section, scenes, dv, fige in SECTIONS:
        base = sum(d for _, d in scenes)
        lg = duree_wav(VOIX / f"{idents[section]}.wav")
        durees.append(base if fige else max(base, demi(dv + lg + QUEUE)))
    total = sum(durees)
    k = 0
    while total < CIBLE:
        i = [s[0] for s in SECTIONS].index(RESPIRATIONS[k % len(RESPIRATIONS)])
        durees[i] += 0.5
        total += 0.5
        k += 1
    scenes_out, voix_out, t = [], [], 0.0
    for (section, scenes, dv, _), duree in zip(SECTIONS, durees):
        voix_out.append((idents[section], t + dv))
        reste = duree - sum(d for _, d in scenes)
        for j, (nom, d) in enumerate(scenes):
            d = d + reste if j == len(scenes) - 1 else d
            scenes_out.append((nom, t, d))
            t += d
    return scenes_out, voix_out, t


if __name__ == "__main__":
    sc, vx, total = decoupage()
    for nom, debut, d in sc:
        print(f"  {debut:6.1f} s  {d:4.1f} s  {nom}")
    print(f"  total {total:.1f} s")
