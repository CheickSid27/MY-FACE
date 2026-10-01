# -*- coding: utf-8 -*-
"""La bande son du motion design : musique, bruitages et voix off.

Tout est fabrique ici (synthese), donc sans droits a payer :
- une boucle afro-house a 120 BPM (grosse caisse, clap, charleston, shaker,
  tambour parlant, basse, accords, kalimba), avec coupures sur les titres
  d'acte et un passage calme quand la borne apparait ;
- les bruitages cales sur le film : chaque toucher, les envolees, le bip du
  cadre, le declencheur, la caisse enregistreuse du -10 %, l'imprimante...
- la voix off temoin (voix Windows, voir voix/generer_voix.ps1), la musique
  baisse sous la voix.

Les temps suivent rendre_film.py (scenes en demi-secondes, film de 36 s).

    python motion-design/sons.py   -> motion-design/son-motion-design.wav
"""

import wave
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

ICI = Path(__file__).resolve().parent
SR = 48000
DUREE = 36.0
N = int(SR * DUREE)
BPM = 120
TEMPS = 60 / BPM  # 0,5 s
rng = np.random.default_rng(7)

# --------------------------------------------------------------------------
# Le film (secondes) : debuts de scene et evenements, voir rendre_film.py
# --------------------------------------------------------------------------
TITRES = [3.5, 7.0, 20.0]                        # « Scanne. » « Retrouve. » « Repars avec. »
TOUCHERS = [5.25, 8.1, 9.85, 10.95, 12.6, 13.5, 15.45, 16.35, 17.25, 19.35, 23.1, 27.2, 28.4, 29.7]
ENVOLEES = [4.0, 8.45, 9.1, 10.5, 11.1, 11.65, 15.0, 20.5, 24.5, 31.8]
BIPS = [1.25, 12.2]                              # le cadre se pose sur un visage
POPS = [1.35, 2.35] + [13.7 + k * 0.09 for k in range(10)] + [23.4 + k * 0.07 for k in range(5)]
DECLENCHEUR = 17.25
BALAYAGE = (17.35, 18.15)
COMPTEUR = [18.15 + k * 0.06 for k in range(10)] + [21.7 + k * 0.09 for k in range(5)]
BARRE = 21.1
TAMPON = 21.4
SCINTILLE = [25.4, 35.0]
IMPRIMANTE = [30.5, 30.8, 31.1]
IMPACT_FIN, CHUTE, MOTS_FIN = 32.5, 33.4, [33.7, 34.2, 34.75]
CALME = (24.5, 26.5)                             # la borne monte : la musique respire

VOIX = [("V01", 0.15), ("V02", 1.30), ("V03", 2.40), ("V04", 3.50), ("V05", 4.20), ("V06", 7.00),
        ("V07", 7.60), ("V08", 10.60), ("V09", 15.10), ("V10", 20.00), ("V11", 20.65), ("V12", 24.50),
        ("V13", 26.75), ("V14", 30.60), ("V15", 32.65), ("V04", 33.70), ("V06", 34.20), ("V10", 34.90)]


# --------------------------------------------------------------------------
# Outils
# --------------------------------------------------------------------------
def filtre(x, bas=None, haut=None, ordre=2):
    if bas and haut:
        sos = butter(ordre, [bas, haut], btype="band", fs=SR, output="sos")
    elif bas:
        sos = butter(ordre, bas, btype="high", fs=SR, output="sos")
    else:
        sos = butter(ordre, haut, btype="low", fs=SR, output="sos")
    return sosfilt(sos, x)


def temps(d):
    return np.arange(int(d * SR)) / SR


def poser(piste, x, t, gain=1.0, pan=0.0):
    """Ajoute un son mono sur la piste stereo a l'instant t."""
    i = int(t * SR)
    if i >= N or i + len(x) <= 0:
        return
    x = x[: N - i] * gain
    g, d = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
    piste[i:i + len(x), 0] += x * g * 1.414
    piste[i:i + len(x), 1] += x * d * 1.414


