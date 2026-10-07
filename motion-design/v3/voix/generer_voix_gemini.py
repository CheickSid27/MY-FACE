# -*- coding: utf-8 -*-
"""Voix off v3 avec Gemini (Google AI Studio) : une voix de synthese naturelle.

La cle API se colle dans motion-design/v3/voix/cle-google.txt (fichier hors GitHub)
ou dans la variable d'environnement GEMINI_API_KEY. Elle n'est jamais affichee.

    python motion-design/v3/voix/generer_voix_gemini.py --essai
        -> voix/essais/<Voix>.wav : deux phrases lues par 8 voix, pour choisir a l'oreille
    python motion-design/v3/voix/generer_voix_gemini.py --voix Sulafat
        -> voix/prise-Sulafat.wav : tout le texte en une seule prise (ton continu),
           puis decoupe en N01.wav a N12.wav (48 kHz mono) pour sons_v3.py
    python motion-design/v3/voix/generer_voix_gemini.py --voix Sulafat --phrase-par-phrase
        -> une requete par phrase (si le decoupage de la prise unique echoue)

Le texte et les temps sont ceux de la v2 : motion-design/v2/voix/texte.txt.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

ICI = Path(__file__).resolve().parent
TEXTE = ICI.parent.parent / "v2" / "voix" / "texte.txt"
CLE = ICI / "cle-google.txt"
ESSAIS = ICI / "essais"
SR = 48000
MODELES = ["gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"]
URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"

# 4 voix de femme, 4 voix d'homme, choisies pour une pub chaleureuse
VOIX_ESSAI = {
    "Sulafat": "femme, chaleureuse",
    "Zephyr": "femme, lumineuse",
    "Aoede": "femme, legere",
    "Laomedeia": "femme, enjouee",
    "Puck": "homme, enjoue",
    "Achird": "homme, amical",
    "Sadachbia": "homme, vif",
    "Charon": "homme, pose",
}

CONSIGNES = """# PROFIL
Voix off d'une publicite de 50 secondes pour MyFace, une application qui retrouve
les photos d'un evenement (mariage, bapteme, soiree) grace a la reconnaissance faciale.
Public : les invites des evenements a Abidjan, en Cote d'Ivoire.

# CONSIGNES DE JEU
- Francais naturel et fluide, comme quelqu'un qui raconte a un ami, avec le sourire.
- Jamais robotique, jamais de lecture appuyee ni de ton de presentateur force.
- Les trois premieres phrases : ton pose et complice, on decrit un probleme que tout le monde connait.
- A partir de « Avec MyFace, c'est fini » : plus d'energie, enthousiaste, rythme vif mais bien articule.
- La derniere phrase : la signature de la marque, posee et confiante.
- « MyFace » se prononce a l'anglaise : « maille-feyce ». « IA » se dit « i-a ».
- Un silence d'une seconde entre chaque phrase.
- Ne lis pas ces consignes : lis uniquement le texte qui suit.

