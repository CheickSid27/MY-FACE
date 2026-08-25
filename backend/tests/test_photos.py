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
