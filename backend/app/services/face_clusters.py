"""Groupage des visages d'un evenement ("personnes detectees") + cache memoire.

DBSCAN sur tous les embeddings de l'evenement (metrique cosinus) : eps est
une DISTANCE cosinus (1 - similarite), coherente avec le seuil utilise pour
le scan visiteur (voir core/config.py). Un visage "bruit" pour DBSCAN (aucun
voisin a moins de eps) reste une personne a part entiere : il forme son
propre groupe a une photo (identifiants negatifs synthetiques) plutot que
d'etre rejete, pour rester retrouvable meme photographie une seule fois.

Pourquoi un cache : ce calcul etait refait a CHAQUE ouverture de "Trouver mon
visage" (rapatriement de tous les vecteurs 512-d depuis Neon, DBSCAN, puis un
aller-retour R2 par groupe pour verifier sa vignette), soit 11 a 60 s mesurees
sur 52 groupes, avec des 504. Le resultat ne change que lorsqu'une photo de
l'evenement est indexee ou supprimee : il est donc memorise par evenement et
invalide explicitement a ces moments-la (face_indexing.py, routers/photos.py,
routers/events.py). Les URLs signees (qui expirent) ne sont jamais mises en
cache : elles sont regenerees a chaque reponse, calcul local sans reseau."""

import asyncio
import datetime as dt
import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import DBSCAN
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.face_embedding import FaceEmbedding
from app.models.photo import IndexingStatus, Photo
from app.schemas.face import ClusterListResponse, FaceCluster
from app.schemas.photo import PhotoRead
from app.services.face_crops import ensure_face_crop
from app.services.photo_urls import to_photo_read
from app.services.storage import StorageService

logger = logging.getLogger("myface.face_clusters")
settings = get_settings()

# Vignettes manquantes generees en parallele (telechargement de l'original +
# recadrage) lors du premier calcul d'un evenement.
CROP_CONCURRENCY = 6
FACE_CROP_URL_TTL_SECONDS = 3600


@dataclass(frozen=True)
class PhotoSnapshot:
    """Copie immuable des champs d'une Photo necessaires a PhotoRead :
    conservee dans le cache sans garder d'objet ORM lie a une session."""

    id: uuid.UUID
    event_id: uuid.UUID
    thumbnail_key: str
    preview_key: str | None
    preview_watermarked_key: str | None
    original_filename: str
    indexing_status: IndexingStatus
    uploaded_at: dt.datetime

    @classmethod
    def from_photo(cls, photo: Photo) -> "PhotoSnapshot":
        return cls(
            id=photo.id,
            event_id=photo.event_id,
            thumbnail_key=photo.thumbnail_key,
            preview_key=photo.preview_key,
            preview_watermarked_key=photo.preview_watermarked_key,
            original_filename=photo.original_filename,
            indexing_status=photo.indexing_status,
            uploaded_at=photo.uploaded_at,
        )


@dataclass(frozen=True)
class ClusterSnapshot:
    cluster_id: int
    photo_ids: tuple[uuid.UUID, ...]
    representative_photo_id: uuid.UUID
    # Cle de la vignette recadree sur le visage ; a defaut (echec de
    # generation), la miniature de la photo representative.
    representative_image_key: str


@dataclass(frozen=True)
class EventClusters:
    clusters: tuple[ClusterSnapshot, ...]
    photos: dict[uuid.UUID, PhotoSnapshot]


def _dbscan_labels(vectors: np.ndarray) -> np.ndarray:
    return DBSCAN(
        eps=settings.face_cluster_eps,
        min_samples=settings.face_cluster_min_samples,
        metric="cosine",
    ).fit_predict(vectors)


