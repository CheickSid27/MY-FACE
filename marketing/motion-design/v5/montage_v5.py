# -*- coding: utf-8 -*-
"""Le decoupage du motion design v5 (1 min, photographes), calcule a partir de la voix.

Comme la v4 : chaque phrase de v5/voix/texte.txt ouvre une scene, qui dure au moins sa duree
de base et assez pour que la phrase finisse avant la suivante. Les durees tombent sur des
demi-secondes (un temps a 120 BPM) pour que les coupes restent dans le rythme.

    python marketing/motion-design/v5/montage_v5.py   -> affiche le decoupage
"""

import math
import wave
from pathlib import Path

ICI = Path(__file__).resolve().parent
VOIX = ICI / "voix"
QUEUE = 0.7         # silence garde apres chaque phrase

# (scene = colonne 2 de texte.txt, duree de base, debut de la voix dans la scene)
SECTIONS = [
    ("reseaux", 5.0, 0.4),
    ("cherche", 4.5, 0.2),
    ("lien", 6.0, 0.6),
    ("compte", 6.0, 0.3),
    ("ia", 6.0, 0.3),
    ("invite", 6.0, 0.2),
    ("choix", 7.0, 0.3),
    ("vente", 3.0, 0.3),
    ("pro", 5.0, 0.2),
    ("packs", 7.0, 0.3),
    ("fin", 4.5, 0.2),
]


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
    scenes, voix, t = [], [], 0.0
    for nom, base, dv in SECTIONS:
        d = max(base, demi(dv + duree_wav(VOIX / f"{idents[nom]}.wav") + QUEUE))
        scenes.append((nom, t, d))
        voix.append((idents[nom], t + dv))
        t += d
    return scenes, voix, t


if __name__ == "__main__":
    s, _, total = decoupage()
    for nom, debut, d in s:
        print(f"  {debut:5.1f} s  {d:4.1f} s  {nom}")
    print(f"  total {total:.1f} s")
