# -*- coding: utf-8 -*-
"""Pub MyFace avec Higgsfield : preparation (fiches des personnages, puis images de depart).

Personnages inventes par l'IA (aucune vraie personne, aucun client). Voir scenario.md.
Chaque generation coute des credits : lancer une etape a la fois, apres accord.

    python marketing/motion-design/higgsfield-pub/generer_preparation.py fiches
    python marketing/motion-design/higgsfield-pub/generer_preparation.py plans
    python marketing/motion-design/higgsfield-pub/generer_preparation.py plans K3      -> un seul plan
"""

import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
FICHES, PLANS = ICI / "fiches", ICI / "plans"

# Soul 2.0 : seul modele d'image ouvert au forfait gratuit (0,12 credit), une seule image de reference
MODELE = "text2image_soul_v2"
# plans : Seedream 5.0 Flash (0,5 credit), jusqu'a 10 references, garde les visages et la borne
MODELE_PLANS = "seedream_5_0_flash"
STYLE_FICHES = "fafd3087-0d0f-4fb1-9af6-91b7d304687c"      # preset Soul « Warm ambient »
STYLE = ("full-frame photorealistic photograph printed edge to edge, natural skin texture, real people, Canon 35mm look, "
         "soft warm evening light")
FOND_FICHE = ("full body, standing, facing the camera, neutral warm beige studio backdrop, even soft light, "
              "character reference sheet photo")

FICHES_PERSOS = {
    "maries": ("Awa and Ismael, the bride and groom, standing side by side holding hands. Awa, the bride: Ivorian woman about 28, dark brown skin, elegant, gentle smile, braided updo with a "
            "small delicate tiara, white lace wedding gown with long sleeves, small gold earrings, bouquet of "
            "white and orange roses. Ismael, the groom: Ivorian man about 30, tall, dark brown skin, short hair, neatly trimmed beard, "
               "royal blue tailored three-piece suit, white shirt, orange bow tie, white rose boutonniere"),
    "aya": ("Tantie Aya, a wedding guest: Ivorian woman about 55, dark brown skin, plump, big warm laugh, bright red "
            "head wrap tied in a large knot, long dress in blue and orange African wax print fabric, gold hoop "
            "earrings, a red silk scarf in her hand"),
    "yann": ("Yann, a young wedding guest: Ivorian man about 24, slim, dark brown skin, short twisted hair, "
             "friendly grin, light beige linen shirt, dark trousers, holding a plain black smartphone"),
    "photographe": ("the wedding photographer: Ivorian man about 35, dark brown skin, short beard, all black "
                    "clothes, camera strap, professional black DSLR camera with a flash on top, no brand names"),
}

BORNE = ("a tall white freestanding photo kiosk with a rounded white body, a large glowing white circular light "
         "ring on top, a small camera under the ring, a screen in the middle and a print slot near the bottom")
SALLE = ("an evening wedding reception hall in Abidjan, white drapes, white and orange flower arrangements, warm "
         "string lights, round tables with white tablecloths")

# plan -> (personnages en reference, autres references, description)
PLANS_DEPART = {
    "K1": (["maries"], [],
           f"{SALLE}. Wide shot down the aisle: the bride Awa and the groom Ismael walk in hand in hand, smiling; "
           "guests stand on both sides and clap. Same faces and outfits as the reference photos."),
    "K2": (["aya", "photographe"], [],
           f"{SALLE}, dance floor. The photographer in the foreground, seen from the side, shoots with his camera, "
           "his flash firing; behind him Tantie Aya dances joyfully, waving her red scarf over her head. "
           "Same faces and outfits as the reference photos."),
    "K3": (["aya"], ["borne"],
           f"Near the entrance of {SALLE}. Tantie Aya (the woman of the first reference photo) stands in front of the white photo kiosk of the "
           "second reference image (exact same kiosk: white body, round light ring on top), smiling at it for a selfie. "
           f"Camera behind her shoulder at three quarters: the kiosk screen is NOT visible, only its white back "
           "edge and glowing ring. Same face and outfit as the reference photo."),
    "K5": (["aya"], ["borne"],
           f"Near the entrance of {SALLE}, the white photo kiosk of the second reference image behind her, slightly out of focus. Tantie Aya holds up a freshly printed 10x15 photo with both hands, the back of the "
           "print faces the camera (plain white paper), she laughs with delight. Same face and outfit."),
    "K6": (["yann"], [],
           f"At a round table in {SALLE}. Yann sits and holds his smartphone up toward a small white folded "
           "table card standing on the tablecloth, scanning it. The phone screen faces away from the camera. "
           "Same face and outfit as the reference photo."),
    "K8": (["yann"], [],
           f"In {SALLE}. Yann shows his smartphone to two friends at the table, the screen faces them and away "
           "from the camera, all three laugh; in the soft background the bride Awa and the groom Ismael dance. "
           "Same faces and outfits as the reference photos."),
}