def bruit(d):
    return rng.uniform(-1, 1, int(d * SR))


# --------------------------------------------------------------------------
# Instruments
# --------------------------------------------------------------------------
def grosse_caisse():
    t = temps(0.42)
    f = 44 + 80 * np.exp(-t / 0.028)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.17)
    x[:150] += np.linspace(0.6, 0, 150)
    return np.tanh(1.6 * x)


def clap():
    x = np.zeros(int(0.3 * SR))
    for dt in (0.0, 0.011, 0.022):
        i, m = int(dt * SR), int(0.012 * SR)
        x[i:i + m] += rng.uniform(-1, 1, m) * np.exp(-np.arange(m) / (0.004 * SR))
    x += bruit(0.3) * np.exp(-temps(0.3) / 0.07) * 0.55
    return filtre(x, 900, 4200)


def charleston(ouvert=False):
    d = 0.16 if ouvert else 0.05
    return filtre(bruit(d) * np.exp(-temps(d) / (0.09 if ouvert else 0.022)), 7500)


def shaker():
    t = temps(0.09)
    env = np.minimum(1, t / 0.012) * np.exp(-t / 0.035)
    return filtre(bruit(0.09) * env, 4500, 11000)


def tambour(f0):
    """Tambour parlant : la hauteur monte pendant la frappe."""
    t = temps(0.3)
    f = f0 * (1 + 0.28 * (1 - np.exp(-t / 0.05)))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * np.exp(-t / 0.11)


def basse(f, d):
    t = temps(d)
    env = np.minimum(1, t / 0.006) * np.minimum(1, (d - t) / 0.03) * np.exp(-t / 0.5)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t)
    return np.tanh(1.8 * x * env) * 0.8


def accord(freqs, d):
    t = temps(d)
    x = np.zeros_like(t)
    for f in freqs:
        for det in (-0.004, 0.004):
            x += 2 * ((t * f * (1 + det)) % 1) - 1
    env = np.minimum(1, t / 0.35) * np.minimum(1, (d - t) / 0.3)
    return filtre(x * env / (2 * len(freqs)), haut=1400)


def kalimba(f):
    t = temps(0.6)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.04)) * np.exp(-t / 0.22)


def montee(d, f0=300, f1=6000):
    """Souffle qui monte (riser)."""
    x = bruit(d)
    out = np.zeros_like(x)
    pas = int(0.05 * SR)
    for i in range(0, len(x), pas):
        p = i / len(x)
        fc = f0 * (f1 / f0) ** p
        seg = filtre(x[max(0, i - 2048):i + pas], fc * 0.7, min(fc * 1.4, SR / 2 - 100))
        out[i:i + pas] = seg[-len(out[i:i + pas]):]
    return out * np.linspace(0.05, 1, len(x)) ** 2


# --------------------------------------------------------------------------
# Bruitages
# --------------------------------------------------------------------------
def toucher():
    t = temps(0.06)
    return 0.9 * np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.012) + 0.5 * bruit(0.06) * np.exp(-t / 0.004)


def envolee():
    x = bruit(0.45)
    t = temps(0.45)
    env = np.sin(np.pi * t / 0.45) ** 2
    return filtre(x, 600, 5000) * env


def bip():
    t = temps(0.16)
    x = np.sin(2 * np.pi * 1320 * t) * ((t < 0.06) | (t > 0.09))
    return x * np.exp(-t / 0.2) * 0.6


def pop():
    t = temps(0.08)
    f = 600 + 900 * t / 0.08
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.03)


def declencheur():
    return filtre(bruit(0.09) * np.exp(-temps(0.09) / 0.015), 1500) * 1.2


def balayage(d):
    t = temps(d)
    f = 380 * (4.5 ** (t / d))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) * 0.35


