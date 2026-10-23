# -*- coding: utf-8 -*-
"""Bande son du motion design v5 (1 min, photographes).

- Jusqu'au logo : l'ouverture sombre de la v2 (nappe, coeur, tic-tac, montee), avec des
  notifications de reseau social et le defilement du fil.
- Ensuite : le groove de la v2 / v4 jusqu'a la fin.
- Bruitages calés sur les animations de v5/rendre_film_v5.py (toucher, balayage de l'IA,
  vibration de la vente, cartes des packs, « 0 % »).
- La voix Zephyr (v5/voix/V*.wav), chaque phrase au debut de sa scene (montage_v5.py).

    python marketing/motion-design/v5/sons_v5.py   -> marketing/motion-design/v5/son-motion-design-v5.wav
"""

import sys
import wave
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI.parent / "v2"))
sys.path.insert(0, str(ICI))
import sons_v2 as V2  # noqa: E402
import montage_v5 as M  # noqa: E402

S = V2.S
SCENES, VOIX, DUREE = M.decoupage()
SR = S.SR
N = int(SR * DUREE)
S.DUREE, S.N, V2.DUREE, V2.N = DUREE, N, DUREE, N
rng = np.random.default_rng(55)
DEBUT = {nom: t for nom, t, _ in SCENES}
LOGO = DEBUT["lien"]


def a(nom, t):
    return DEBUT[nom] + t


# --------------------------------------------------------------------------
# Musique
# --------------------------------------------------------------------------
def ouverture():
    m = np.zeros((N, 2))
    S.poser(m, V2.nappe(LOGO - 0.3), 0.0, 0.32)
    for k in range(int(LOGO)):
        if k < LOGO - 0.6:
            S.poser(m, V2.coeur(), k, 0.5)
    tic = S.tic()
    for k in range(int(LOGO * 2)):
        S.poser(m, tic, k * 0.5 + 0.25, 0.10, 0.4)
    S.poser(m, S.montee(2.4, 250, 7000), LOGO - 2.4, 0.22)
    return m


def groove():
    m = np.zeros((N, 2))
    gc, cl, ch, cho, sh = S.grosse_caisse(), S.clap(), S.charleston(), S.charleston(True), S.shaker()
    seize, swing = S.TEMPS / 4, 0.018
    racines = [55.0, 43.65, 65.41, 49.0]
    accords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66)]
    penta = [440.0, 523.25, 587.33, 659.25, 783.99]
    riff = [(0, 3), (3, 2), (6, 4), (10, 3), (14, 1), (16, 0), (19, 2), (22, 3), (27, 4), (30, 2)]
    tambours = [(3, 170), (6, 200), (11, 170), (14, 230), (19, 170), (22, 200), (27, 150), (30, 230)]
    lignes_basse = [(0, 0.3, 1), (3, 0.2, 1), (6, 0.25, 1.5), (10, 0.2, 2), (14, 0.3, 1),
                    (16, 0.3, 1), (19, 0.2, 1), (22, 0.25, 1.5), (26, 0.2, 2), (30, 0.2, 1.5)]
    mesure, t0 = 0, LOGO
    while t0 < DUREE:
        r = mesure % 4
        intro = t0 < LOGO + 2.0
        S.poser(m, S.accord(accords[r], 2.0), t0, 0.22 if intro else 0.11)
        for k in range(32):
            t = t0 + k * seize + (swing if k % 2 else 0)
            if t >= DUREE - 0.5:
                continue
            S.poser(m, sh, t, 0.10 * (1.0 if k % 2 == 0 else 0.6), 0.35)
            if intro:
                continue
            if k % 4 == 0:
                S.poser(m, gc, t, 0.95)
            if k % 8 == 4:
                S.poser(m, cl, t, 0.5, -0.1)
            S.poser(m, ch, t, (0.13, 0.06, 0.1, 0.06)[k % 4], 0.3)
            if k % 4 == 2:
                S.poser(m, cho, t, 0.08, -0.3)
        if not intro:
            for k, f in tambours:
                t = t0 + k * seize
                if t < DUREE - 0.5:
                    S.poser(m, S.tambour(f), t, 0.22, -0.4)
            for k, dur, mult in lignes_basse:
                t = t0 + k * seize
                if t < DUREE - 0.5:
                    S.poser(m, S.basse(racines[r] * mult, dur), t, 0.42)
            if mesure % 2 == 1:
                for k, i in riff:
                    t = t0 + k * seize
                    if t < DUREE - 0.5:
                        S.poser(m, S.kalimba(penta[i]), t, 0.13, 0.25)
        mesure += 1
        t0 += 2.0
    debut_fondu = int((DUREE - 0.8) * SR)
    m[debut_fondu:] *= np.linspace(1, 0, N - debut_fondu)[:, None]
    return m


