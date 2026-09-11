import io

import pytest
from httpx import AsyncClient
from PIL import Image

pytestmark = pytest.mark.asyncio


def _make_jpeg_bytes(color: tuple[int, int, int] = (200, 50, 50)) -> bytes:
    img = Image.new("RGB", (800, 600), color=color)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


async def _create_event(auth_client: AsyncClient) -> str:
    resp = await auth_client.post(
        "/events",
        json={
            "name": "Bapteme Traore",
            "date": "2026-10-01T10:00:00Z",
            "location": "Bouake",
            "pricing": {"unit_price": 500},
        },
    )
    return resp.json()["id"]


async def test_upload_photos_batch(auth_client: AsyncClient):
    event_id = await _create_event(auth_client)

    files = [
        ("files", ("photo1.jpg", _make_jpeg_bytes((10, 10, 10)), "image/jpeg")),
        ("files", ("photo2.jpg", _make_jpeg_bytes((20, 20, 20)), "image/jpeg")),
    ]
    resp = await auth_client.post(f"/photos/upload?event_id={event_id}", files=files)

    assert resp.status_code == 201
    data = resp.json()
    assert len(data["uploaded"]) == 2
    assert data["errors"] == []
    for photo in data["uploaded"]:
        assert photo["thumbnail_url"]
        assert photo["indexing_status"] == "pending"


async def test_upload_rejects_invalid_file_type(auth_client: AsyncClient):
    event_id = await _create_event(auth_client)

    files = [("files", ("notanimage.txt", b"hello world", "text/plain"))]
    resp = await auth_client.post(f"/photos/upload?event_id={event_id}", files=files)

    assert resp.status_code == 201
    data = resp.json()
    assert data["uploaded"] == []
    assert len(data["errors"]) == 1
    assert "notanimage.txt" in data["errors"][0]["filename"]


async def test_upload_requires_auth(client: AsyncClient):
    files = [("files", ("photo1.jpg", _make_jpeg_bytes(), "image/jpeg"))]
    resp = await client.post(
        "/photos/upload?event_id=00000000-0000-0000-0000-000000000000", files=files
    )
    assert resp.status_code in (401, 403)


async def test_upload_unknown_event_returns_404(auth_client: AsyncClient):
    files = [("files", ("photo1.jpg", _make_jpeg_bytes(), "image/jpeg"))]
    resp = await auth_client.post(
        "/photos/upload?event_id=00000000-0000-0000-0000-000000000000", files=files
    )
    assert resp.status_code == 404


async def test_list_event_photos(auth_client: AsyncClient):
    event_id = await _create_event(auth_client)
    files = [("files", ("photo1.jpg", _make_jpeg_bytes(), "image/jpeg"))]
    await auth_client.post(f"/photos/upload?event_id={event_id}", files=files)

    resp = await auth_client.get(f"/events/{event_id}/photos")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


async def test_list_photos_pagination(auth_client: AsyncClient):
    event_id = await _create_event(auth_client)
    files = [
        ("files", (f"photo{i}.jpg", _make_jpeg_bytes((i, i, i)), "image/jpeg")) for i in range(1, 4)
    ]
    await auth_client.post(f"/photos/upload?event_id={event_id}", files=files)

    resp = await auth_client.get(f"/events/{event_id}/photos?page=1&page_size=2")
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2


async def test_delete_photo(auth_client: AsyncClient):
    event_id = await _create_event(auth_client)
    files = [("files", ("photo1.jpg", _make_jpeg_bytes(), "image/jpeg"))]
    upload_resp = await auth_client.post(f"/photos/upload?event_id={event_id}", files=files)
    photo_id = upload_resp.json()["uploaded"][0]["id"]

    resp = await auth_client.delete(f"/photos/{photo_id}")
    assert resp.status_code == 204

    list_resp = await auth_client.get(f"/events/{event_id}/photos")
    assert list_resp.json()["total"] == 0