# TEXTE
"""


def lire_cle():
    cle = os.environ.get("GEMINI_API_KEY", "").strip()
    if not cle and CLE.exists():
        for l in CLE.read_text(encoding="utf-8-sig").splitlines():
            if l.strip() and not l.lstrip().startswith("#"):
                cle = l.strip()
                break
    if not cle:
        sys.exit(f"Pas de cle API : colle-la dans {CLE} (ligne sans #), puis relance.")
    return cle


def phrases():
    lignes = []
    for l in TEXTE.read_text(encoding="utf-8").splitlines():
        if not l.strip() or l.startswith("#"):
            continue
        ident, debut, fin, _, texte = l.split("|", 4)
        lignes.append((ident, float(debut), float(fin), texte.replace("{MYFACE}", "MyFace")))
    return lignes


def generer(cle, voix, texte):
    """Une requete Gemini : renvoie l'audio en float 48 kHz mono."""
    corps = json.dumps({
        "contents": [{"parts": [{"text": texte}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voix}}},
        },
    }).encode("utf-8")
    for modele in MODELES:
        for essai in range(5):
            req = urllib.request.Request(URL.format(modele), data=corps, method="POST", headers={
                "Content-Type": "application/json", "x-goog-api-key": cle})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    rep = json.load(r)
                break
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")
                if e.code == 429:                      # quota par minute : on attend et on reessaie
                    m = re.search(r'"retryDelay":\s*"(\d+)', detail)
                    attente = int(m.group(1)) + 2 if m else 30 * (essai + 1)
                    if "PerDay" in detail or "per day" in detail.lower():
                        sys.exit("Quota gratuit du jour atteint : reessaie demain (ou plus tard).")
                    print(f"  quota atteint, j'attends {attente} s...")
                    time.sleep(attente)
                    continue
                if e.code == 404:                      # modele indisponible : on passe au suivant
                    rep = None
                    break
                if "API_KEY_INVALID" in detail or e.code in (401, 403):
                    sys.exit("Cle API refusee par Google : verifie-la dans cle-google.txt.")
                sys.exit(f"Erreur Google {e.code} : {detail[:400]}")
        else:
            sys.exit("Toujours bloque par le quota apres 5 essais : reessaie plus tard.")
        if rep is None:
            continue
        try:
            parts = rep["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError):
            sys.exit(f"Reponse sans audio : {json.dumps(rep)[:400]}")
        donnees, taux = b"", 24000
        for p in parts:
            if "inlineData" in p:
                donnees += base64.b64decode(p["inlineData"]["data"])
                m = re.search(r"rate=(\d+)", p["inlineData"].get("mimeType", ""))
                taux = int(m.group(1)) if m else taux
        if not donnees:
            sys.exit(f"Reponse sans audio : {json.dumps(rep)[:400]}")
        a = np.frombuffer(donnees, dtype="<i2").astype(float) / 32768
        return resample_poly(a, SR, taux) if taux != SR else a
    sys.exit("Aucun modele de voix Gemini disponible avec cette cle.")


def ecrire(chemin, a):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype("<i2").tobytes())