# --------------------------------------------------------------------------
# Bruitages
# --------------------------------------------------------------------------
def bruitages():
    s = np.zeros((N, 2))
    tou = S.toucher()
    # le fil : on fait defiler, les notifications s'enchainent
    for t in (2.4, 3.4, 4.4):
        S.poser(s, tou, a("reseaux", t), 0.35)
        S.poser(s, S.balayage(0.35), a("reseaux", t + 0.05), 0.12)
    t, pas = a("reseaux", 0.8), 0.7
    while t < a("cherche", 4.8):
        S.poser(s, V2.notif(), t, 0.16, rng.uniform(-0.3, 0.3))
        t += pas
        pas = max(0.14, pas * 0.9)
    for t in (0.5, 1.3, 2.1, 2.9):
        S.poser(s, tou, a("cherche", t), 0.35)
        S.poser(s, S.balayage(0.3), a("cherche", t + 0.05), 0.12)
    S.poser(s, S.coup_sourd(), a("cherche", 2.3), 0.5)
    # le logo, le lien, le QR, le selfie
    S.poser(s, S.impact(), a("lien", 0.35), 0.4)
    S.poser(s, S.scintille(), a("lien", 0.45), 0.35)
    S.poser(s, S.pop(), a("lien", 1.5), 0.3)
    S.poser(s, S.bip(), a("lien", 2.3), 0.3)
    S.poser(s, S.coup_sourd(), a("lien", 3.3), 0.45)
    S.poser(s, S.pop(), a("lien", 4.5), 0.3)
    # le compte, puis le depot
    S.poser(s, S.envolee(), a("compte", 0.0), 0.25)
    S.poser(s, S.pop(), a("compte", 0.2), 0.25)
    for k in range(22):
        S.poser(s, S.pop(), a("compte", 2.6 + 0.25 + k * 0.13 + 0.85), 0.07, rng.uniform(-0.4, 0.4))
    S.poser(s, S.coup_sourd(), a("compte", 2.6 + 1.2), 0.35)
    S.poser(s, S.coup_sourd(), a("compte", 2.6 + 2.4), 0.35)
    # l'IA
    S.poser(s, S.balayage(1.9), a("ia", 0.4), 0.2)
    for i in range(2):
        S.poser(s, S.bip(), a("ia", 0.95 + 0.25 * i), 0.3)
    S.poser(s, S.envolee(), a("ia", 3.4), 0.25)
    for k in range(13):
        S.poser(s, S.pop(), a("ia", 3.4 + 0.55 + k * 0.08), 0.08, rng.uniform(-0.4, 0.4))
    S.poser(s, S.coup_sourd(), a("ia", 3.4 + 1.9), 0.4)
    # l'invite
    for t in (1.15, 2.5, 3.85):
        S.poser(s, tou, a("invite", t), 0.4)
    S.poser(s, S.scintille(), a("invite", 4.3), 0.3)
    # offertes ou payantes, l'argent
    S.poser(s, tou, a("choix", 0.75), 0.4)
    S.poser(s, tou, a("choix", 0.9), 0.35)
    S.poser(s, S.envolee(), a("choix", 1.0), 0.2)
    S.poser(s, S.pop(), a("choix", 2.75), 0.25)
    S.poser(s, S.bip(), a("choix", 3.5), 0.3)
    for i in range(4):
        S.poser(s, S.pop(), a("choix", 4.2 + i * 0.12), 0.18)
    S.poser(s, S.balayage(0.5), a("choix", 5.0), 0.15)
    S.poser(s, S.caisse(), a("choix", 5.45), 0.35)
    # la vente : notification et vibration
    S.poser(s, S.bip(), a("vente", 0.35), 0.4)
    for t0, t1 in ((0.35, 1.3), (1.6, 2.2)):
        t = t0
        while t < t1:
            S.poser(s, S.filtre(S.bruit(0.06), 80, 220), a("vente", t), 0.5)
            t += 0.07
    # MYFACE Pro
    S.poser(s, S.envolee(), a("pro", 0.0), 0.25)
    S.poser(s, S.envolee(), a("pro", 1.3), 0.2)
    for i in range(3):
        S.poser(s, S.pop(), a("pro", 2.6 + i * 0.12), 0.18)
    # les packs, zero commission
    for i in range(3):
        S.poser(s, S.coup_sourd(), a("packs", 0.3 + i * 0.35), 0.3)
    S.poser(s, S.pop(), a("packs", 2.0), 0.25)
    S.poser(s, S.pop(), a("packs", 3.0), 0.25)
    S.poser(s, S.impact(), a("packs", 3.6), 0.45)
    # la fin
    S.poser(s, S.scintille(), a("fin", 0.9), 0.35)
    for i in range(3):
        S.poser(s, S.coup_sourd(), a("fin", 1.2 + i * 0.5), 0.35)
    return s


# --------------------------------------------------------------------------
# Voix
# --------------------------------------------------------------------------
def voix():
    v = np.zeros(N)
    for ident, debut in VOIX:
        with wave.open(str(ICI / "voix" / f"{ident}.wav")) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
        nz = np.flatnonzero(np.abs(x) > 0.01)
        x = x[max(0, nz[0] - int(0.03 * SR)): nz[-1] + int(0.15 * SR)]
        x = V2.traiter_voix(x) * 0.85
        i = int(debut * SR)
        x = x[: N - i]
        v[i:i + len(x)] += x
    return v


def main():
    m = ouverture() + groove()
    s = bruitages()
    v = voix()
    env = np.convolve(np.abs(v), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
    gain = 1 - 0.55 * np.clip(env / 0.05, 0, 1)
    mix = m * 0.85 * gain[:, None] + s * (1 - 0.35 * np.clip(env / 0.05, 0, 1))[:, None] + np.stack([v, v], axis=1)
    mix = mix / (np.abs(mix).max() + 1e-9)
    mix = np.tanh(2.2 * mix) / np.tanh(2.2) * 0.95
    sortie = ICI / "son-motion-design-v5.wav"
    wavfile.write(sortie, SR, (mix * 32767).astype(np.int16))
    print(f"{sortie}  {DUREE:.1f} s")


if __name__ == "__main__":
    main()
