# -*- coding: utf-8 -*-
"""Les visages trouves par l'IA de MYFACE sur l'evenement de demonstration (photos Pexels).

Lecture seule, par l'API publique : liste des photos, puis pour chaque photo ses visages
(vignette + numero de personne). L'API ne donne pas la boite du visage : on la retrouve en
cherchant la vignette dans la photo locale (watched-photos/<evenement>), a plusieurs tailles.

    python marketing/motion-design/v6/visages_demo.py   -> v6/visages_demo.json
"""

import io
import json
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ICI = Path(__file__).resolve().parent
EVENT = "6b3391d9-e2eb-4942-990b-ac1353cd170e"
API = "https://app.myfaceci.online/api"
DEMO = ICI.parents[2] / "watched-photos" / EVENT
LARGEUR = 900


def lire(url):
    req = urllib.request.Request(url, headers={"User-Agent": "myface-motion/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def chercher(photo_gris, vignette_gris):
    """-> (score, x1, y1, cote) de la meilleure place de la vignette dans la photo."""
    meilleur = (-1, 0, 0, 0)
    cote = 24
    while cote < min(photo_gris.shape) * 0.9:
        v = cv2.resize(vignette_gris, (int(cote), int(cote)), interpolation=cv2.INTER_AREA)
        r = cv2.matchTemplate(photo_gris, v, cv2.TM_CCOEFF_NORMED)
        _, s, _, (x, y) = cv2.minMaxLoc(r)
        if s > meilleur[0]:
            meilleur = (s, x, y, cote)
        cote *= 1.06
    return meilleur


def main():
    photos = json.loads(lire(f"{API}/events/{EVENT}/photos?limit=200"))
    photos = photos.get("items", photos.get("photos", photos)) if isinstance(photos, dict) else photos
    res = {}
    for p in photos:
        nom = p["original_filename"]
        chemin = DEMO / nom
        if not chemin.exists():
            print("absente :", nom)
            continue
        im = ImageOps.exif_transpose(Image.open(chemin)).convert("L")
        ech = LARGEUR / im.width
        gris = np.asarray(im.resize((LARGEUR, round(im.height * ech)), Image.LANCZOS))
        faces = json.loads(lire(f"{API}/photos/{p['id']}/faces"))["faces"]
        out = []
        for f in faces:
            v = np.asarray(Image.open(io.BytesIO(lire(f["face_url"]))).convert("L"))
            s, x, y, c = chercher(gris, v)
            # retour aux pixels de la photo d'origine (redressee)
            out.append({"personne": f["cluster_id"], "score": round(float(s), 3),
                        "x1": round(x / ech), "y1": round(y / ech), "x2": round((x + c) / ech), "y2": round((y + c) / ech)})
        res[nom] = {"id": p["id"], "taille": [im.width, im.height], "visages": out}
        print(nom, [(o["personne"], o["score"]) for o in out])
    (ICI / "visages_demo.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
