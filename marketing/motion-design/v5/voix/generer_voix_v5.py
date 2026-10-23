# -*- coding: utf-8 -*-
"""Voix off du motion design v5 (1 min, photographes), voix Gemini Zephyr comme les v3 et v4.

Reprend les outils de la v3 (marketing/motion-design/v3/voix/generer_voix_gemini.py) et la meme
cle API (marketing/motion-design/v3/voix/cle-google.txt). Le texte est dans v5/voix/texte.txt.

    python marketing/motion-design/v5/voix/generer_voix_v5.py
        -> v5/voix/prise-Zephyr.wav (le texte entier en une prise), puis V01.wav a V11.wav
    python marketing/motion-design/v5/voix/generer_voix_v5.py --phrase V07
        -> regenere seulement ces phrases (si l'une sonne mal)
    python marketing/motion-design/v5/voix/generer_voix_v5.py --decouper v5/voix/prise-Zephyr.wav
        -> redecoupe une prise deja generee, sans requete
"""

import argparse
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent.parent / "v3" / "voix"))
import generer_voix_gemini as G  # noqa: E402

VOIX = "Zephyr"

CONSIGNES = """# PROFIL
Voix off d'une video d'une minute pour MyFace, une application ivoirienne qui retrouve les
photos d'un evenement grace a la reconnaissance faciale. Cette video s'adresse aux photographes
d'evenement d'Abidjan, en Cote d'Ivoire, qui publient aujourd'hui leurs photos gratuitement sur
les reseaux sociaux.

# CONSIGNES DE JEU
- Meme voix et meme style que les videos precedentes de MyFace : francais naturel et fluide,
  chaleureux, avec le sourire, jamais robotique, jamais de ton de presentateur force.
- On vouvoie les photographes, comme un partenaire qui leur parle franchement.
- Les deux premieres phrases : ton complice, on decrit un probleme que tout photographe connait.
- A partir de « Avec MyFace » : plus d'energie, enthousiaste, rythme vif mais bien articule.
- La phrase « Et votre telephone vibre a chaque vente » : avec un petit sourire dans la voix.
- La derniere phrase : la signature de la marque, posee et confiante.
- « MyFace » se prononce a l'anglaise : « maille-feyce ». « MyFace Pro » : « maille-feyce pro ».
  « RAW » se dit « rô ». « QR code » se dit « ku-erre code ».
- Un silence d'une seconde entre chaque phrase.
- Ne lis pas ces consignes : lis uniquement le texte qui suit.

# TEXTE
"""


def lignes():
    out = []
    for l in (ICI / "texte.txt").read_text(encoding="utf-8").splitlines():
        if l.strip() and not l.startswith("#"):
            ident, scene, texte = l.split("|", 2)
            out.append((ident, scene, texte.replace("{MYFACE}", "MyFace")))
    return out


def ecrire_phrases(lg, morceaux):
    for (ident, _, _), m in zip(lg, morceaux):
        G.ecrire(ICI / f"{ident}.wav", m)
    total = 0.0
    for (ident, scene, texte), m in zip(lg, morceaux):
        d = len(m) / G.SR
        total += d
        print(f"  {ident}  {d:4.1f} s  {scene:16s} {texte[:60]}")
    print(f"  parole : {total:.1f} s")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phrase", action="append", help="regenerer seulement cette phrase (V01...)")
    p.add_argument("--decouper", metavar="PRISE.wav")
    args = p.parse_args()
    lg = lignes()
    textes = [t for *_, t in lg]

    if args.decouper:
        morceaux, _ = G.decouper(G.lire(Path(args.decouper)), textes)
        ecrire_phrases(lg, morceaux)
        return

    cle = G.lire_cle()
    if args.phrase:
        for ident, _, texte in lg:
            if ident in args.phrase:
                a = G.generer(cle, VOIX, CONSIGNES + texte)
                G.ecrire(ICI / f"{ident}.wav", a)
                print(f"  {ident}  {len(a) / G.SR:4.1f} s  regeneree")
        return

    prise = G.generer(cle, VOIX, CONSIGNES + "\n\n".join(textes))
    G.ecrire(ICI / f"prise-{VOIX}.wav", prise)
    print(f"  prise unique : {len(prise) / G.SR:.1f} s")
    morceaux, plus_court = G.decouper(prise, textes)
    print(f"  plus petit silence entre deux phrases : {plus_court:.2f} s")
    ecrire_phrases(lg, morceaux)


if __name__ == "__main__":
    main()
