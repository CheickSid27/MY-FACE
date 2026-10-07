# -*- coding: utf-8 -*-
"""Bande son du motion design v3 : la musique et les bruitages de la v2, avec la
voix off Gemini (motion-design/v3/voix/N*.wav, 48 kHz mono).

Chaque phrase demarre a son temps de la v2 (v2/voix/texte.txt), donc reste calee sur
les images. Une phrase qui deborderait sur la suivante est resserree sans changer la
hauteur de la voix (au plus 15 %).

    python motion-design/v3/sons_v3.py                  -> motion-design/v3/son-motion-design-v3.wav
    python motion-design/v3/sons_v3.py --voix DOSSIER   (essai avec d'autres fichiers N*.wav)
"""

import argparse
import sys
import wave
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "v2"))
import sons_v2 as V2  # noqa: E402

SR, N, DUREE = V2.SR, V2.N, V2.DUREE
MARGE = 0.12            # silence minimal garde avant la phrase suivante
RESSERRE_MAX = 0.85     # on ne raccourcit jamais une phrase de plus de 15 %


def resserrer(a, f):
    """Raccourcit a la duree x f sans changer la hauteur (WSOLA)."""
    if f >= 0.999:
        return a
    trame = int(0.04 * SR)
    pas_sortie = trame // 2
    pas_entree = pas_sortie / f
    tol = int(0.012 * SR)
    fen = np.hanning(trame)
    sortie = np.zeros(int(len(a) * f) + 2 * trame)
    poids = np.zeros_like(sortie)
    pos_entree, pos_sortie, prec = 0.0, 0, None
    while True:
        centre = int(pos_entree)
        if centre + trame + tol >= len(a) or pos_sortie + trame >= len(sortie):
            break
        if prec is None:
            k = centre
        else:
            cible = a[prec + pas_sortie: prec + pas_sortie + trame]
            lo, hi = max(0, centre - tol), min(len(a) - trame, centre + tol)
            if len(cible) < trame or hi <= lo:
                k = centre
            else:
                k = lo + int(np.argmax(np.correlate(a[lo:hi + trame], cible, mode="valid")))
        sortie[pos_sortie:pos_sortie + trame] += a[k:k + trame] * fen
        poids[pos_sortie:pos_sortie + trame] += fen
        prec = k
        pos_entree += pas_entree
        pos_sortie += pas_sortie
    sortie = sortie / np.maximum(poids, 1e-3)
    return sortie[: int(len(a) * f)]


def lire(chemin):
    with wave.open(str(chemin)) as w:
        if w.getframerate() != SR:
            sys.exit(f"{chemin.name} : {w.getframerate()} Hz, il faut {SR} Hz")
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768


def voix(dossier):
    lignes = []
    for l in (ICI.parent / "v2" / "voix" / "texte.txt").read_text(encoding="utf-8").splitlines():
        if l.strip() and not l.startswith("#"):
            lignes.append((l.split("|")[0], float(l.split("|")[1])))
    v = np.zeros(N)
    for k, (ident, debut) in enumerate(lignes):
        a = lire(dossier / f"{ident}.wav")
        nz = np.flatnonzero(np.abs(a) > 0.01)
        a = a[max(0, nz[0] - int(0.03 * SR)): nz[-1] + int(0.15 * SR)]   # pile au debut, queue gardee
        suivant = lignes[k + 1][1] if k + 1 < len(lignes) else DUREE
        place = int((suivant - debut - MARGE) * SR)
        note = ""
        if len(a) > place:
            f = max(place / len(a), RESSERRE_MAX)
            note = f"  resserree de {(1 - f) * 100:.0f} %"
            a = resserrer(a, f)
            if len(a) > place:
                note += f", deborde encore de {(len(a) - place) / SR:.2f} s"
        print(f"  {ident}  {debut:5.2f} s  {len(a) / SR:4.1f} s{note}")
        a = V2.traiter_voix(a) * 0.85
        i = int(debut * SR)
        a = a[: N - i]
        v[i:i + len(a)] += a
    return v


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--voix", type=Path, default=ICI / "voix", help="dossier des N01.wav a N12.wav")
    args = p.parse_args()
    m = V2.ouverture() + V2.groove()
    s = V2.bruitages_ouverture() + V2.bruitages_myface()
    v = voix(args.voix.resolve())
    env = np.convolve(np.abs(v), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
    gain = 1 - 0.55 * np.clip(env / 0.05, 0, 1)
    mix = m * 0.85 * gain[:, None] + s * (1 - 0.35 * np.clip(env / 0.05, 0, 1))[:, None] + np.stack([v, v], axis=1)
    mix = mix / (np.abs(mix).max() + 1e-9)
    mix = np.tanh(2.2 * mix) / np.tanh(2.2) * 0.95
    sortie = ICI / "son-motion-design-v3.wav"
    wavfile.write(sortie, SR, (mix * 32767).astype(np.int16))
    print(f"{sortie}  {DUREE:.0f} s")


if __name__ == "__main__":
    main()