def generer(modele, prompt, sortie, references=(), **params):
    cmd = [shutil.which("higgsfield") or "higgsfield", "generate", "create", modele, "--prompt", prompt, "--wait", "--json"]
    for r in references:
        cmd += ["--image", str(r)]
    for k, v in params.items():
        cmd += [f"--{k}", str(v)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("ECHEC", sortie.name, r.stderr.strip()[:300])
        return None
    jobs = json.loads(r.stdout)
    job = jobs[0] if isinstance(jobs, list) else jobs
    url = _premiere_url(job)
    if not url:
        print("PAS D'URL", sortie.name, json.dumps(job)[:300])
        return None
    urllib.request.urlretrieve(url, sortie)
    print("ok", sortie.name)
    return sortie


def _premiere_url(o):
    if isinstance(o, str) and o.startswith("http") and any(e in o.lower() for e in (".png", ".jpg", ".jpeg", ".webp", ".mp4")):
        return o
    if isinstance(o, dict):
        for k in ("result_url", "url", "results", "result", "outputs", "output", "media"):
            if k in o:
                u = _premiere_url(o[k])
                if u:
                    return u
        for v in o.values():
            u = _premiere_url(v)
            if u:
                return u
    if isinstance(o, list):
        for v in o:
            u = _premiere_url(v)
            if u:
                return u
    return None


def main():
    etape = sys.argv[1]
    choix = sys.argv[2:]
    if etape == "fiches":
        FICHES.mkdir(exist_ok=True)
        for nom, desc in FICHES_PERSOS.items():
            if choix and nom not in choix:
                continue
            generer(MODELE, f"{desc}. {FOND_FICHE}. {STYLE}", FICHES / f"{nom}.png",
                    aspect_ratio="9:16", quality="1.5k", style_id=STYLE_FICHES)
    elif etape == "plans":
        PLANS.mkdir(exist_ok=True)
        for k, (persos, autres, desc) in PLANS_DEPART.items():
            if choix and k not in choix:
                continue
            refs = [FICHES / f"{p}.png" for p in persos] + [ICI / "refs" / f"{a}.png" for a in autres]
            generer(MODELE_PLANS, f"{desc} Vertical 9:16 cinematic frame. {STYLE}", PLANS / f"{k}.png", refs,
                    aspect_ratio="9:16", resolution="2k")




# Corrections du 29/10 apres relecture des images de depart (incoherences relevees) :
# K5 : le tirage montre la danse de K2 ; ecran de la borne eteint.
# K3 : meme borne que la nouvelle K5.  K6 : chevalet vu de dos.  K8 : les maries de la fiche.
PLANS_DEPART["K5"] = (["aya"], ["borne", "../plans/K2"],
    f"Near the entrance of {SALLE}. Tantie Aya (woman of the first reference photo, same face, red head wrap and "
    "dress) stands in front of the white photo kiosk of the second reference image, whose screen is turned off "
    "(black). She laughs with delight and holds up toward the camera a freshly printed 10x15 photo: the print "
    "shows exactly the picture of the third reference image (her dancing with her red scarf on the dance floor).")
PLANS_DEPART["K3"] = (["aya"], ["../plans/K5"],
    f"Near the entrance of {SALLE}. Tantie Aya (woman of the first reference photo, same face and outfit) stands "
    "in front of the exact same white photo kiosk as in the second reference image (same shape, same light ring, "
    "same place). Her hands are empty and relaxed at her sides: she holds nothing, no phone. She simply poses and "
    "smiles at the small camera of the kiosk under the light ring, for the kiosk's selfie. Camera behind her "
    "shoulder at three quarters: the kiosk screen is not visible, only the side of the kiosk and its glowing ring.")
PLANS_DEPART["K6"] = (["yann"], [],
    f"At a round table in {SALLE}. Yann (man of the reference photo, same face and beige linen shirt) sits and "
    "points his smartphone at a small white folded table card standing on the tablecloth, to scan it; the printed "
    "side of the card faces Yann, the camera only sees the plain white back of the card, with no writing. The "
    "phone screen faces Yann, away from the camera.")
PLANS_DEPART["K8"] = (["yann", "maries"], [],
    f"In {SALLE}. Yann (man of the first reference photo, same face and beige linen shirt) shows his smartphone "
    "to two friends at the table, the screen faces them and away from the camera, all three laugh. In the soft "
    "background the bride and groom of the second reference photo dance: same white lace gown, the groom in the "
    "same royal blue three-piece suit with orange bow tie.")


if __name__ == "__main__":
    main()
