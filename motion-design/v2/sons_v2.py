# -*- coding: utf-8 -*-
"""Bande son du motion design v2 (50 s).

0 a 11 s, les problemes : nappe sombre, battement de coeur, tic-tac, bruits de
papier sur le tas, notifications qui s'emballent dans le groupe, echec de la
recherche. A 11 s, le logo : impact, puis le groove afro-house de la v1
(instruments repris de motion-design/sons.py, inchange).
Voix off : motion-design/v2/voix/N*.wav, placees selon voix/texte.txt, avec un
traitement leger (filtre, presence, compression, petite piece).

    python motion-design/v2/sons_v2.py   -> motion-design/v2/son-motion-design-v2.wav
"""

import sys
import wave
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
import sons as S  # noqa: E402

DUREE = 50.0
S.DUREE = DUREE
S.N = int(S.SR * DUREE)
SR, N = S.SR, S.N
rng = np.random.default_rng(21)

# --------------------------------------------------------------------------
# Temps du film v2 (rendre_film_v2.scenes)
# --------------------------------------------------------------------------
LOGO = 11.0
TITRES = [13.0, 16.5, 29.5]
CALME = (34.0, 36.0)
TOUCHERS = [14.75, 17.6, 19.35, 20.45, 22.1, 23.0, 24.95, 25.85, 26.75, 28.85, 32.6, 36.7, 37.9, 39.2]
ENVOLEES = [13.5, 17.95, 18.6, 20.0, 20.6, 21.15, 24.5, 30.0, 34.0, 41.3]
POPS = [23.2 + k * 0.09 for k in range(10)] + [32.9 + k * 0.07 for k in range(5)] + [44.1, 44.8]
COMPTEUR = [27.65 + k * 0.06 for k in range(10)] + [31.2 + k * 0.09 for k in range(5)]
IMPRIMANTE = [40.0, 40.3, 40.6]
FIN, CHUTE, MOTS_FIN = 46.0, 46.9, [47.2, 47.7, 48.2]


# --------------------------------------------------------------------------
# Sons de l'ouverture
# --------------------------------------------------------------------------
def papier(d=0.07):
    t = S.temps(d)
    return S.filtre(S.bruit(d), 900, 5200) * np.exp(-t / (d / 3))


def froissement(d=0.18):
    t = S.temps(d)
    env = np.minimum(1, t / 0.02) * np.exp(-t / (d / 2.5))
    return S.filtre(S.bruit(d), 1800, 9000) * env * (0.6 + 0.4 * np.sin(2 * np.pi * 37 * t))


def notif():
    t = S.temps(0.26)
    x = np.sin(2 * np.pi * 1318 * t) * (t < 0.11) + np.sin(2 * np.pi * 1760 * t) * (t >= 0.11)
    return x * np.exp(-((t % 0.11) / 0.06)) * 0.7


def craquement():
    x = S.bruit(0.18)
    x = np.round(x * 3) / 3  # numerique, abime
    return S.filtre(x, 300, 4000) * np.exp(-S.temps(0.18) / 0.07)


def erreur():
    t = S.temps(0.32)
    x = np.sign(np.sin(2 * np.pi * 110 * t)) * 0.5 + np.sign(np.sin(2 * np.pi * 116 * t)) * 0.5
    return S.filtre(x, haut=1400) * np.exp(-t / 0.18) * 0.6


def coeur():
    t = S.temps(0.5)
    f = 48 + 20 * np.exp(-t / 0.03)
    un = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.09)
    deux = np.roll(un, int(0.17 * SR)) * 0.6
    deux[: int(0.17 * SR)] = 0
    return un + deux


def nappe(d):
    t = S.temps(d)
    x = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * a for f, a in ((55, 1), (110, 0.5), (164.8, 0.35), (220, 0.2)))
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.2 * t)
    return S.filtre(x * lfo, haut=600) * np.minimum(1, t / 1.2)


