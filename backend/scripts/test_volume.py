"""Test de volume : un tres gros evenement, pour savoir ou MYFACE casse.

Remplit la BASE DE TEST (myface_test, jamais Neon) avec un faux evenement de
N photos et leurs visages (vecteurs synthetiques : chaque invite a un visage
« moyen », ses photos en sont des variantes proches), puis mesure ce que fait
vraiment l'application :
- la galerie (1re et derniere page, meme requete que routers/photos.py) ;
- « Trouver mon visage » : compute_event_clusters (DBSCAN sur tous les
  visages, comme a chaque nouvelle photo indexee), temps et memoire ;
- le scan d'un selfie : meme requete pgvector que routers/faces.py.
Aucune image n'est creee (les vignettes de visage sont supposees deja faites,
comme depuis le 23/10) : on mesure la base et le calcul, pas le stockage.

    docker compose up -d db
    MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps -v "D:/MY FACE/backend:/app" -w /app \
        -e PYTHONPATH=/app backend python3 scripts/test_volume.py 2000 5000 10000
"""

import asyncio
import gc
import json
import resource
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.database import Base
from app.models.event import Event
from app.models.face_embedding import FaceEmbedding
from app.models.photo import IndexingStatus, Photo
from app.models.user import User, UserRole
from app.services.face_clusters import compute_event_clusters

settings = get_settings()
TEST_URL = settings.test_database_url or settings.database_url.rsplit("/", 1)[0] + "/myface_test"
if "test" not in TEST_URL.rsplit("/", 1)[-1] or "neon" in TEST_URL:
    sys.exit(f"Refus : ce test n'ecrit que dans une base de test (adresse lue : ...{TEST_URL[-30:]})")

engine = create_async_engine(TEST_URL, poolclass=NullPool)
Session = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
DIM = 512
rng = np.random.default_rng(42)


def memoire_mo() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def visages_synthetiques(n_photos: int):
    """-> (personnes, liste par photo de (personne, vecteur)). Popularite en loi
    de puissance : les maries sur beaucoup de photos, la plupart des invites
    sur quelques-unes ; 1 a 6 visages par photo."""
    n_personnes = max(50, n_photos // 7)
    centres = rng.normal(size=(n_personnes, DIM)).astype(np.float32)
    centres /= np.linalg.norm(centres, axis=1, keepdims=True)
    poids = 1 / np.arange(1, n_personnes + 1) ** 0.9
    poids /= poids.sum()
    bruit = 0.036  # similarite cosinus ~0,6 entre deux photos d'une meme personne
    photos = []
    for _ in range(n_photos):
        k = int(rng.choice([1, 2, 2, 3, 3, 4, 5, 6]))
        gens = rng.choice(n_personnes, size=k, replace=False, p=poids)
        vecs = centres[gens] + rng.normal(scale=bruit, size=(k, DIM)).astype(np.float32)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
        photos.append(list(zip(gens.tolist(), vecs)))
    return centres, photos


async def preparer_schema():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_face_embeddings_vector_hnsw ON face_embeddings "
            "USING hnsw (vector vector_cosine_ops) WITH (m = 16, ef_construction = 64)"))


async def remplir(n_photos: int):
    centres, photos = visages_synthetiques(n_photos)
    async with Session() as db:
        user = User(email=f"volume-{uuid.uuid4().hex[:8]}@myface-test.com", hashed_password="x",
                    role=UserRole.PHOTOGRAPHE, display_name="Test volume")
        db.add(user)
        await db.flush()
        event = Event(name=f"Volume {n_photos}", date=datetime.now(timezone.utc), location="Abidjan",
                      kiosk_token=uuid.uuid4().hex, organizer_id=user.id)
        db.add(event)
        await db.flush()
        debut = datetime.now(timezone.utc) - timedelta(hours=6)
        lignes_photos, lignes_visages = [], []
        for i, visages in enumerate(photos):
            pid = uuid.uuid4()
            lignes_photos.append(dict(
                id=pid, event_id=event.id, original_key=f"vol/{pid}.jpg", thumbnail_key=f"vol/t/{pid}.jpg",
                preview_key=f"vol/p/{pid}.jpg", preview_watermarked_key=f"vol/w/{pid}.jpg",
                original_filename=f"IMG_{i:05d}.jpg", indexing_status=IndexingStatus.DONE,
                uploaded_at=debut + timedelta(seconds=i)))
            for j, (_, vec) in enumerate(visages):
                fid = uuid.uuid4()
                lignes_visages.append(dict(
                    id=fid, photo_id=pid, vector=vec.tolist(), confidence=0.9,
                    bounding_box={"x1": 100 * j, "y1": 100, "x2": 100 * j + 80, "y2": 180},
                    crop_key=f"vol/c/{fid}.jpg"))
        for k in range(0, len(lignes_photos), 1000):
            await db.execute(insert(Photo), lignes_photos[k:k + 1000])
        for k in range(0, len(lignes_visages), 1000):
            await db.execute(insert(FaceEmbedding), lignes_visages[k:k + 1000])
        await db.commit()
        return event.id, user.id, centres, photos, len(lignes_visages)


