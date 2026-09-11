"""Surveillance d'un dossier local pour l'ingestion automatique de photos
(section 1 du cahier des charges : "sans intervention manuelle").

Approche : on scanne le disque par polling (pas d'evenements inotify/watchdog).
Sur Windows + Docker Desktop, un dossier hote monte en bind-mount ne propage
pas toujours fiablement les evenements filesystem au conteneur ; le polling
est plus lent mais marche partout, sans dependance supplementaire.

Structure attendue : {settings.watched_folder_path}/<event_id>/*.jpg — un
sous-dossier par evenement (cree automatiquement a la creation de
l'evenement, voir routers/events.py). Chaque fichier image y apparaissant est
ingere automatiquement des que sa taille est stable entre deux scans
(evite de lire un fichier encore en cours de copie).

Le scan periodique ne touche QUE le disque : la base n'est interrogee que
lorsqu'un fichier nouveau (ou modifie) est pret a etre ingere. Auparavant,
chaque scan (toutes les 5 s, en permanence) listait les evenements en base :
Neon ne pouvait jamais se mettre en veille et consommait son quota gratuit
meme sans aucune activite."""

import asyncio
import logging
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.event import Event
from app.models.photo import Photo
from app.services.face_indexing import index_photos_faces
from app.services.ingestion import InvalidImageError, ingest_photo
from app.services.storage import StorageService, get_storage_service

logger = logging.getLogger("myface.folder_watcher")
settings = get_settings()

CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@dataclass
class WatchedFileStatus:
    filename: str
    status: str  # "pending_write" | "ingested" | "error"
    detail: str | None = None


@dataclass(frozen=True)
class _FileState:
    size: int
    mtime: float


@dataclass(frozen=True)
class _FoundFile:
    event_id: uuid.UUID
    path: str
    name: str
    state: _FileState


def _read_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


