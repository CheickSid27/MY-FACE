import io
import os
import uuid

import pytest
from PIL import Image
from sqlalchemy import func, select

from app.models.photo import Photo
from app.services.folder_watcher import FolderWatcher

pytestmark = pytest.mark.asyncio


def _jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (320, 240), color=(40, 90, 140)).save(buffer, format="JPEG")
    return buffer.getvalue()


async def _create_event(auth_client) -> str:
    resp = await auth_client.post(
        "/events",
        json={"name": "Gala Dossier", "date": "2026-11-01T20:00:00Z", "location": "Abidjan", "pricing": {"unit_price": 800}},
    )
    return resp.json()["id"]


def _watcher(tmp_path, storage_service, test_session_factory, scheduled: list) -> FolderWatcher:
    return FolderWatcher(
        session_factory=test_session_factory,
        storage=storage_service,
        poll_seconds=0.01,
        base_path=str(tmp_path),
        schedule_indexing=lambda ids, _storage: scheduled.extend(ids),
    )


async def _photo_count(test_session_factory, event_id: str) -> int:
    async with test_session_factory() as db:
        return (await db.execute(select(func.count(Photo.id)).where(Photo.event_id == uuid.UUID(event_id)))).scalar_one()


async def test_ingests_file_once_size_is_stable(auth_client, tmp_path, storage_service, test_session_factory):
    event_id = await _create_event(auth_client)
    (tmp_path / event_id).mkdir()
    (tmp_path / event_id / "IMG_0001.jpg").write_bytes(_jpeg_bytes())
    scheduled: list = []
    watcher = _watcher(tmp_path, storage_service, test_session_factory, scheduled)

    await watcher._scan_once()  # premiere vue : taille pas encore confirmee stable
    assert await _photo_count(test_session_factory, event_id) == 0
    assert watcher.status_for_event(uuid.UUID(event_id))[0].status == "pending_write"

    await watcher._scan_once()  # taille stable : ingestion
    assert await _photo_count(test_session_factory, event_id) == 1
    assert watcher.status_for_event(uuid.UUID(event_id))[0].status == "ingested"
    assert len(scheduled) == 1

    await watcher._scan_once()  # deja traite : ignore
    assert await _photo_count(test_session_factory, event_id) == 1
    assert len(scheduled) == 1


async def test_restart_does_not_duplicate(auth_client, tmp_path, storage_service, test_session_factory):
    event_id = await _create_event(auth_client)
    (tmp_path / event_id).mkdir()
    (tmp_path / event_id / "IMG_0002.jpg").write_bytes(_jpeg_bytes())

    first = _watcher(tmp_path, storage_service, test_session_factory, [])
    await first._scan_once()
    await first._scan_once()

    # Nouveau process (etat memoire perdu) : la photo est reconnue par nom.
    restarted = _watcher(tmp_path, storage_service, test_session_factory, [])
    await restarted._scan_once()
    await restarted._scan_once()
    assert await _photo_count(test_session_factory, event_id) == 1
    assert restarted.status_for_event(uuid.UUID(event_id))[0].detail == "deja present"


async def test_invalid_file_not_retried_until_changed(auth_client, tmp_path, storage_service, test_session_factory):
    event_id = await _create_event(auth_client)
    (tmp_path / event_id).mkdir()
    bad = tmp_path / event_id / "corrompu.jpg"
    bad.write_bytes(b"pas une image")
    watcher = _watcher(tmp_path, storage_service, test_session_factory, [])

    await watcher._scan_once()
    await watcher._scan_once()
    assert watcher.status_for_event(uuid.UUID(event_id))[0].status == "error"

    # Fichier inchange : aucune nouvelle tentative (plus de requete en base
    # toutes les 5 s pour un fichier en erreur).
    watcher._recent_status.clear()
    await watcher._scan_once()
    assert watcher.status_for_event(uuid.UUID(event_id)) == []

    # Fichier remplace par une vraie photo : nouvelle tentative.
    bad.write_bytes(_jpeg_bytes())
    os.utime(bad, None)
    await watcher._scan_once()
    await watcher._scan_once()
    assert await _photo_count(test_session_factory, event_id) == 1


async def test_ignores_non_event_folders(tmp_path, storage_service, test_session_factory):
    (tmp_path / "pas-un-uuid").mkdir()
    (tmp_path / "pas-un-uuid" / "photo.jpg").write_bytes(_jpeg_bytes())
    unknown = str(uuid.uuid4())
    (tmp_path / unknown).mkdir()
    (tmp_path / unknown / "photo.jpg").write_bytes(_jpeg_bytes())
    watcher = _watcher(tmp_path, storage_service, test_session_factory, [])

    await watcher._scan_once()
    await watcher._scan_once()
    assert watcher.status_for_event(uuid.UUID(unknown))[0].detail == "evenement inconnu"