async def mesurer(n_photos: int) -> dict:
    t0 = time.perf_counter()
    event_id, user_id, centres, photos, n_visages = await remplir(n_photos)
    res = {"photos": n_photos, "visages": n_visages, "personnes": len(centres),
           "remplissage_s": round(time.perf_counter() - t0, 1)}

    async with Session() as db:
        for nom, page in (("galerie_page1_s", 1), ("galerie_derniere_page_s", max(1, n_photos // 50))):
            t = time.perf_counter()
            r = await db.execute(
                select(Photo, func.count(Photo.id).over().label("total"))
                .where(Photo.event_id == event_id)
                .order_by(Photo.uploaded_at.desc(), Photo.id)
                .offset((page - 1) * 50).limit(50))
            r.all()
            res[nom] = round(time.perf_counter() - t, 3)

    class _SansStockage:  # toutes les vignettes sont deja connues
        pass

    gc.collect()
    mem_avant = memoire_mo()
    async with Session() as db:
        t = time.perf_counter()
        clusters = await compute_event_clusters(event_id, db, _SansStockage())
        res["trouver_mon_visage_s"] = round(time.perf_counter() - t, 1)
    res["groupes"] = len(clusters.clusters)
    res["groupes_de_plusieurs_photos"] = sum(1 for c in clusters.clusters if len(c.photo_ids) > 1)
    res["memoire_pic_mo"] = round(memoire_mo(), 0)
    res["memoire_ajoutee_mo"] = round(memoire_mo() - mem_avant, 0)
    plus_grand = max(len(c.photo_ids) for c in clusters.clusters)
    vrai_plus_grand = sum(1 for vis in photos if any(p == 0 for p, _ in vis))
    res["plus_grand_groupe"] = f"{plus_grand} photos (attendu : {vrai_plus_grand})"
    del clusters

    # selfie de la personne la plus photographiee
    selfie = centres[0] + rng.normal(scale=0.036, size=DIM).astype(np.float32)
    selfie /= np.linalg.norm(selfie)
    async with Session() as db:
        dist = FaceEmbedding.vector.cosine_distance(selfie.tolist())
        sous = (select(FaceEmbedding.photo_id.label("photo_id"), func.min(dist).label("d"))
                .join(Photo, Photo.id == FaceEmbedding.photo_id)
                .where(Photo.event_id == event_id, dist <= 1 - settings.face_match_similarity_threshold)
                .group_by(FaceEmbedding.photo_id).subquery())
        t = time.perf_counter()
        r = await db.execute(select(Photo.id, sous.c.d).join(sous, Photo.id == sous.c.photo_id)
                             .order_by(sous.c.d).limit(500))
        trouvees = len(r.all())
        res["scan_selfie_s"] = round(time.perf_counter() - t, 3)
        res["scan_photos_trouvees"] = f"{trouvees} (attendu : {min(500, vrai_plus_grand)})"

    async with Session() as db:  # menage : la base de test reste propre
        ids = select(Photo.id).where(Photo.event_id == event_id)
        await db.execute(delete(FaceEmbedding).where(FaceEmbedding.photo_id.in_(ids)))
        await db.execute(delete(Photo).where(Photo.event_id == event_id))
        await db.execute(delete(Event).where(Event.id == event_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
    return res


async def main():
    tailles = [int(x) for x in sys.argv[1:]] or [2000, 5000, 10000]
    await preparer_schema()
    for n in tailles:
        print(json.dumps(await mesurer(n), ensure_ascii=False), flush=True)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