@dataclass
class FolderWatcher:
    session_factory: Callable[[], AsyncSession] = AsyncSessionLocal
    storage: StorageService | None = None
    poll_seconds: float = field(default_factory=lambda: settings.watched_folder_poll_seconds)
    base_path: str = field(default_factory=lambda: settings.watched_folder_path)
    # Programme l'indexation faciale des photos ingerees. Injectable pour les
    # tests (qui ne doivent pas lancer InsightFace en tache de fond).
    schedule_indexing: Callable[[list[uuid.UUID], StorageService], None] | None = None

    _task: asyncio.Task | None = field(default=None, init=False, repr=False)
    _pending: dict[str, _FileState] = field(default_factory=dict, init=False, repr=False)
    # Etat (taille, date) de chaque fichier deja traite, ingere OU en erreur :
    # tant qu'il ne change pas, il n'est plus jamais re-examine. Une erreur
    # n'est donc retentee que si le fichier est remplace/modifie.
    _settled: dict[str, _FileState] = field(default_factory=dict, init=False, repr=False)
    _recent_status: dict[str, WatchedFileStatus] = field(default_factory=dict, init=False, repr=False)
    _index_tasks: set[asyncio.Task] = field(default_factory=set, init=False, repr=False)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run_loop())
            logger.info("Dossier surveille actif : %s (poll %.0fs)", self.base_path, self.poll_seconds)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def status_for_event(self, event_id: uuid.UUID) -> list[WatchedFileStatus]:
        prefix = f"{event_id}/"
        return [
            status
            for key, status in self._recent_status.items()
            if key.startswith(prefix)
        ]

    def event_folder(self, event_id: uuid.UUID) -> str:
        return os.path.join(self.base_path, str(event_id))

    def ensure_event_folder(self, event_id: uuid.UUID) -> bool:
        """Cree le sous-dossier de l'evenement s'il manque (le chemin affiche
        a l'organisateur doit exister pour qu'il puisse y deposer ses photos).
        Sans effet si le dossier surveille lui-meme n'est pas monte."""
        if not os.path.isdir(self.base_path):
            return False
        try:
            os.makedirs(self.event_folder(event_id), exist_ok=True)
            return True
        except OSError:
            logger.warning("Impossible de creer le dossier surveille de %s", event_id)
            return False

    async def _run_loop(self) -> None:
        while True:
            try:
                await self._scan_once()
            except Exception:  # noqa: BLE001 - ne doit jamais tuer la boucle de fond
                logger.exception("Erreur durant le scan du dossier surveille")
            await asyncio.sleep(self.poll_seconds)

    def _list_files(self) -> list[_FoundFile]:
        """Parcours disque uniquement (execute dans un thread)."""
        if not os.path.isdir(self.base_path):
            return []
        found: list[_FoundFile] = []
        for folder in os.scandir(self.base_path):
            if not folder.is_dir():
                continue
            try:
                event_id = uuid.UUID(folder.name)
            except ValueError:
                continue
            for entry in os.scandir(folder.path):
                if not entry.is_file():
                    continue
                if os.path.splitext(entry.name)[1].lower() not in CONTENT_TYPES:
                    continue
                stat = entry.stat()
                found.append(
                    _FoundFile(event_id, entry.path, entry.name, _FileState(stat.st_size, stat.st_mtime))
                )
        return found

    async def _scan_once(self) -> None:
        files = await asyncio.to_thread(self._list_files)
        storage: StorageService | None = None
        ingested: list[uuid.UUID] = []

        for found in files:
            key = f"{found.event_id}/{found.name}"
            if self._settled.get(key) == found.state:
                continue

            if self._pending.get(key) != found.state:
                self._pending[key] = found.state
                self._recent_status[key] = WatchedFileStatus(found.name, "pending_write")
                continue

            del self._pending[key]
            storage = storage or self.storage or get_storage_service()
            photo_id = await self._ingest_file(found, key, storage)
            self._settled[key] = found.state
            if photo_id is not None:
                ingested.append(photo_id)

        if ingested and storage is not None:
            self._schedule(ingested, storage)

    def _schedule(self, photo_ids: list[uuid.UUID], storage: StorageService) -> None:
        if self.schedule_indexing is not None:
            self.schedule_indexing(photo_ids, storage)
            return
        task = asyncio.create_task(index_photos_faces(photo_ids, storage, self.session_factory))
        # Reference gardee jusqu'a la fin : une tache asyncio sans reference
        # peut etre ramassee par le garbage collector en cours de route.
        self._index_tasks.add(task)
        task.add_done_callback(self._index_tasks.discard)

    async def _ingest_file(self, found: _FoundFile, key: str, storage: StorageService) -> uuid.UUID | None:
        filename = found.name
        try:
            content_type = CONTENT_TYPES[os.path.splitext(filename)[1].lower()]

            async with self.session_factory() as db:
                if await db.get(Event, found.event_id) is None:
                    self._recent_status[key] = WatchedFileStatus(filename, "error", "evenement inconnu")
                    return None

                # Deja ingere lors d'un scan precedent (ex: apres un redemarrage
                # du backend qui a perdu l'etat en memoire) : on evite le doublon
                # en verifiant par nom de fichier original, AVANT de lire le
                # fichier (jusqu'a 25 Mo) pour rien.
                existing = await db.execute(
                    select(Photo.id).where(Photo.event_id == found.event_id, Photo.original_filename == filename)
                )
                if existing.first() is not None:
                    self._recent_status[key] = WatchedFileStatus(filename, "ingested", "deja present")
                    return None

                data = await asyncio.to_thread(_read_file, found.path)
                photo = await ingest_photo(found.event_id, filename, content_type, data, db, storage)
                await db.commit()
                photo_id = photo.id

            self._recent_status[key] = WatchedFileStatus(filename, "ingested")
            logger.info("Dossier surveille : %s ingere pour l'evenement %s", filename, found.event_id)
            return photo_id
        except (ValueError, InvalidImageError) as exc:
            self._recent_status[key] = WatchedFileStatus(filename, "error", str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Echec ingestion dossier surveille : %s", filename)
            self._recent_status[key] = WatchedFileStatus(filename, "error", str(exc))
        return None


folder_watcher = FolderWatcher()
