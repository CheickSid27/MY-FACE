"""Surveillance d'un dossier local pour l'ingestion automatique de photos
(section 1 du cahier des charges : "sans intervention manuelle").

Approche : on scanne le disque par polling (pas d'evenements inotify/watchdog).
Sur Windows + Docker Desktop, un dossier hote monte en bind-mount ne propage
pas toujours fiablement les evenements filesystem au conteneur ; le polling
est plus lent mais marche partout, sans dependance supplementaire.

Structure attendue : {settings.watched_folder_path}/<event_id>/*.jpg — un
sous-dossier par evenement (cree a la main, ou par le logiciel de transfert
de l'appareil photo/carte SD). Chaque fichier image y apparaissant est
ingere automatiquement des que sa taille est stable entre deux scans
(evite de lire un fichier encore en cours de copie)."""

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
from app.services.face_indexing import index_photo_faces
from app.services.ingestion import InvalidImageError, ingest_photo
from app.services.storage import StorageService, get_storage_service

logger = logging.getLogger("myface.folder_watcher")
settings = get_settings()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass
class WatchedFileStatus:
    filename: str
    status: str  # "pending_write" | "ingested" | "error"
    detail: str | None = None


@dataclass
class _PendingFile:
    size: int


@dataclass
class FolderWatcher:
    session_factory: Callable[[], AsyncSession] = AsyncSessionLocal
    storage: StorageService | None = None
    poll_seconds: float = field(default_factory=lambda: settings.watched_folder_poll_seconds)
    base_path: str = field(default_factory=lambda: settings.watched_folder_path)

    _task: asyncio.Task | None = field(default=None, init=False, repr=False)
    _pending: dict[str, _PendingFile] = field(default_factory=dict, init=False, repr=False)
    _recent_status: dict[str, WatchedFileStatus] = field(default_factory=dict, init=False, repr=False)

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

    async def _run_loop(self) -> None:
        while True:
            try:
                await self._scan_once()
            except Exception:  # noqa: BLE001 - ne doit jamais tuer la boucle de fond
                logger.exception("Erreur durant le scan du dossier surveille")
            await asyncio.sleep(self.poll_seconds)

    async def _scan_once(self) -> None:
        if not os.path.isdir(self.base_path):
            return

        async with self.session_factory() as db:
            result = await db.execute(select(Event.id))
            event_ids = {row[0] for row in result.all()}

        storage = self.storage or get_storage_service()

        for event_id in event_ids:
            folder = self.event_folder(event_id)
            if not os.path.isdir(folder):
                continue

            for entry in os.scandir(folder):
                if not entry.is_file():
                    continue
                ext = os.path.splitext(entry.name)[1].lower()
                if ext not in IMAGE_EXTENSIONS:
                    continue

                key = f"{event_id}/{entry.name}"
                if key in self._recent_status and self._recent_status[key].status == "ingested":
                    continue

                size = entry.stat().st_size
                pending = self._pending.get(key)
                if pending is None or pending.size != size:
                    self._pending[key] = _PendingFile(size=size)
                    self._recent_status[key] = WatchedFileStatus(entry.name, "pending_write")
                    continue

                del self._pending[key]
                await self._ingest_file(event_id, entry.path, entry.name, key, db_storage=storage)

    async def _ingest_file(
        self, event_id: uuid.UUID, path: str, filename: str, key: str, db_storage: StorageService
    ) -> None:
        try:
            with open(path, "rb") as f:
                data = f.read()

            content_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }[os.path.splitext(filename)[1].lower()]

            async with self.session_factory() as db:
                # Deja ingere lors d'un scan precedent (ex: apres un redemarrage
                # du backend qui a perdu l'etat en memoire) : on evite le doublon
                # en verifiant par nom de fichier original.
                existing = await db.execute(
                    select(Photo.id).where(Photo.event_id == event_id, Photo.original_filename == filename)
                )
                if existing.scalar_one_or_none() is not None:
                    self._recent_status[key] = WatchedFileStatus(filename, "ingested", "deja present")
                    return

                photo = await ingest_photo(event_id, filename, content_type, data, db, db_storage)
                await db.commit()
                await db.refresh(photo)

            self._recent_status[key] = WatchedFileStatus(filename, "ingested")
            logger.info("Dossier surveille : %s ingere pour l'evenement %s", filename, event_id)
            asyncio.create_task(index_photo_faces(photo.id, db_storage, self.session_factory))
        except (ValueError, InvalidImageError) as exc:
            self._recent_status[key] = WatchedFileStatus(filename, "error", str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Echec ingestion dossier surveille : %s", filename)
            self._recent_status[key] = WatchedFileStatus(filename, "error", str(exc))


folder_watcher = FolderWatcher()