def ouverture():
    m = np.zeros((N, 2))
    S.poser(m, nappe(LOGO - 0.3), 0.0, 0.32)
    for k in range(int(LOGO)):
        if k < LOGO - 0.6:
            S.poser(m, coeur(), k, 0.55)
    tic = S.tic()
    for k in range(int(LOGO * 2)):
        S.poser(m, tic, k * 0.5 + 0.25, 0.10, 0.4)
    S.poser(m, S.montee(2.4, 250, 7000), LOGO - 2.4, 0.22)
    return m


def bruitages_ouverture():
    s = np.zeros((N, 2))
    r = np.random.default_rng(5)
    # les tirages tombent (memes temps que rendre_film_v2 : t0 + ~0,35 s)
    for k in range(24):
        S.poser(s, papier(), 0.05 + k * 0.05 + r.uniform(0, 0.12) + 0.33, 0.35, r.uniform(-0.6, 0.6))
    # les mains fouillent
    t = 1.45
    while t < 3.95:
        S.poser(s, froissement(r.uniform(0.12, 0.25)), t, 0.28, r.uniform(-0.7, 0.7))
        t += r.uniform(0.07, 0.16)
    # le groupe : notifications qui s'emballent
    t, pas = 4.3, 0.55
    while t < 7.75:
        S.poser(s, notif(), t, 0.22, r.uniform(-0.3, 0.3))
        t += pas
        pas = max(0.09, pas * 0.82)
    S.poser(s, craquement(), 5.0, 0.4)
    for t0 in (4.9, 5.55, 6.2):
        S.poser(s, S.coup_sourd(), t0, 0.35)
    # la recherche qui echoue
    t = 8.0
    while t < 9.6:
        S.poser(s, S.tic(), t, 0.10)
        t += 0.04 + 0.1 * ((t - 8.0) / 1.6) ** 2
    for t0 in (8.42, 8.84, 9.26):
        S.poser(s, S.bip(), t0, 0.22)
    S.poser(s, erreur(), 9.68, 0.55)
    S.poser(s, S.coup_sourd(), 9.25, 0.4)
    return s


# --------------------------------------------------------------------------
# La partie MYFACE (groove de la v1, recale)
# --------------------------------------------------------------------------
def coupe(t):
    return any(a <= t < a + 0.5 for a in TITRES) or t >= DUREE - 0.5


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
    mesure = 0
    t0 = LOGO
    while t0 < DUREE:
        r = mesure % 4
        calme = CALME[0] <= t0 < CALME[1]
        intro = t0 < LOGO + 2.0  # le logo : accord seul, la batterie arrive sur « Scanne. »
        S.poser(m, S.accord(accords[r], 2.0), t0, 0.22 if (calme or intro) else 0.11)
        for k in range(32):
            t = t0 + k * seize + (swing if k % 2 else 0)
            if t >= DUREE or coupe(t):
                continue
            S.poser(m, sh, t, 0.10 * (1.0 if k % 2 == 0 else 0.6), 0.35)
            if intro:
                continue
            if calme:
                if k == 0:
                    S.poser(m, S.filtre(gc, haut=220), t, 0.6)
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
                if t < DUREE and not coupe(t):
                    S.poser(m, S.tambour(f), t, 0.22, -0.4)
            for k, dur, mult in lignes_basse:
                t = t0 + k * seize
                if t < DUREE and not coupe(t) and not calme:
                    S.poser(m, S.basse(racines[r] * mult, dur), t, 0.42)
            if mesure % 2 == 1 or calme:
                for k, i in riff:
                    t = t0 + k * seize
                    if t < DUREE and not coupe(t):
                        S.poser(m, S.kalimba(penta[i]), t, 0.13, 0.25)
        mesure += 1
        t0 += 2.0
    S.poser(m, S.montee(1.9, 400, 8000), CALME[1] - 1.9, 0.16)
    debut_fondu = int((DUREE - 0.6) * SR)
    m[debut_fondu:] *= np.linspace(1, 0, N - debut_fondu)[:, None]
    return m


