# -*- coding: utf-8 -*-
"""Voix off du motion design v4 (2 min), voix Gemini Zephyr.

Reprend les outils de la v3 (marketing/motion-design/v3/voix/generer_voix_gemini.py) et la meme
cle API (marketing/motion-design/v3/voix/cle-google.txt). Le texte est dans v4/voix/texte.txt.

    python marketing/motion-design/v4/voix/generer_voix_v4.py
        -> v4/voix/prise-Zephyr.wav (le texte entier en une prise), puis L01.wav a L22.wav
    python marketing/motion-design/v4/voix/generer_voix_v4.py --phrase L07 --phrase L12
        -> regenere seulement ces phrases (si l'une sonne mal)
    python marketing/motion-design/v4/voix/generer_voix_v4.py --decouper v4/voix/prise-Zephyr.wav
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
Voix off d'une video de presentation de 2 minutes pour MyFace, une application ivoirienne
qui retrouve les photos d'un evenement (mariage, remise de diplomes, gala) grace a la
reconnaissance faciale. Elle sera vue par les invites, les organisateurs et un jury
d'innovation a Abidjan, en Cote d'Ivoire.

# CONSIGNES DE JEU
- Francais naturel et fluide, chaleureux, avec le sourire, comme quelqu'un qui raconte a un ami.
- Jamais robotique, jamais de ton de presentateur force.
- Les trois premieres phrases : ton pose et complice, on decrit un probleme que tout le monde connait.
- A partir de « Avec MyFace, c'est fini » : plus d'energie, enthousiaste, rythme vif mais bien articule.
- Les phrases sur le selfie jamais enregistre et sur le test a Abidjan : ton sincere, rassurant, credible.
- L'avant-derniere phrase, avec fierte. La derniere : la signature de la marque, posee et confiante.
- « MyFace » se prononce a l'anglaise : « maille-feyce ». « IA » se dit « i-a ». « IIT » se dit « i-i-te ».
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
    p.add_argument("--phrase", action="append", help="regenerer seulement cette phrase (L01...)")
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
