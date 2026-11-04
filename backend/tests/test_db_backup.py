"""Sauvegardes de la base envoyees dans R2 (services/db_backup.py)."""

import datetime as dt

import pytest

from app.services import db_backup

pytestmark = pytest.mark.asyncio


async def test_new_backups_are_sent_once_and_old_ones_removed(tmp_path, storage_service, monkeypatch):
    monkeypatch.setattr(db_backup, "DOSSIER", tmp_path)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    recent = tmp_path / f"myface-{today}-0300.dump"
    recent.write_bytes(b"copie recente")
    (tmp_path / "myface-20200101-0300.dump").write_bytes(b"trop vieille")
    (tmp_path / "autre-fichier.txt").write_text("ignore")
    await storage_service.upload("sauvegardes/myface-20200101-0300.dump", b"x", "application/octet-stream")

    assert await db_backup.envoyer_sauvegardes(storage_service) == 1
    assert storage_service.objects[f"sauvegardes/{recent.name}"] == b"copie recente"
    assert "sauvegardes/myface-20200101-0300.dump" not in storage_service.objects

    # deja envoyee : rien de plus au passage suivant
    assert await db_backup.envoyer_sauvegardes(storage_service) == 0


async def test_no_backup_folder_is_fine(tmp_path, storage_service, monkeypatch):
    monkeypatch.setattr(db_backup, "DOSSIER", tmp_path / "absent")
    assert await db_backup.envoyer_sauvegardes(storage_service) == 0