def tic():
    t = temps(0.03)
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.006)


def barre():
    return filtre(bruit(0.25), 2000, 8000) * np.exp(-temps(0.25) / 0.06)


def caisse():
    """Le « ding » de la caisse enregistreuse."""
    t = temps(1.3)
    x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / dd)
            for f, a, dd in ((2093, 1.0, 0.5), (2637, 0.6, 0.4), (4186, 0.25, 0.2)))
    return x * 0.5


def coup_sourd():
    t = temps(0.5)
    f = 50 + 70 * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18)


def scintille():
    t = temps(1.2)
    x = sum(np.sin(2 * np.pi * f * t) for f in (2640, 3520, 3960, 5280)) / 4
    return x * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * t)) * np.exp(-t / 0.5) * 0.35


def imprimante():
    t = temps(0.24)
    moteur = (2 * ((t * 118) % 1) - 1) * 0.5 + filtre(bruit(0.24), 300, 2500) * 0.6
    return moteur * np.sin(np.pi * t / 0.24) ** 0.5


def impact():
    t = temps(1.2)
    boum = np.sin(2 * np.pi * np.cumsum(48 + 60 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.35)
    crash = filtre(bruit(1.2), 3000) * np.exp(-t / 0.45) * 0.45
    return boum + crash


def chute():
    """La basse qui tombe sous le logo final."""
    t = temps(1.6)
    f = 75 * (0.42 ** (t / 1.6))
    return np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t / 0.9)


# --------------------------------------------------------------------------
# La musique
# --------------------------------------------------------------------------
def coupe(t):
    """Vrai pendant un titre d'acte (la batterie s'arrete une demi-seconde)."""
    return any(a <= t < a + 0.5 for a in TITRES) or t >= 35.5


def musique():
    m = np.zeros((N, 2))
    gc, cl, ch, cho, sh = grosse_caisse(), clap(), charleston(), charleston(True), shaker()
    seize = TEMPS / 4
    swing = 0.018
    # progression : la mineur, fa, do, sol (une mesure de 2 s chacune)
    racines = [55.0, 43.65, 65.41, 49.0]
    accords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66)]
    penta = [440.0, 523.25, 587.33, 659.25, 783.99]
    riff = [(0, 3), (3, 2), (6, 4), (10, 3), (14, 1), (16, 0), (19, 2), (22, 3), (27, 4), (30, 2)]
    tambours = [(3, 170), (6, 200), (11, 170), (14, 230), (19, 170), (22, 200), (27, 150), (30, 230)]
    lignes_basse = [(0, 0.3, 1), (3, 0.2, 1), (6, 0.25, 1.5), (10, 0.2, 2), (14, 0.3, 1),
                    (16, 0.3, 1), (19, 0.2, 1), (22, 0.25, 1.5), (26, 0.2, 2), (30, 0.2, 1.5)]

    for mesure in range(int(DUREE / 2) + 1):
        t0 = mesure * 2.0
        r = mesure % 4
        intro = t0 < 2.0
        calme = CALME[0] <= t0 < CALME[1]
        # accords tout du long, plus forts quand la musique respire
        poser(m, accord(accords[r], 2.0), t0, 0.22 if calme else 0.11)
        for k in range(32):
            t = t0 + k * seize + (swing if k % 2 else 0)
            if t >= DUREE or coupe(t):
                continue
            # shaker partout
            poser(m, shaker(), t, 0.10 * (1.0 if k % 2 == 0 else 0.6), 0.35)
            if intro:
                if k % 4 == 0:
                    poser(m, filtre(gc, haut=180), t, 0.5)
                continue
            if calme:
                if k == 0:
                    poser(m, filtre(gc, haut=220), t, 0.6)
                continue
            if k % 4 == 0:
                poser(m, gc, t, 0.95)
            if k % 8 == 4:
                poser(m, cl, t, 0.5, -0.1)
            poser(m, ch, t, (0.13, 0.06, 0.1, 0.06)[k % 4], 0.3)
            if k % 4 == 2:
                poser(m, cho, t, 0.08, -0.3)
        if not intro:
            for k, f in tambours:
                t = t0 + k * seize
                if not coupe(t):
                    poser(m, tambour(f), t, 0.22, -0.4)
            for k, dur, mult in lignes_basse:
                t = t0 + k * seize
                if not coupe(t) and not calme:
                    poser(m, basse(racines[r] * mult, dur), t, 0.42)
            if mesure % 2 == 1 or calme:
                for k, i in riff:
                    t = t0 + k * seize
                    if not coupe(t):
                        poser(m, kalimba(penta[i]), t, 0.13, 0.25)
    # les montees : avant le logo et avant le retour apres la borne
    poser(m, montee(1.9), 0.1, 0.18)
    poser(m, montee(1.9, 400, 8000), CALME[1] - 1.9, 0.16)
    m[int(35.5 * SR):] *= np.linspace(1, 0, N - int(35.5 * SR))[:, None]
    return m