def lire(chemin):
    with wave.open(str(chemin)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768


def decouper(a, textes):
    """Coupe une prise en phrases : choisit les silences qui donnent a chaque phrase
    une duree proche de ce qu'annonce son nombre de lettres (programmation dynamique),
    en preferant les silences longs. Un « ? » suivi d'une pause ne trompe donc pas."""
    n = len(textes)
    pas = int(0.01 * SR)
    env = np.sqrt(np.convolve(a ** 2, np.ones(2 * pas) / (2 * pas), mode="same"))[::pas]
    parle = env > max(0.004, 0.05 * np.percentile(env, 95))
    idx = np.flatnonzero(parle)
    if not len(idx):
        raise ValueError("prise silencieuse")
    cands, i = [], idx[0]
    while i <= idx[-1]:
        if parle[i]:
            i += 1
            continue
        j = i
        while j <= idx[-1] and not parle[j]:
            j += 1
        if j - i >= 20:                                   # silences de 0,2 s et plus
            cands.append((j - i, i, j))
        i = j
    if len(cands) < n - 1:
        raise ValueError(f"{len(cands) + 1} morceaux trouves pour {n} phrases")
    poids = np.array([len(t) for t in textes], float)
    poids /= poids.sum()
    parole = (idx[-1] + 1 - idx[0]) - sum(sorted(c[0] for c in cands)[-(n - 1):])
    attendu = poids * max(parole, 1)
    bonus = [0.8 * min(c[0] / 100, 1.2) for c in cands]

    def cout(d, f, k):
        return np.log(max(f - d, 1) / attendu[k]) ** 2

    C, INF = len(cands), float("inf")
    dp = np.full((n - 1, C), INF)
    prec = np.zeros((n - 1, C), int)
    for j in range(C):
        dp[0, j] = cout(idx[0], cands[j][1], 0) - bonus[j]
    for k in range(1, n - 1):
        for j in range(k, C):
            vals = [dp[k - 1, i] + cout(cands[i][2], cands[j][1], k) for i in range(k - 1, j)]
            m = int(np.argmin(vals))
            dp[k, j] = vals[m] - bonus[j]
            prec[k, j] = k - 1 + m
    fins = [dp[n - 2, j] + cout(cands[j][2], idx[-1] + 1, n - 1) for j in range(C)]
    choix = [int(np.argmin(fins))]
    for k in range(n - 2, 0, -1):
        choix.append(int(prec[k, choix[-1]]))
    coupes = [cands[j] for j in reversed(choix)]
    bornes = [idx[0]] + [x for _, d, f in coupes for x in (d, f)] + [idx[-1] + 1]
    morceaux = []
    for k in range(n):
        d, f = bornes[2 * k], bornes[2 * k + 1]
        morceaux.append(a[max(0, d * pas - int(0.03 * SR)): f * pas + int(0.12 * SR)])
    return morceaux, min(t[0] for t in coupes) * 0.01


def bilan(lignes, morceaux):
    print("\n  phrase   duree   place   ")
    for (ident, debut, fin, texte), m in zip(lignes, morceaux):
        d = len(m) / SR
        note = "" if d <= fin - debut else "  un peu long (sons_v3 resserre jusqu'a 15 %)"
        print(f"  {ident}    {d:4.1f} s  {fin - debut:4.1f} s{note}")
    ratios = [len(m) / SR / max(len(t), 1) for (_, _, _, t), m in zip(lignes, morceaux)]
    if max(ratios) / min(ratios) > 2.5:
        print("\n  ATTENTION : une phrase a une duree anormale, le decoupage est peut-etre faux.")
        print("  Relance avec --phrase-par-phrase si tu entends un melange.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--essai", action="store_true", help="deux phrases lues par 8 voix")
    p.add_argument("--voix", default="Sulafat")
    p.add_argument("--phrase-par-phrase", action="store_true")
    p.add_argument("--decouper", metavar="PRISE.wav", help="redecouper une prise deja generee (sans requete)")
    args = p.parse_args()
    lignes = phrases()

    if args.decouper:
        morceaux, _ = decouper(lire(Path(args.decouper)), [t for *_, t in lignes])
        for (ident, *_), m in zip(lignes, morceaux):
            ecrire(ICI / f"{ident}.wav", m)
        bilan(lignes, morceaux)
        return

    cle = lire_cle()
    if args.essai:
        texte = CONSIGNES + lignes[3][3] + "\n\n" + lignes[4][3]
        for voix, genre in VOIX_ESSAI.items():
            ecrire(ESSAIS / f"{voix}.wav", generer(cle, voix, texte))
            print(f"  {voix:10s} ({genre}) ok")
        print(f"\nEcoute les fichiers de {ESSAIS} et choisis ta voix.")
        return

    if args.phrase_par_phrase:
        morceaux = []
        for ident, _, _, texte in lignes:
            a = generer(cle, args.voix, CONSIGNES + texte)
            ecrire(ICI / f"{ident}.wav", a)
            morceaux.append(a)
            print(f"  {ident} ok")
    else:
        prise = generer(cle, args.voix, CONSIGNES + "\n\n".join(t for *_, t in lignes))
        ecrire(ICI / f"prise-{args.voix}.wav", prise)
        print(f"  prise unique : {len(prise) / SR:.1f} s")
        morceaux, plus_court = decouper(prise, [t for *_, t in lignes])
        for (ident, *_), m in zip(lignes, morceaux):
            ecrire(ICI / f"{ident}.wav", m)
        print(f"  decoupee en {len(lignes)} phrases (plus petit silence entre deux phrases : {plus_court:.2f} s)")
    bilan(lignes, morceaux)
    print("\nEnsuite : python motion-design/v3/sons_v3.py, puis assembler_v3.ps1")


if __name__ == "__main__":
    main()