def bruitages_myface():
    s = np.zeros((N, 2))
    S.poser(s, S.impact(), LOGO, 0.75)
    S.poser(s, S.chute(), LOGO + 0.05, 0.45)
    S.poser(s, S.scintille(), LOGO + 0.4, 0.5)
    for t in TOUCHERS:
        S.poser(s, S.toucher(), t, 0.5)
    for t in ENVOLEES:
        S.poser(s, S.envolee(), t - 0.15, 0.22)
    S.poser(s, S.bip(), 21.7, 0.35)
    for t in POPS:
        S.poser(s, S.pop(), t, 0.22)
    S.poser(s, S.declencheur(), 26.75, 0.6)
    S.poser(s, S.balayage(0.8), 26.85, 0.4)
    for t in COMPTEUR:
        S.poser(s, S.tic(), t, 0.3)
    S.poser(s, S.barre(), 30.6, 0.35)
    S.poser(s, S.coup_sourd(), 30.9, 0.7)
    S.poser(s, S.caisse(), 30.92, 0.45)
    for t in (34.9, 43.0):
        S.poser(s, S.scintille(), t, 0.6)
    for t in IMPRIMANTE:
        S.poser(s, S.imprimante(), t, 0.4)
    # le rideau de l'avant / apres
    long = S.filtre(S.bruit(1.5), 500, 6000) * np.sin(np.pi * S.temps(1.5) / 1.5) ** 2
    S.poser(s, long, 42.45, 0.25)
    for t in TITRES:
        S.poser(s, S.impact(), t, 0.55)
    S.poser(s, S.impact(), FIN, 0.6)
    S.poser(s, S.chute(), CHUTE, 0.6)
    for t in MOTS_FIN:
        S.poser(s, S.coup_sourd(), t, 0.5)
    return s


# --------------------------------------------------------------------------
# Voix off
# --------------------------------------------------------------------------
def traiter_voix(a):
    a = S.filtre(a, 90)                                   # enleve le grave inutile
    a = a + 0.25 * S.filtre(a, 2500, 5000)                # un peu de presence
    pic = np.abs(a).max() + 1e-9
    a = np.tanh(1.6 * a / pic) / np.tanh(1.6)             # compression douce
    ir_t = S.temps(0.32)
    ir = rng.normal(0, 1, len(ir_t)) * np.exp(-ir_t / 0.07)
    ir = S.filtre(ir, 300, 6000)
    ir /= np.abs(ir).sum() + 1e-9
    piece = fftconvolve(a, ir)[: len(a)] * 6.0
    return a * 0.9 + piece * 0.1                          # petite piece, pas une cathedrale


def voix():
    v = np.zeros(N)
    for l in open(ICI / "voix" / "texte.txt", encoding="utf-8"):
        if not l.strip() or l.startswith("#"):
            continue
        ident, debut = l.split("|")[0], float(l.split("|")[1])
        with wave.open(str(ICI / "voix" / f"{ident}.wav")) as w:
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
        nz = np.where(np.abs(a) > 0.01)[0]
        a = a[max(0, nz[0] - int(0.03 * SR)):]               # le debut de la parole tombe pile
        a = traiter_voix(a) * 0.85
        i = int(debut * SR)
        a = a[: N - i]
        v[i:i + len(a)] += a
    return v


def main():
    m = ouverture() + groove()
    s = bruitages_ouverture() + bruitages_myface()
    v = voix()
    env = np.convolve(np.abs(v), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
    gain = 1 - 0.55 * np.clip(env / 0.05, 0, 1)
    mix = m * 0.85 * gain[:, None] + s * (1 - 0.35 * np.clip(env / 0.05, 0, 1))[:, None] + np.stack([v, v], axis=1)
    mix = mix / (np.abs(mix).max() + 1e-9)
    mix = np.tanh(2.2 * mix) / np.tanh(2.2) * 0.95
    sortie = ICI / "son-motion-design-v2.wav"
    wavfile.write(sortie, SR, (mix * 32767).astype(np.int16))
    print(f"{sortie}  {DUREE:.0f} s")


if __name__ == "__main__":
    main()
