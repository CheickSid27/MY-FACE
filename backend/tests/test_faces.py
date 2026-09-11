"""Tests de la reconnaissance faciale.

Utilise l'image d'exemple fournie avec le package insightface (photo de
groupe reelle 't1.jpg', livree dans insightface/data/images/) plutot qu'une
image synthetique : la detection de visage ArcFace ne fonctionne que sur de
vrais visages, donc aucun mock n'est possible ni souhaitable ici.
"""

import io
import uuid

import cv2
import pytest
from httpx import AsyncClient
from insightface.data import get_image as ins_get_image
from PIL import Image
from sqlalchemy import select

from app.core.config import get_settings
from app.models.face_embedding import FaceEmbedding
from app.models.photo import IndexingStatus, Photo
from app.services.face_indexing import index_photo_faces
from app.services.face_recognition import ImageDecodeError, detect_faces

settings = get_settings()


def _real_face_image_bytes() -> bytes:
    img = ins_get_image("t1")
    success, buffer = cv2.imencode(".jpg", img)
    assert success
    return buffer.tobytes()


def _plain_color_image_bytes() -> bytes:
    img = Image.new("RGB", (200, 200), color=(80, 80, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


async def _create_event(auth_client: AsyncClient) -> str:
    resp = await auth_client.post(
        "/events",
        json={
            "name": "Gala Faces",
            "date": "2026-11-01T20:00:00Z",
            "location": "Yamoussoukro",
            "pricing": {"unit_price": 800},
        },
    )
    return resp.json()["id"]


async def _seed_photo(event_id: str, storage_service, session_factory, filename: str, image_bytes: bytes) -> str:
    """Cree une photo directement en base (sans passer par /photos/upload),
    pour ne PAS declencher l'indexation automatique en arriere-plan : ces
    tests appellent `index_photo_faces` eux-memes de facon deterministe.
    Executer les deux en meme temps ferait tourner InsightFace deux fois en
    parallele sur la meme instance partagee, ce qui peut bloquer le process."""
    photo_id = uuid.uuid4()
    original_key = f"events/{event_id}/originals/{photo_id}.jpg"
    thumbnail_key = f"events/{event_id}/thumbnails/{photo_id}.jpg"
    await storage_service.upload(original_key, image_bytes, "image/jpeg")
    await storage_service.upload(thumbnail_key, image_bytes, "image/jpeg")

    async with session_factory() as session:
        photo = Photo(
            id=photo_id,
            event_id=uuid.UUID(event_id),
            original_key=original_key,
            thumbnail_key=thumbnail_key,
            original_filename=filename,
            indexing_status=IndexingStatus.PENDING,
        )
        session.add(photo)
        await session.commit()

    return str(photo_id)


def test_detect_faces_on_real_image():
    faces = detect_faces(_real_face_image_bytes())
    assert len(faces) >= 1
    for face in faces:
        assert len(face.embedding) == 512
        assert 0.0 <= face.confidence <= 1.0
        assert len(face.bounding_box) == 4
        assert face.sharpness >= settings.face_min_sharpness


def test_detect_faces_rejects_blurry_face():
    img = ins_get_image("t1")
    blurred = cv2.GaussianBlur(img, (31, 31), 15)
    success, buffer = cv2.imencode(".jpg", blurred)
    assert success
    faces = detect_faces(buffer.tobytes())
    assert faces == []


def test_detect_faces_on_image_without_face():
    faces = detect_faces(_plain_color_image_bytes())
    assert faces == []


def test_detect_faces_invalid_image_raises():
    with pytest.raises(ImageDecodeError):
        detect_faces(b"not an image")


async def test_index_photo_faces_creates_embeddings(
    auth_client: AsyncClient, storage_service, test_session_factory, db_session
):
    event_id = await _create_event(auth_client)
    photo_id = await _seed_photo(
        event_id, storage_service, test_session_factory, "group.jpg", _real_face_image_bytes()
    )

    await index_photo_faces(photo_id, storage=storage_service, session_factory=test_session_factory)

    photo = await db_session.get(Photo, photo_id)
    assert photo.indexing_status == IndexingStatus.DONE

    result = await db_session.execute(select(FaceEmbedding).where(FaceEmbedding.photo_id == photo_id))
    embeddings = result.scalars().all()
    assert len(embeddings) >= 1


async def test_index_photo_faces_marks_failed_on_missing_object(
    auth_client: AsyncClient, storage_service, test_session_factory, db_session
):
    event_id = await _create_event(auth_client)
    photo_id = await _seed_photo(
        event_id, storage_service, test_session_factory, "group.jpg", _real_face_image_bytes()
    )

    # Simule un objet de stockage corrompu.
    photo = await db_session.get(Photo, photo_id)
    storage_service.objects[photo.original_key] = b"corrupted-not-an-image"

    await index_photo_faces(photo_id, storage=storage_service, session_factory=test_session_factory)

    await db_session.refresh(photo)
    assert photo.indexing_status == IndexingStatus.FAILED


async def test_scan_finds_matching_photo(
    auth_client: AsyncClient, client: AsyncClient, storage_service, test_session_factory
):
    event_id = await _create_event(auth_client)
    photo_id = await _seed_photo(
        event_id, storage_service, test_session_factory, "group.jpg", _real_face_image_bytes()
    )

    await index_photo_faces(photo_id, storage=storage_service, session_factory=test_session_factory)

    resp = await client.post(
        f"/faces/scan?event_id={event_id}",
        data={"consent": "true"},
        files={"selfie": ("selfie.jpg", _real_face_image_bytes(), "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["faces_detected_in_selfie"] >= 1
    assert len(data["matches"]) >= 1
    assert any(m["photo"]["id"] == photo_id for m in data["matches"])
    assert all(m["similarity"] >= 0.45 for m in data["matches"])


async def test_scan_requires_consent(client: AsyncClient):
    event_resp_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        f"/faces/scan?event_id={event_resp_id}",
        data={"consent": "false"},
        files={"selfie": ("selfie.jpg", _real_face_image_bytes(), "image/jpeg")},
    )
    assert resp.status_code == 400
    assert "onsentement" in resp.json()["detail"]


async def test_scan_unknown_event_returns_404(client: AsyncClient):
    resp = await client.post(
        "/faces/scan?event_id=00000000-0000-0000-0000-000000000000",
        data={"consent": "true"},
        files={"selfie": ("selfie.jpg", _real_face_image_bytes(), "image/jpeg")},
    )
    assert resp.status_code == 404


async def test_scan_rejects_selfie_without_face(auth_client: AsyncClient, client: AsyncClient):
    event_id = await _create_event(auth_client)
    resp = await client.post(
        f"/faces/scan?event_id={event_id}",
        data={"consent": "true"},
        files={"selfie": ("selfie.jpg", _plain_color_image_bytes(), "image/jpeg")},
    )
    assert resp.status_code == 400
    assert "isage" in resp.json()["detail"]


async def test_clusters_group_duplicate_faces(
    auth_client: AsyncClient, storage_service, test_session_factory
):
    event_id = await _create_event(auth_client)

    photo_ids = []
    for filename in ("group1.jpg", "group2.jpg"):
        photo_id = await _seed_photo(
            event_id, storage_service, test_session_factory, filename, _real_face_image_bytes()
        )
        photo_ids.append(photo_id)

    for photo_id in photo_ids:
        await index_photo_faces(photo_id, storage=storage_service, session_factory=test_session_factory)

    resp = await auth_client.get(f"/events/{event_id}/clusters")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["clusters"]) >= 1
    for cluster in data["clusters"]:
        assert cluster["photo_count"] == 2
        assert len(cluster["photos"]) == 2


async def test_reindex_does_not_duplicate_embeddings(
    auth_client: AsyncClient, storage_service, test_session_factory, db_session
):
    event_id = await _create_event(auth_client)
    photo_id = await _seed_photo(
        event_id, storage_service, test_session_factory, "group.jpg", _real_face_image_bytes()
    )

    await index_photo_faces(photo_id, storage=storage_service, session_factory=test_session_factory)
    first = (await db_session.execute(select(FaceEmbedding).where(FaceEmbedding.photo_id == photo_id))).scalars().all()

    await index_photo_faces(photo_id, storage=storage_service, session_factory=test_session_factory)
    db_session.expire_all()
    second = (await db_session.execute(select(FaceEmbedding).where(FaceEmbedding.photo_id == photo_id))).scalars().all()

    assert len(first) >= 1
    assert len(second) == len(first)


async def test_clusters_cache_invalidated_by_new_indexing(
    auth_client: AsyncClient, storage_service, test_session_factory
):
    event_id = await _create_event(auth_client)
    first_id = await _seed_photo(event_id, storage_service, test_session_factory, "g1.jpg", _real_face_image_bytes())
    await index_photo_faces(first_id, storage=storage_service, session_factory=test_session_factory)

    before = (await auth_client.get(f"/events/{event_id}/clusters")).json()
    assert all(c["photo_count"] == 1 for c in before["clusters"])

    # Deuxieme photo des memes personnes : le resultat memorise doit etre
    # invalide par l'indexation, pas servi perime.
    second_id = await _seed_photo(event_id, storage_service, test_session_factory, "g2.jpg", _real_face_image_bytes())
    await index_photo_faces(second_id, storage=storage_service, session_factory=test_session_factory)

    after = (await auth_client.get(f"/events/{event_id}/clusters")).json()
    assert all(c["photo_count"] == 2 for c in after["clusters"])


async def test_public_clusters_serve_previous_result_while_refreshing(
    auth_client: AsyncClient, client: AsyncClient, storage_service, test_session_factory
):
    from app.services.face_clusters import face_cluster_cache

    event_id = await _create_event(auth_client)
    first_id = await _seed_photo(event_id, storage_service, test_session_factory, "g1.jpg", _real_face_image_bytes())
    await index_photo_faces(first_id, storage=storage_service, session_factory=test_session_factory)
    before = (await client.get(f"/events/{event_id}/clusters/public")).json()
    assert all(c["photo_count"] == 1 for c in before["clusters"])

    second_id = await _seed_photo(event_id, storage_service, test_session_factory, "g2.jpg", _real_face_image_bytes())
    await index_photo_faces(second_id, storage=storage_service, session_factory=test_session_factory)

    # Invite : reponse immediate avec le resultat precedent...
    stale = (await client.get(f"/events/{event_id}/clusters/public")).json()
    assert all(c["photo_count"] == 1 for c in stale["clusters"])

    # ...pendant que le recalcul tourne en arriere-plan.
    await face_cluster_cache._refreshing[uuid.UUID(event_id)]
    fresh = (await client.get(f"/events/{event_id}/clusters/public")).json()
    assert all(c["photo_count"] == 2 for c in fresh["clusters"])


async def test_face_crop_key_memorized(auth_client: AsyncClient, storage_service, test_session_factory, db_session):
    event_id = await _create_event(auth_client)
    photo_id = await _seed_photo(event_id, storage_service, test_session_factory, "g.jpg", _real_face_image_bytes())
    await index_photo_faces(photo_id, storage=storage_service, session_factory=test_session_factory)

    data = (await auth_client.get(f"/events/{event_id}/clusters")).json()
    assert all("/face-crops/" in c["representative_face_url"] for c in data["clusters"])

    result = await db_session.execute(select(FaceEmbedding.crop_key).where(FaceEmbedding.photo_id == photo_id))
    crop_keys = [key for (key,) in result.all() if key]
    assert len(crop_keys) == len(data["clusters"])
    assert all(key in storage_service.objects for key in crop_keys)


async def test_public_clusters_watermark_except_kiosk(
    auth_client: AsyncClient, client: AsyncClient, storage_service, test_session_factory
):
    created = (await auth_client.post(
        "/events",
        json={"name": "Gala Kiosk", "date": "2026-11-01T20:00:00Z", "location": "Abidjan", "pricing": {"unit_price": 800}},
    )).json()
    event_id, kiosk_token = created["id"], created["kiosk_token"]
    photo_id = await _seed_photo(event_id, storage_service, test_session_factory, "g.jpg", _real_face_image_bytes())
    async with test_session_factory() as session:
        photo = await session.get(Photo, uuid.UUID(photo_id))
        photo.preview_key = f"events/{event_id}/previews/{photo_id}.jpg"
        photo.preview_watermarked_key = f"events/{event_id}/previews-wm/{photo_id}.jpg"
        await session.commit()
    await index_photo_faces(photo_id, storage=storage_service, session_factory=test_session_factory)

    phone = (await client.get(f"/events/{event_id}/clusters/public")).json()
    assert "/previews-wm/" in phone["clusters"][0]["photos"][0]["preview_url"]

    kiosk = (await client.get(f"/events/{event_id}/clusters/public", params={"kiosk_token": kiosk_token})).json()
    assert "/previews-wm/" not in kiosk["clusters"][0]["photos"][0]["preview_url"]


async def test_clusters_requires_auth(client: AsyncClient):
    resp = await client.get("/events/00000000-0000-0000-0000-000000000000/clusters")
    assert resp.status_code in (401, 403)
