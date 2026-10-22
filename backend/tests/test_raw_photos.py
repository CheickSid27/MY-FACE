"""Photos RAW et limite de 70 Mo : le RAW est garde tel quel, un JPEG pleine
resolution sert d'original (apercus, visages, telechargement)."""

import pytest
from httpx import AsyncClient

from app.services import ingestion, raw_images
from app.services.thumbnails import InvalidImageError
from tests.test_photos import _create_event, _make_jpeg_bytes

pytestmark = pytest.mark.asyncio


async def test_raw_upload_keeps_raw_and_serves_jpeg(auth_client: AsyncClient, storage_service, monkeypatch):
    jpeg = _make_jpeg_bytes()
    monkeypatch.setattr(ingestion, "raw_to_jpeg", lambda data: jpeg)
    event_id = await _create_event(auth_client)
    raw_bytes = b"faux-fichier-raw-de-boitier" * 100

    files = [("files", ("IMG_0042.CR3", raw_bytes, "application/octet-stream"))]
    resp = await auth_client.post(f"/photos/upload?event_id={event_id}", files=files)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["errors"] == []
    assert body["uploaded"][0]["original_filename"] == "IMG_0042.jpg"

    raw_keys = [k for k in storage_service.objects if "/raw/" in k]
    assert len(raw_keys) == 1 and raw_keys[0].endswith(".cr3")
    assert storage_service.objects[raw_keys[0]] == raw_bytes
    originals = [k for k in storage_service.objects if "/originals/" in k]
    assert storage_service.objects[originals[0]] == jpeg

    # supprimer la photo efface aussi le RAW
    photo_id = body["uploaded"][0]["id"]
    assert (await auth_client.delete(f"/photos/{photo_id}")).status_code in (200, 204)
    assert not [k for k in storage_service.objects if "/raw/" in k]


async def test_unreadable_raw_is_reported(auth_client: AsyncClient):
    event_id = await _create_event(auth_client)
    files = [("files", ("DSC_0001.NEF", b"pas un vrai raw", "application/octet-stream"))]
    resp = await auth_client.post(f"/photos/upload?event_id={event_id}", files=files)
    assert resp.status_code == 201
    assert resp.json()["uploaded"] == []
    assert "RAW" in resp.json()["errors"][0]["error"]


def test_raw_detection_and_limit():
    assert raw_images.is_raw_filename("a.ARW") and raw_images.is_raw_filename("b.dng")
    assert not raw_images.is_raw_filename("c.jpg")
    assert ingestion.MAX_FILE_SIZE_BYTES == 70 * 1024 * 1024
    with pytest.raises(InvalidImageError):
        raw_images.raw_to_jpeg(b"garbage")
