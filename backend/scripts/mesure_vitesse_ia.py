"""Mesure la vitesse de l'IA de reconnaissance faciale, sans base de donnees.

Analyse un dossier de photos avec InsightFace (buffalo_l), comme l'indexation reelle
(services/face_recognition.py), et chronometre :
- le chargement du modele (le demarrage a froid d'un serveur) ;
- l'analyse de chaque photo (decodage + detection + empreinte de chaque visage) ;
- la recherche d'un selfie (un seul visage).
Deux reglages : les 5 modeles charges aujourd'hui, et seulement les 2 utiles
(detection + reconnaissance). Rien n'est ecrit nulle part.

    python scripts/mesure_vitesse_ia.py CUDAExecutionProvider,CPUExecutionProvider /photos
    THREADS=4 python scripts/mesure_vitesse_ia.py CPUExecutionProvider /photos
"""

import glob
import os
import statistics
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort
from insightface.app import FaceAnalysis

# THREADS=4 : limite les calculs a 4 fils, comme un serveur a 4 processeurs (sinon
# onnxruntime en lance autant que la machine hote en a, meme dans un conteneur limite)
if os.environ.get("THREADS"):
    _n = int(os.environ["THREADS"])
    cv2.setNumThreads(_n)
    _Session = ort.InferenceSession

    class _SessionLimitee(_Session):
        def __init__(self, chemin, sess_options=None, providers=None, **kw):
            so = sess_options or ort.SessionOptions()
            so.intra_op_num_threads = _n
            so.inter_op_num_threads = 1
            super().__init__(chemin, sess_options=so, providers=providers, **kw)

    ort.InferenceSession = _SessionLimitee


# DEMI=1 : photos decodees a moitie de leur taille (4 fois moins de pixels a lire)
LECTURE = cv2.IMREAD_REDUCED_COLOR_2 if os.environ.get("DEMI") else cv2.IMREAD_COLOR


def mesurer(providers, images, modules, tours):
    t0 = time.perf_counter()
    app = FaceAnalysis(name="buffalo_l", providers=providers, allowed_modules=modules)
    app.prepare(ctx_id=0, det_size=(640, 640))
    chargement = time.perf_counter() - t0
    actifs = set()
    for m in app.models.values():
        actifs.update(m.session.get_providers())
    premiere = cv2.imdecode(np.frombuffer(images[0], np.uint8), cv2.IMREAD_COLOR)
    t0 = time.perf_counter()
    app.get(premiere)
    premier_appel = time.perf_counter() - t0
    durees, visages = [], 0
    for _ in range(tours):
        for brut in images:
            t0 = time.perf_counter()
            img = cv2.imdecode(np.frombuffer(brut, np.uint8), LECTURE)
            faces = app.get(img)
            durees.append(time.perf_counter() - t0)
            visages += len(faces)
    # le selfie : un visage seul, recadre comme un selfie de telephone (720 x 960)
    faces = app.get(premiere)
    x1, y1, x2, y2 = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])).bbox
    cx, cy, cote = (x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) * 2.2
    h, w = premiere.shape[:2]
    selfie = premiere[int(max(0, cy - cote * 0.65)):int(min(h, cy + cote * 0.65)),
                      int(max(0, cx - cote / 2)):int(min(w, cx + cote / 2))]
    selfie = cv2.resize(selfie, (720, 960))
    s = []
    for _ in range(10):
        t0 = time.perf_counter()
        app.get(selfie)
        s.append(time.perf_counter() - t0)
    moy = statistics.mean(durees)
    return {
        "actifs": ",".join(sorted(p.replace("ExecutionProvider", "") for p in actifs)),
        "chargement": chargement, "premier": premier_appel, "moyenne": moy,
        "mediane": statistics.median(durees), "visages": visages / len(durees),
        "selfie": statistics.median(s), "mille": 1000 * moy / 60,
    }


def main():
    providers = sys.argv[1].split(",")
    dossier = sys.argv[2]
    tours = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    fichiers = sorted(glob.glob(os.path.join(dossier, "*.jpg")) + glob.glob(os.path.join(dossier, "*.jpeg")))
    images = [open(f, "rb").read() for f in fichiers]
    taille = cv2.imdecode(np.frombuffer(images[0], np.uint8), cv2.IMREAD_COLOR).shape
    print(f"{len(images)} photos x {tours} tours, premiere photo {taille[1]} x {taille[0]}, "
          f"{os.environ.get('THREADS') or os.cpu_count()} fils de calcul", flush=True)
    for nom, modules in (("5 modeles (aujourd'hui)", None), ("2 modeles (detection + reconnaissance)", ["detection", "recognition"])):
        r = mesurer(providers, images, modules, tours)
        print(f"\n[{nom}] moteur : {r['actifs']}")
        print(f"  chargement du modele : {r['chargement']:.1f} s ; premier appel : {r['premier']:.2f} s")
        print(f"  par photo : moyenne {r['moyenne']:.2f} s, mediane {r['mediane']:.2f} s, {r['visages']:.1f} visages/photo")
        print(f"  1 000 photos : {r['mille']:.1f} min")
        print(f"  recherche d'un selfie : {r['selfie'] * 1000:.0f} ms", flush=True)


if __name__ == "__main__":
    main()