async def compute_event_clusters(event_id: uuid.UUID, db: AsyncSession, storage: StorageService) -> EventClusters:
    result = await db.execute(
        select(
            FaceEmbedding.id,
            FaceEmbedding.vector,
            FaceEmbedding.confidence,
            FaceEmbedding.bounding_box,
            FaceEmbedding.crop_key,
            Photo,
        )
        .join(Photo, Photo.id == FaceEmbedding.photo_id)
        .where(Photo.event_id == event_id)
    )
    rows = result.all()
    if not rows:
        return EventClusters(clusters=(), photos={})

    vectors = np.array([row.vector for row in rows], dtype=np.float32)
    # DBSCAN (calcul CPU, quelques centaines de ms sur des milliers de
    # visages) execute hors de la boucle d'evenements.
    labels = await asyncio.to_thread(_dbscan_labels, vectors)

    photos = {row.Photo.id: PhotoSnapshot.from_photo(row.Photo) for row in rows}
    groups: dict[int, dict] = {}
    next_singleton_id = -1
    for label, row in zip(labels, rows):
        if label == -1:
            cluster_id = next_singleton_id
            next_singleton_id -= 1
        else:
            cluster_id = int(label)
        group = groups.setdefault(cluster_id, {"photo_ids": set(), "best": None})
        group["photo_ids"].add(row.Photo.id)
        if group["best"] is None or row.confidence > group["best"].confidence:
            group["best"] = row

    ordered = sorted(groups.items(), key=lambda kv: -len(kv[1]["photo_ids"]))

    semaphore = asyncio.Semaphore(CROP_CONCURRENCY)

    async def _crop_for(best_row) -> str | None:
        async with semaphore:
            try:
                return await ensure_face_crop(
                    best_row.id,
                    event_id,
                    best_row.Photo.original_key,
                    best_row.bounding_box,
                    best_row.crop_key,
                    storage,
                )
            except Exception:
                logger.exception("Vignette de visage impossible pour %s", best_row.id)
                return None

    crop_keys = await asyncio.gather(*(_crop_for(group["best"]) for _, group in ordered))

    # Cles nouvellement connues memorisees en une seule requete (mise a jour
    # groupee par cle primaire) : les affichages suivants n'ont plus besoin
    # d'interroger le stockage.
    newly_known = [
        {"id": group["best"].id, "crop_key": key}
        for (_, group), key in zip(ordered, crop_keys)
        if key is not None and group["best"].crop_key != key
    ]
    if newly_known:
        await db.execute(update(FaceEmbedding), newly_known)
        await db.commit()

    clusters = tuple(
        ClusterSnapshot(
            cluster_id=cluster_id,
            photo_ids=tuple(
                sorted(group["photo_ids"], key=lambda pid: photos[pid].uploaded_at, reverse=True)
            ),
            representative_photo_id=group["best"].Photo.id,
            representative_image_key=key or group["best"].Photo.thumbnail_key,
        )
        for (cluster_id, group), key in zip(ordered, crop_keys)
    )
    return EventClusters(clusters=clusters, photos=photos)


@dataclass(frozen=True)
class _CacheEntry:
    computed_at: float
    # Generation de l'evenement au DEMARRAGE du calcul : si une invalidation
    # est survenue depuis (photo indexee pendant le calcul), le resultat est
    # considere comme perime, jamais fige comme s'il etait a jour.
    generation: int
    value: EventClusters


