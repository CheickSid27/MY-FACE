# -*- coding: utf-8 -*-
"""Bande son du motion design v4 (2 min).

- 0 a 11 s : l'ouverture de la v2 (nappe, coeur, papier, notifications), inchangee.
- Ensuite : le groove de la v2, sur toute la longueur, avec les coupures des titres et
  deux respirations (la borne qui monte, « une solution ivoirienne »).
- Les bruitages des scenes de la v2 sont recales sur le decoupage v4 (montage_v4.py) ;
  les nouvelles scenes ont les leurs, aux memes instants que leurs animations.
- La voix Zephyr (v4/voix/L*.wav), chaque phrase au debut de sa section.

    python motion-design/v4/sons_v4.py   -> motion-design/v4/son-motion-design-v4.wav
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
import montage_v4 as M  # noqa: E402

S = V2.S
SCENES, VOIX, DUREE = M.decoupage()
SR = S.SR
N = int(SR * DUREE)
S.DUREE, S.N, V2.DUREE, V2.N = DUREE, N, DUREE, N
rng = np.random.default_rng(44)
DEBUT = {nom: t for nom, t, _ in SCENES}
LONGUEUR = {nom: d for nom, _, d in SCENES}

# les scenes de la v2, avec leur debut et leur duree dans la v2
V2_SCENES = [("probleme_tas", 0, 4), ("probleme_groupe", 4, 4), ("probleme_perdu", 8, 3), ("logo", 11, 2),
             ("titre_scanne", 13, 0.5), ("accueil", 13.5, 3), ("titre_retrouve", 16.5, 0.5), ("galerie", 17, 3),
             ("visages", 20, 4.5), ("selfie", 24.5, 5), ("titre_repars", 29.5, 0.5), ("panier", 30, 4),
             ("borne_monte", 34, 2), ("borne_gros_plan", 36, 4), ("tirage_sort", 40, 2), ("qualite", 42, 4),
             ("fin", 46, 4)]


def v4(t2):
    """Un instant de la v2 -> le meme moment de la meme scene dans la v4."""
    for nom, d, lg in V2_SCENES:
        if d <= t2 < d + lg:
            return DEBUT[nom] + (t2 - d)
    return DEBUT["fin"] + (t2 - 46)


def a(nom, t):
    """Un instant local d'une scene -> l'instant dans le film."""
    return DEBUT[nom] + t


# --------------------------------------------------------------------------
# Musique
# --------------------------------------------------------------------------
TITRES = [DEBUT["titre_scanne"], DEBUT["titre_retrouve"], DEBUT["titre_repars"]]
CALMES = [(DEBUT["borne_monte"], DEBUT["borne_monte"] + LONGUEUR["borne_monte"]),
          (DEBUT["ivoirienne"], DEBUT["ivoirienne"] + LONGUEUR["ivoirienne"])]


def coupe(t):
    return any(x <= t < x + 0.5 for x in TITRES) or t >= DUREE - 0.5


def calme(t):
    return any(x <= t < y for x, y in CALMES)


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
    mesure, t0 = 0, V2.LOGO
    while t0 < DUREE:
        r = mesure % 4
        intro = t0 < V2.LOGO + 2.0
        S.poser(m, S.accord(accords[r], 2.0), t0, 0.22 if (calme(t0) or intro) else 0.11)
        for k in range(32):
            t = t0 + k * seize + (swing if k % 2 else 0)
            if t >= DUREE or coupe(t):
                continue
            S.poser(m, sh, t, 0.10 * (1.0 if k % 2 == 0 else 0.6), 0.35)
            if intro:
                continue
            if calme(t):
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
                if t < DUREE and not coupe(t) and not calme(t):
                    S.poser(m, S.tambour(f), t, 0.22, -0.4)
            for k, dur, mult in lignes_basse:
                t = t0 + k * seize
                if t < DUREE and not coupe(t) and not calme(t):
                    S.poser(m, S.basse(racines[r] * mult, dur), t, 0.42)
            if mesure % 2 == 1 or calme(t0):
                for k, i in riff:
                    t = t0 + k * seize
                    if t < DUREE and not coupe(t):
                        S.poser(m, S.kalimba(penta[i]), t, 0.13, 0.25)
        mesure += 1
        t0 += 2.0
    for _, fin in CALMES:
        S.poser(m, S.montee(1.9, 400, 8000), fin - 1.9, 0.16)
    debut_fondu = int((DUREE - 0.8) * SR)
    m[debut_fondu:] *= np.linspace(1, 0, N - debut_fondu)[:, None]
    return m


# --------------------------------------------------------------------------
# Bruitages
# --------------------------------------------------------------------------
def desintegration():
    """Le selfie qui part en morceaux : un souffle qui descend, granuleux."""
    d = 1.2
    t = S.temps(d)
    x = S.filtre(S.bruit(d), 1200, 9000) * np.exp(-t / 0.45)
    grains = (rng.uniform(0, 1, len(t)) > 0.985) * rng.uniform(-1, 1, len(t))
    return x * 0.7 + S.filtre(grains, 2500) * 0.8


def train(s, debut, fin, pas, gain):
    t = debut
    while t < fin:
        S.poser(s, S.tic(), t, gain)
        t += pas


def bruitages_v2(s):
    """Les bruitages des scenes reprises de la v2, recales."""
    S.poser(s, S.impact(), DEBUT["logo"], 0.75)
    S.poser(s, S.chute(), DEBUT["logo"] + 0.05, 0.45)
    S.poser(s, S.scintille(), DEBUT["logo"] + 0.4, 0.5)
    for t in V2.TOUCHERS:
        S.poser(s, S.toucher(), v4(t), 0.5)
    for t in V2.ENVOLEES:
        S.poser(s, S.envolee(), v4(t) - 0.15, 0.22)
    S.poser(s, S.bip(), v4(21.7), 0.35)
    for t in V2.POPS:
        S.poser(s, S.pop(), v4(t), 0.22)
    S.poser(s, S.declencheur(), v4(26.75), 0.6)
    S.poser(s, S.balayage(0.8), v4(26.85), 0.4)
    for t in V2.COMPTEUR:
        S.poser(s, S.tic(), v4(t), 0.3)
    S.poser(s, S.barre(), v4(30.6), 0.35)
    S.poser(s, S.coup_sourd(), v4(30.9), 0.7)
    S.poser(s, S.caisse(), v4(30.92), 0.45)
    for t in (34.9, 43.0):
        S.poser(s, S.scintille(), v4(t), 0.6)
    for t in V2.IMPRIMANTE:
        S.poser(s, S.imprimante(), v4(t), 0.4)
    long = S.filtre(S.bruit(1.5), 500, 6000) * np.sin(np.pi * S.temps(1.5) / 1.5) ** 2
    S.poser(s, long, v4(42.45), 0.25)
    for t in TITRES:
        S.poser(s, S.impact(), t, 0.55)
    S.poser(s, S.impact(), DEBUT["fin"], 0.6)
    S.poser(s, S.chute(), DEBUT["fin"] + 0.9, 0.6)
    for t in (1.2, 1.7, 2.2):
        S.poser(s, S.coup_sourd(), DEBUT["fin"] + t, 0.5)


def bruitages_nouveaux(s):
    # le depot des photos
    S.poser(s, S.scintille(), a("depot", 0.3), 0.4)
    for k in range(22):
        t0 = 0.35 + k * 0.155
        if k % 2 == 0:
            S.poser(s, S.envolee(), a("depot", t0), 0.10, rng.uniform(-0.6, 0.6))
        S.poser(s, S.pop(), a("depot", t0 + 0.85), 0.12, rng.uniform(-0.3, 0.3))
    S.poser(s, S.coup_sourd(), a("depot", 3.0), 0.4)
    # l'IA : balayage, detections, groupes
    S.poser(s, S.balayage(2.0), a("ia", 0.5), 0.3)
    for t in (1.05, 1.30):
        S.poser(s, S.bip(), a("ia", t), 0.35)
    for t in (1.35, 1.6):
        S.poser(s, S.pop(), a("ia", t), 0.2)
    S.poser(s, S.envolee(), a("ia", 3.5), 0.3)
    for i in range(2):
        for k in range(10):
            S.poser(s, S.pop(), a("ia", 3.6 + 0.7 + k * 0.09 + i * 0.05), 0.10, -0.4 if i == 0 else 0.4)
    S.poser(s, S.coup_sourd(), a("ia", 6.0), 0.5)
    # le selfie efface
    train(s, a("confiance", 0.3), a("confiance", 2.3), 0.12, 0.07)
    S.poser(s, S.pop(), a("confiance", 1.0), 0.2)
    S.poser(s, desintegration(), a("confiance", 2.55), 0.4)
    S.poser(s, S.coup_sourd(), a("confiance", 3.3), 0.6)
    S.poser(s, S.scintille(), a("confiance", 3.35), 0.45)
    S.poser(s, S.pop(), a("confiance", 3.7), 0.2)
    # paiement et telechargement
    for i in range(4):
        S.poser(s, S.pop(), a("telechargement", 0.1 + i * 0.12), 0.15, -0.5 + i * 0.33)
    S.poser(s, S.envolee(), a("telechargement", 0.75), 0.2)
    S.poser(s, S.caisse(), a("telechargement", 1.3), 0.35)
    S.poser(s, S.toucher(), a("telechargement", 3.3), 0.5)
    train(s, a("telechargement", 3.45), a("telechargement", 4.95), 0.1, 0.07)
    S.poser(s, S.scintille(), a("telechargement", 4.95), 0.5)
    for k in range(6):
        S.poser(s, S.pop(), a("telechargement", 5.0 + k * 0.1), 0.12)
    S.poser(s, S.coup_sourd(), a("telechargement", 5.4), 0.4)
    # sans smartphone, sans Mobile Money
    for t in (1.8, 2.5):
        S.poser(s, S.pop(), a("tirage_sort", t), 0.22)
    # photos offertes
    S.poser(s, S.envolee(), a("offertes", 0.0), 0.2)
    S.poser(s, S.toucher(), a("offertes", 0.95), 0.5)
    S.poser(s, S.pop(), a("offertes", 1.1), 0.25)
    S.poser(s, S.envolee(), a("offertes", 1.65), 0.2)
    S.poser(s, S.toucher(), a("offertes", 3.5), 0.5)
    S.poser(s, S.scintille(), a("offertes", 3.6), 0.6)
    for _ in range(14):
        S.poser(s, S.pop(), a("offertes", 3.6 + rng.uniform(0, 1.0)), 0.07, rng.uniform(-0.8, 0.8))
    S.poser(s, S.coup_sourd(), a("offertes", 3.9), 0.4)
    # le tableau de bord
    S.poser(s, S.envolee(), a("tableau", 0.0), 0.2)
    train(s, a("tableau", 0.6), a("tableau", 2.2), 0.1, 0.05)
    for k in range(7):
        S.poser(s, S.pop(), a("tableau", 1.0 + k * 0.12), 0.11)
    for k in range(4):
        S.poser(s, S.pop(), a("tableau", 2.0 + k * 0.25), 0.12)
        S.poser(s, S.bip(), a("tableau", 3.7 + k * 0.3), 0.18)
    S.poser(s, S.toucher(), a("tableau", 3.6), 0.5)
    # la preuve a Abidjan
    S.poser(s, S.pop(), a("preuve", 0.3), 0.25)
    S.poser(s, S.coup_sourd(), a("preuve", 0.4), 0.45)
    S.poser(s, S.pop(), a("preuve", 2.0), 0.2)
    train(s, a("preuve", 3.3), a("preuve", 4.2), 0.07, 0.09)
    S.poser(s, S.coup_sourd(), a("preuve", 4.2), 0.55)
    train(s, a("preuve", 5.0), a("preuve", 5.9), 0.09, 0.09)
    S.poser(s, S.coup_sourd(), a("preuve", 5.9), 0.55)
    S.poser(s, S.impact(), a("preuve", 6.4), 0.3)
    S.poser(s, S.pop(), a("preuve", 6.9), 0.2)
    # partout
    for t0 in (0.4, 1.1, 2.0, 2.9, 3.4, 3.8, 4.05, 4.3):
        S.poser(s, S.pop(), a("partout", t0), 0.18, rng.uniform(-0.5, 0.5))
    S.poser(s, S.coup_sourd(), a("partout", 5.0), 0.45)
    # une solution ivoirienne
    S.poser(s, S.impact(), a("ivoirienne", 0.2), 0.45)
    S.poser(s, S.scintille(), a("ivoirienne", 0.3), 0.4)
    for t in (0.9, 1.3):
        S.poser(s, S.coup_sourd(), a("ivoirienne", t), 0.45)
    S.poser(s, S.balayage(0.5), a("ivoirienne", 1.6), 0.15)
    for t in (2.6, 3.8):
        S.poser(s, S.coup_sourd(), a("ivoirienne", t), 0.3)


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
    m = V2.ouverture() + groove()
    s = V2.bruitages_ouverture()
    bruitages_v2(s)
    bruitages_nouveaux(s)
    v = voix()
    env = np.convolve(np.abs(v), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
    gain = 1 - 0.55 * np.clip(env / 0.05, 0, 1)
    mix = m * 0.85 * gain[:, None] + s * (1 - 0.35 * np.clip(env / 0.05, 0, 1))[:, None] + np.stack([v, v], axis=1)
    mix = mix / (np.abs(mix).max() + 1e-9)
    mix = np.tanh(2.2 * mix) / np.tanh(2.2) * 0.95
    sortie = ICI / "son-motion-design-v4.wav"
    wavfile.write(sortie, SR, (mix * 32767).astype(np.int16))
    print(f"{sortie}  {DUREE:.1f} s")


if __name__ == "__main__":
    main()