async def test_delete_photo_requires_auth(client: AsyncClient):
    resp = await client.delete("/photos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code in (401, 403)


async def test_delete_photo_unknown_returns_404(auth_client: AsyncClient):
    resp = await auth_client.delete("/photos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_upload_generates_watermarked_preview(auth_client: AsyncClient, storage_service):
    event_id = await _create_event(auth_client)
    files = [("files", ("photo1.jpg", _make_jpeg_bytes(), "image/jpeg"))]
    photo = (await auth_client.post(f"/photos/upload?event_id={event_id}", files=files)).json()["uploaded"][0]

    wm_key = f"events/{event_id}/previews-wm/{photo['id']}.jpg"
    clean_key = f"events/{event_id}/previews/{photo['id']}.jpg"
    assert wm_key in storage_service.objects
    assert clean_key in storage_service.objects
    # Meme dimensions que l'apercu net, contenu different (filigrane incruste).
    wm = Image.open(io.BytesIO(storage_service.objects[wm_key]))
    clean = Image.open(io.BytesIO(storage_service.objects[clean_key]))
    assert wm.size == clean.size
    assert storage_service.objects[wm_key] != storage_service.objects[clean_key]


async def test_public_gallery_serves_watermark_except_on_kiosk(auth_client: AsyncClient, client: AsyncClient):
    created = (await auth_client.post(
        "/events",
        json={"name": "Gala Filigrane", "date": "2026-10-01T10:00:00Z", "location": "Abidjan", "pricing": {"unit_price": 500}},
    )).json()
    event_id, kiosk_token = created["id"], created["kiosk_token"]
    files = [("files", ("photo1.jpg", _make_jpeg_bytes(), "image/jpeg"))]
    await auth_client.post(f"/photos/upload?event_id={event_id}", files=files)
    client.headers.pop("Authorization", None)

    phone = (await client.get(f"/events/{event_id}/photos")).json()["items"][0]
    assert "/previews-wm/" in phone["preview_url"]

    wrong = (await client.get(f"/events/{event_id}/photos", params={"kiosk_token": "faux"})).json()["items"][0]
    assert "/previews-wm/" in wrong["preview_url"]

    kiosk = (await client.get(f"/events/{event_id}/photos", params={"kiosk_token": kiosk_token})).json()["items"][0]
    assert "/previews/" in kiosk["preview_url"]
    assert "/previews-wm/" not in kiosk["preview_url"]


async def test_photo_without_watermark_yet_falls_back_to_thumbnail(
    auth_client: AsyncClient, client: AsyncClient, storage_service, test_session_factory, seed_photo
):
    """Anciennes photos pas encore rattrapees : le telephone recoit la
    miniature, jamais l'apercu net."""
    event_id = await _create_event(auth_client)
    await seed_photo(event_id, storage_service, test_session_factory, "old.jpg", _make_jpeg_bytes())

    item = (await client.get(f"/events/{event_id}/photos")).json()["items"][0]
    assert "/thumbnails/" in item["preview_url"]


async def test_delete_photo_removes_all_derivatives(auth_client: AsyncClient, storage_service):
    event_id = await _create_event(auth_client)
    files = [("files", ("photo1.jpg", _make_jpeg_bytes(), "image/jpeg"))]
    photo_id = (await auth_client.post(f"/photos/upload?event_id={event_id}", files=files)).json()["uploaded"][0]["id"]
    assert any(photo_id in key for key in storage_service.objects)

    assert (await auth_client.delete(f"/photos/{photo_id}")).status_code == 204
    assert not any(photo_id in key for key in storage_service.objects)


async def test_delete_photo_blocked_if_sold(
    auth_client: AsyncClient, client: AsyncClient, storage_service, test_session_factory
):
    from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod

    event_id = await _create_event(auth_client)
    files = [("files", ("photo1.jpg", _make_jpeg_bytes(), "image/jpeg"))]
    upload_resp = await auth_client.post(f"/photos/upload?event_id={event_id}", files=files)
    photo_id = upload_resp.json()["uploaded"][0]["id"]

    import uuid

    async with test_session_factory() as db:
        order = Order(
            event_id=uuid.UUID(event_id),
            contact_phone="+2250700000000",
            total_amount=500,
            currency="XOF",
            status=OrderStatus.SUCCESS,
            payment_method=PaymentMethod.MANUAL,
        )
        db.add(order)
        await db.flush()
        db.add(OrderItem(order_id=order.id, photo_id=uuid.UUID(photo_id), unit_price=500))
        await db.commit()

    resp = await auth_client.delete(f"/photos/{photo_id}")
    assert resp.status_code == 409
