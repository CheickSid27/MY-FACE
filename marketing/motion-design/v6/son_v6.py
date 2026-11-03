# -*- coding: utf-8 -*-
"""Bande son et assemblage des films v6.

- Avant le moment cle (DROP du film) : l'ouverture tendue de la v2 (nappe, coeur, tic-tac,
  montee) ; au moment cle, impact et groove a 120 BPM jusqu'a la fin (mesures de 2 s qui
  partent du drop, donc les coupes tombent sur les temps).
- Bruitages synthetises, poses aux instants des animations (fonction sons(a) de chaque film).
- La voix du scenario (scenarios/voix/S*.wav), traitee une fois, decoupee en lignes et posee
  au debut de chaque scene (moteur_v6.decoupage).
- Musique baissee d'environ 9 dB sous la voix ; normalisation en deux passes a -14 LUFS, crete -1 dB.
- Assemblage : films/SN.mp4 (image copiee + AAC 256k) et films/SN-partage.mp4 (plus leger).

    python marketing/motion-design/v6/son_v6.py S3          -> films/S3-son.wav, films/S3.mp4, films/S3-partage.mp4
"""

import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ICI = Path(__file__).resolve().parent
for p in (ICI.parent, ICI.parent / "v2", ICI):
    sys.path.insert(0, str(p))
import sons_v2 as V2  # noqa: E402
from moteur_v6 import FFMPEG, SORTIES, decoupage, lire_voix  # noqa: E402

S = V2.S
SR = S.SR
MODULES = {"S1": "film_s1", "S2": "film_s2", "S3": "film_s3", "S4": "film_s4", "S5": "film_s5", "S6": "film_s6"}
# un caractere par film : accords, basse et instrument de la melodie
GAMMES = {
    "S1": dict(transpo=0, riff=True, accords=[(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66)]),
    "S2": dict(transpo=2, riff=True, accords=[(261.63, 329.63, 392.0), (220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66)]),
    "S3": dict(transpo=-2, riff=False, accords=[(220.0, 261.63, 329.63), (196.0, 246.94, 293.66), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66)]),
    "S4": dict(transpo=0, riff=True, accords=[(174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (220.0, 261.63, 329.63), (196.0, 246.94, 293.66)]),
    "S5": dict(transpo=3, riff=True, accords=[(261.63, 329.63, 392.0), (196.0, 246.94, 293.66), (220.0, 261.63, 329.63), (174.61, 220.0, 261.63)]),
    "S6": dict(transpo=-3, riff=True, accords=[(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66), (164.81, 207.65, 246.94)]),
}
SONS = {"toucher": S.toucher, "envolee": S.envolee, "bip": S.bip, "pop": S.pop, "declencheur": S.declencheur,
        "tic": S.tic, "caisse": S.caisse, "coup": S.coup_sourd, "scintille": S.scintille,
        "imprimante": S.imprimante, "impact": S.impact, "chute": S.chute, "notif": V2.notif,
        "papier": V2.papier, "froissement": V2.froissement, "erreur": V2.erreur}


def demi_ton(f, n):
    return f * 2 ** (n / 12)


def ouverture(N, fin):
    m = np.zeros((N, 2))
    if fin <= 0.6:
        return m
    S.poser(m, V2.nappe(fin), 0.0, 0.30)
    for k in range(int(fin)):
        if k < fin - 0.6:
            S.poser(m, V2.coeur(), k, 0.45)
    tic = S.tic()
    for k in range(int(fin * 2)):
        S.poser(m, tic, k * 0.5 + 0.25, 0.08, 0.4)
    d = min(2.4, fin)
    S.poser(m, S.montee(d, 250, 7000), fin - d, 0.2)
    return m


def groove(N, duree, t_drop, g):
    m = np.zeros((N, 2))
    gc, cl, ch, cho, sh = S.grosse_caisse(), S.clap(), S.charleston(), S.charleston(True), S.shaker()
    seize, swing = S.TEMPS / 4, 0.018
    racines = [55.0, 43.65, 65.41, 49.0]
    penta = [440.0, 523.25, 587.33, 659.25, 783.99]
    riff = [(0, 3), (3, 2), (6, 4), (10, 3), (14, 1), (16, 0), (19, 2), (22, 3), (27, 4), (30, 2)]
    tambours = [(3, 170), (6, 200), (11, 170), (14, 230), (19, 170), (22, 200), (27, 150), (30, 230)]
    lignes_basse = [(0, 0.3, 1), (3, 0.2, 1), (6, 0.25, 1.5), (10, 0.2, 2), (14, 0.3, 1),
                    (16, 0.3, 1), (19, 0.2, 1), (22, 0.25, 1.5), (26, 0.2, 2), (30, 0.2, 1.5)]
    tr = g["transpo"]
    mesure, t0 = 0, t_drop
    while t0 < duree:
        r = mesure % 4
        S.poser(m, S.accord([demi_ton(f, tr) for f in g["accords"][r]], 2.0), t0, 0.11)
        for k in range(32):
            t = t0 + k * seize + (swing if k % 2 else 0)
            if t >= duree - 0.4:
                continue
            S.poser(m, sh, t, 0.10 * (1.0 if k % 2 == 0 else 0.6), 0.35)
            if k % 4 == 0:
                S.poser(m, gc, t, 0.95)
            if k % 8 == 4:
                S.poser(m, cl, t, 0.5, -0.1)
            S.poser(m, ch, t, (0.13, 0.06, 0.1, 0.06)[k % 4], 0.3)
            if k % 4 == 2:
                S.poser(m, cho, t, 0.08, -0.3)
        for k, f in tambours:
            t = t0 + k * seize
            if t < duree - 0.4:
                S.poser(m, S.tambour(f), t, 0.22, -0.4)
        for k, dur, mult in lignes_basse:
            t = t0 + k * seize
            if t < duree - 0.4:
                S.poser(m, S.basse(demi_ton(racines[r], tr) * mult, dur), t, 0.42)
        if g["riff"] and mesure % 2 == 1:
            for k, i in riff:
                t = t0 + k * seize
                if t < duree - 0.4:
                    S.poser(m, S.kalimba(demi_ton(penta[i], tr)), t, 0.13, 0.25)
        mesure += 1
        t0 += 2.0
    i = int((duree - 0.9) * SR)
    m[i:] *= np.linspace(1, 0, N - i)[:, None]
    return m