def bruitages():
    s = np.zeros((N, 2))
    for t in TOUCHERS:
        poser(s, toucher(), t, 0.5)
    for t in ENVOLEES:
        poser(s, envolee(), t - 0.15, 0.22)
    for t in BIPS:
        poser(s, bip(), t, 0.35)
    for t in POPS:
        poser(s, pop(), t, 0.22)
    poser(s, declencheur(), DECLENCHEUR, 0.6)
    poser(s, balayage(BALAYAGE[1] - BALAYAGE[0]), BALAYAGE[0], 0.4)
    for t in COMPTEUR:
        poser(s, tic(), t, 0.3)
    poser(s, barre(), BARRE, 0.35)
    poser(s, coup_sourd(), TAMPON, 0.7)
    poser(s, caisse(), TAMPON + 0.02, 0.45)
    for t in SCINTILLE:
        poser(s, scintille(), t, 0.6)
    for t in IMPRIMANTE:
        poser(s, imprimante(), t, 0.4)
    for t in TITRES:
        poser(s, impact(), t, 0.55)
    poser(s, impact(), IMPACT_FIN, 0.6)
    poser(s, chute(), CHUTE, 0.6)
    for t in MOTS_FIN:
        poser(s, coup_sourd(), t, 0.5)
    # l'accroche : les photos qui defilent, de plus en plus lentement
    t = 0.05
    while t < 1.3:
        poser(s, tic(), t, 0.12)
        t += 0.03 + 0.12 * (t / 1.3) ** 2
    return s


def voix():
    v = np.zeros(N)
    for nom, t in VOIX:
        with wave.open(str(ICI / "voix" / f"{nom}.wav")) as w:
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
        a = a / (np.abs(a).max() + 1e-9) * 0.85
        a = filtre(a, 90)  # enleve le grave inutile
        i = int(t * SR)
        a = a[: N - i]
        v[i:i + len(a)] += a
    return v


def main():
    m, s, v = musique(), bruitages(), voix()
    # la musique baisse quand la voix parle
    env = np.abs(v)
    lisse = np.convolve(env, np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
    actif = np.clip(lisse / 0.05, 0, 1)
    gain = 1 - 0.55 * actif
    mix = m * 0.9 * gain[:, None] + s + np.stack([v, v], axis=1) * 1.0
    # plus fort, sans saturer : normalisation puis compression douce
    mix = mix / (np.abs(mix).max() + 1e-9)
    mix = np.tanh(2.2 * mix) / np.tanh(2.2) * 0.95
    sortie = ICI / "son-motion-design.wav"
    wavfile.write(sortie, SR, (mix * 32767).astype(np.int16))
    print(f"{sortie}  {DUREE:.1f} s, {SR} Hz stereo")


if __name__ == "__main__":
    main()