class FaceClusterCache:
    """Cache memoire par evenement (un seul process uvicorn).

    Deux modes de lecture :
    - a jour (admin) : si le resultat memorise est perime, on recalcule
      avant de repondre ;
    - tolerant (invites, `allow_stale`) : pendant un evenement, chaque photo
      indexee invalide le cache. Plutot que de faire attendre un invite le
      temps d'un recalcul (plusieurs secondes, surtout latence Neon), on
      renvoie immediatement le dernier resultat et on recalcule en tache de
      fond ; la nouvelle photo apparait quelques secondes plus tard."""

    def __init__(self) -> None:
        self._entries: dict[uuid.UUID, _CacheEntry] = {}
        self._generations: dict[uuid.UUID, int] = defaultdict(int)
        self._locks: dict[uuid.UUID, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._refreshing: dict[uuid.UUID, asyncio.Task] = {}

    def invalidate(self, event_id: uuid.UUID, *, drop: bool = False) -> None:
        """Marque le resultat de l'evenement comme perime. `drop` le retire
        completement (photo ou evenement supprime : ne plus jamais le servir,
        meme en mode tolerant)."""
        self._generations[event_id] += 1
        if drop:
            self._entries.pop(event_id, None)

    def _is_fresh(self, event_id: uuid.UUID, entry: _CacheEntry) -> bool:
        return (
            entry.generation == self._generations[event_id]
            and time.monotonic() - entry.computed_at <= settings.face_cluster_cache_ttl_seconds
        )

    async def _compute_and_store(
        self, event_id: uuid.UUID, db: AsyncSession, storage: StorageService
    ) -> EventClusters:
        generation = self._generations[event_id]
        started = time.monotonic()
        value = await compute_event_clusters(event_id, db, storage)
        self._entries[event_id] = _CacheEntry(time.monotonic(), generation, value)
        logger.info(
            "Groupes de visages calcules pour %s : %d groupe(s) en %.1fs",
            event_id,
            len(value.clusters),
            time.monotonic() - started,
        )
        return value

    def _refresh_in_background(
        self, event_id: uuid.UUID, storage: StorageService, session_factory: Callable[[], AsyncSession]
    ) -> None:
        running = self._refreshing.get(event_id)
        if running is not None and not running.done():
            return

        async def _run() -> None:
            try:
                async with self._locks[event_id]:
                    entry = self._entries.get(event_id)
                    if entry is not None and self._is_fresh(event_id, entry):
                        return
                    async with session_factory() as db:
                        await self._compute_and_store(event_id, db, storage)
            except Exception:
                logger.exception("Recalcul en tache de fond des groupes de %s : echec", event_id)

        self._refreshing[event_id] = asyncio.create_task(_run())

    async def get(
        self,
        event_id: uuid.UUID,
        db: AsyncSession,
        storage: StorageService,
        *,
        allow_stale: bool = False,
        session_factory: Callable[[], AsyncSession] | None = None,
    ) -> EventClusters:
        entry = self._entries.get(event_id)
        if entry is not None and self._is_fresh(event_id, entry):
            return entry.value
        if allow_stale and entry is not None and session_factory is not None:
            self._refresh_in_background(event_id, storage, session_factory)
            return entry.value

        # Un seul calcul a la fois par evenement : plusieurs invites qui
        # ouvrent "Trouver mon visage" en meme temps attendent le meme
        # resultat au lieu de relancer chacun le calcul complet.
        async with self._locks[event_id]:
            entry = self._entries.get(event_id)
            if entry is not None and self._is_fresh(event_id, entry):
                return entry.value
            return await self._compute_and_store(event_id, db, storage)

    async def prewarm(
        self, event_ids: list[uuid.UUID], storage: StorageService, session_factory: Callable[[], AsyncSession]
    ) -> None:
        """Calcule a l'avance (demarrage du backend) les groupes des
        evenements recents : le premier invite n'attend pas le calcul."""
        for event_id in event_ids:
            try:
                async with self._locks[event_id]:
                    async with session_factory() as db:
                        await self._compute_and_store(event_id, db, storage)
            except Exception:
                logger.exception("Pre-calcul des groupes de %s : echec", event_id)


face_cluster_cache = FaceClusterCache()


async def recent_event_ids(db: AsyncSession, days: int = 30, limit: int = 10) -> list[uuid.UUID]:
    """Evenements ayant recu des photos recemment (candidats au pre-calcul)."""
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    result = await db.execute(
        select(Photo.event_id)
        .where(Photo.uploaded_at >= since)
        .group_by(Photo.event_id)
        .order_by(func.max(Photo.uploaded_at).desc())
        .limit(limit)
    )
    return [event_id for (event_id,) in result.all()]


async def build_cluster_response(
    snapshot: EventClusters, storage: StorageService, *, clean_preview: bool
) -> ClusterListResponse:
    # Une photo de groupe apparait dans plusieurs groupes : sa PhotoRead
    # (2 URLs signees) n'est construite qu'une fois par reponse.
    reads: dict[uuid.UUID, PhotoRead] = {}

    async def _read(photo_id: uuid.UUID) -> PhotoRead:
        if photo_id not in reads:
            reads[photo_id] = await to_photo_read(snapshot.photos[photo_id], storage, clean_preview=clean_preview)
        return reads[photo_id]

    clusters = []
    for cluster in snapshot.clusters:
        clusters.append(
            FaceCluster(
                cluster_id=cluster.cluster_id,
                photo_count=len(cluster.photo_ids),
                representative_photo=await _read(cluster.representative_photo_id),
                representative_face_url=await storage.get_presigned_url(
                    cluster.representative_image_key, expires_in=FACE_CROP_URL_TTL_SECONDS
                ),
                photos=[await _read(photo_id) for photo_id in cluster.photo_ids],
            )
        )
    return ClusterListResponse(clusters=clusters, unclustered_count=0)