def voix(N, nom_wav, placements):
    x, sr = lire_voix(nom_wav)
    assert sr == SR, sr
    x = V2.traiter_voix(x) * 0.85
    v = np.zeros(N)
    for a, b, debut in placements:
        i0, i1 = max(0, int((a - 0.04) * SR)), min(len(x), int((b + 0.12) * SR))
        seg = x[i0:i1].copy()
        f = int(0.01 * SR)
        seg[:f] *= np.linspace(0, 1, f)
        seg[-f:] *= np.linspace(1, 0, f)
        j = int((debut - 0.04) * SR)
        seg = seg[: N - j]
        v[j:j + len(seg)] += seg
    return v


def loudnorm(entree, sortie):
    """Deux passes ffmpeg : mesure, puis normalisation a -14 LUFS, crete -1 dB."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(entree), "-af",
                        "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    mes = json.loads(re.findall(r"\{[^{}]+\}", r.stderr)[-1])
    af = ("loudnorm=I=-14:TP=-1:LRA=11:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:"
          "measured_thresh={input_thresh}:offset={target_offset}:linear=true").format(**mes)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(entree), "-af", af, "-ar", str(SR), str(sortie)], check=True)
    return mes


def fabriquer(code):
    mod = importlib.import_module(MODULES[code])
    film = getattr(mod, f"Film{code}")
    scenes, placements, duree = decoupage(film.LIGNES)
    debut = {n: d for n, d, _ in scenes}

    def a(nom, t):
        return debut[nom] + t

    N = int(SR * duree)
    S.DUREE, S.N, V2.DUREE, V2.N = duree, N, duree, N
    t_drop = debut[film.DROP]
    m = ouverture(N, t_drop) + groove(N, duree, t_drop, GAMMES[code])
    s = np.zeros((N, 2))
    S.poser(s, S.impact(), t_drop, 0.45)
    for nom, t, gain, *pan in mod.sons(a):
        if t < duree:
            S.poser(s, SONS[nom]() if nom not in ("balayage", "montee") else
                    (S.balayage(pan[1]) if nom == "balayage" else S.montee(pan[1], 250, 7000)), t, gain,
                    pan[0] if pan else 0.0)
    v = voix(N, film.VOIX, placements)
    env = np.convolve(np.abs(v), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
    presence = np.clip(env / 0.05, 0, 1)
    mix = m * 0.85 * (1 - 0.65 * presence)[:, None] + s * (1 - 0.3 * presence)[:, None] + np.stack([v, v], axis=1)
    mix = mix / (np.abs(mix).max() + 1e-9)
    mix = np.tanh(2.0 * mix) / np.tanh(2.0) * 0.9
    SORTIES.mkdir(exist_ok=True)
    brut = SORTIES / f"{code}-son-brut.wav"
    wavfile.write(brut, SR, (mix * 32767).astype(np.int16))
    son = SORTIES / f"{code}-son.wav"
    mes = loudnorm(brut, son)
    brut.unlink()
    print(f"{son}  {duree:.1f} s  (avant normalisation : {mes['input_i']} LUFS)")
    muet = SORTIES / f"{code}-muet.mp4"
    if muet.exists():
        final = SORTIES / f"{code}.mp4"
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(muet), "-i", str(son), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(final)], check=True)
        partage = SORTIES / f"{code}-partage.mp4"
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(final), "-c:v", "libx264", "-preset", "slow", "-crf", "25",
                        "-maxrate", "3M", "-bufsize", "6M", "-pix_fmt", "yuv420p", "-colorspace", "bt709",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
                        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(partage)], check=True)
        for f in (final, partage):
            print(f"{f}  {f.stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    for c in sys.argv[1:]:
        fabriquer(c)
