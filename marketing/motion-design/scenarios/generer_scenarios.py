# -*- coding: utf-8 -*-
"""Voix des nouveaux scenarios de pub (marketing/motion-design/scenarios/scenarios.md).

Une requete Gemini par scenario (voix Zephyr, la voix de la marque). Le sketch de la
tantie est un dialogue a deux voix (Sulafat pour Tantie Aya, Puck pour Koffi), puis la
signature est dite par Zephyr. Meme cle API que la v3 (v3/voix/cle-google.txt).

    python marketing/motion-design/scenarios/generer_scenarios.py          -> scenarios/voix/S*.wav
    python marketing/motion-design/scenarios/generer_scenarios.py S2 S5    -> seulement ces scenarios
"""

import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "v3" / "voix"))
import generer_voix_gemini as G  # noqa: E402

VOIX = ICI / "voix"

JEU = """# CONSIGNES DE JEU
- Francais naturel et fluide, ton chaleureux d'Abidjan, avec le sourire. Jamais robotique.
- « MyFace » se prononce a l'anglaise : « maille-feyce ». « IA » se dit « i-a ».
- Respecte les points de suspension : petite pause. Une respiration entre les phrases.
- Ne lis pas ces consignes : lis uniquement le texte qui suit.
"""

SCENARIOS = {
    "S1-avez-vous-deja-vecu-ca": ("Zephyr", """# PROFIL
Publicite de 35 secondes. Debut : ton complice et un peu desabuse, on raconte un probleme
que tout le monde a vecu. A partir de « Avec MyFace » : enthousiaste, energique.
""", """Tu as déjà vécu ça ? La soirée était belle, le photographe a mitraillé toute la nuit...

Et le lendemain ? Rien. Ou alors cinq cents photos floues dans le groupe WhatsApp.

Tu passes une heure à te chercher... et tu ne te trouves même pas.

Avec MyFace, c'est terminé.

Tu scannes le QR code de la soirée, tu touches « Trouver mon visage »...

et notre intelligence artificielle te sort toutes tes photos, en qualité d'origine.

MyFace. Scanne, retrouve, repars avec."""),

    "S3-un-selfie": ("Zephyr", """# PROFIL
Publicite tres courte (15 secondes) pour un statut WhatsApp ou TikTok. Phrases courtes,
rythme vif, un peu de mystere au debut, puis une chute joyeuse.
""", """Un selfie...

Deux secondes...

Et toutes tes photos de la soirée sont là.

MyFace, l'intelligence artificielle qui te retrouve sur chaque photo.

Scanne, retrouve, repars avec."""),

    "S4-organisateurs": ("Zephyr", """# PROFIL
Publicite de 35 secondes pour les organisateurs d'evenements (vouvoiement). Ton
professionnel mais chaleureux, rassurant, sur un rythme pose.
""", """Vous organisez un mariage, une remise de diplômes, un gala ?

Vos invités repartent souvent sans leurs photos... et vous en entendez parler pendant des semaines.

Avec MyFace, chaque invité retrouve ses photos en scannant un QR code, grâce à notre intelligence artificielle de reconnaissance faciale.

Envie de faire plaisir ? Offrez-les : vos invités les reçoivent gratuitement, sans aucune page de paiement.

Et une borne peut même les imprimer sur place.

MyFace. Parlons de votre événement sur WhatsApp."""),

    "S5-la-borne": ("Zephyr", """# PROFIL
Publicite de 35 secondes sur la borne photo. Ton simple et rassurant au debut, puis de
plus en plus enjoue ; la derniere phrase avec fierte.
""", """Pas de smartphone ? Pas de souci.

À la borne MyFace, tu prends un selfie...

et l'intelligence artificielle retrouve toutes tes photos de la soirée.

Tu choisis, tu coches « Imprimer »...

tu paies en espèces : sept cents francs la photo, tirage compris.

Et en vingt secondes, ta photo sort. En vrai papier.

La borne MyFace. Personne ne repart les mains vides."""),

    "S6-photographes": ("Zephyr", """# PROFIL
Publicite de 35 secondes pour les photographes professionnels (vouvoiement). Ton direct,
complice, entre professionnels ; energique sur la fin.
""", """Photographes, combien de photos vous restent sur les bras après chaque événement ?

Avec MyFace, vous déposez vos photos, notre intelligence artificielle reconnaît chaque visage...

et vous envoyez un seul lien à vos invités.

Chacun retrouve ses photos avec un selfie, et paie directement par Mobile Money.

Vous vendez plus, sans trier, sans courir derrière vos clients.

MyFace. Ouvrez votre compte photographe."""),
}

# le sketch : deux voix dans une seule requete, puis la signature par Zephyr
SKETCH = "S2-tantie-aya"
SKETCH_JEU = """# PROFIL
Petit sketch comique de 30 secondes a Abidjan. Tantie Aya : femme d'une cinquantaine
d'annees, expressive, impatiente puis aux anges. Koffi : son neveu d'une vingtaine
d'annees, calme, un peu moqueur. Francais d'Abidjan naturel, avec le sourire.
Ne lis pas ces consignes ni les noms des personnages : joue seulement leurs repliques.
"""
SKETCH_TEXTE = """Aya: Koffi ! Toi qui es fort dans téléphone, trouve-moi ma photo du mariage là.
Koffi: Tantie, y a huit cents photos dans le groupe dèh...
Aya: Je veux celle où je danse avec mon foulard rouge !
Koffi: Attends... MyFace. On scanne le QR code... un selfie... voilà !
Aya: Ehhh ! Toutes mes photos ! Même celle-là où je ferme les yeux...
Koffi: Tantie, celle-là, on va la laisser."""
SKETCH_FIN = "MyFace. Un selfie, et l'IA retrouve toutes tes photos. Y a pas drap."
DEUX_VOIX = {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [
    {"speaker": "Aya", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Sulafat"}}},
    {"speaker": "Koffi", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}}},
]}}


def raccourcir(a):
    nz = np.flatnonzero(np.abs(a) > 0.01)
    return a[max(0, nz[0] - int(0.05 * G.SR)): nz[-1] + int(0.3 * G.SR)] if len(nz) else a


def main():
    choix = sys.argv[1:]
    cle = G.lire_cle()
    for nom, (voix, profil, texte) in SCENARIOS.items():
        if choix and nom.split("-")[0] not in choix:
            continue
        a = raccourcir(G.generer(cle, voix, profil + JEU + "\n# TEXTE\n" + texte))
        G.ecrire(VOIX / f"{nom}.wav", a)
        print(f"  {nom:28s} {len(a) / G.SR:5.1f} s")
    if not choix or SKETCH.split("-")[0] in choix:
        dialogue = raccourcir(G.generer(cle, None, SKETCH_JEU + "\n" + SKETCH_TEXTE, DEUX_VOIX))
        fin = raccourcir(G.generer(cle, "Zephyr", JEU + "\n# TEXTE\n" + SKETCH_FIN))
        a = np.concatenate([dialogue, np.zeros(int(0.6 * G.SR)), fin])
        G.ecrire(VOIX / f"{SKETCH}.wav", a)
        print(f"  {SKETCH:28s} {len(a) / G.SR:5.1f} s")


if __name__ == "__main__":
    main()
