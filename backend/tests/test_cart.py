import pytest
from httpx import AsyncClient
from PIL import Image
import io

pytestmark = pytest.mark.asyncio


def _jpeg_bytes(color=(10, 10, 10)) -> bytes:
    img = Image.new("RGB", (200, 200), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


async def _create_event(auth_client: AsyncClient, unit_price: int = 1000) -> str:
    resp = await auth_client.post(
        "/events",
        json={
            "name": "Bapteme Cart",
            "date": "2026-12-01T10:00:00Z",
            "location": "Abidjan",
            "pricing": {"unit_price": unit_price},
        },
    )
    return resp.json()["id"]


async def test_add_to_cart_creates_session(auth_client, client, storage_service, test_session_factory, seed_photo):
    event_id = await _create_event(auth_client)
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())

    resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["event_id"] == event_id
    assert len(data["items"]) == 1
    assert data["pricing"]["photo_count"] == 1
    assert data["pricing"]["total"] == 1000


async def test_add_second_item_reuses_session(auth_client, client, storage_service, test_session_factory, seed_photo):
    event_id = await _create_event(auth_client)
    photo1 = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes((1, 1, 1)))
    photo2 = await seed_photo(event_id, storage_service, test_session_factory, "p2.jpg", _jpeg_bytes((2, 2, 2)))

    resp1 = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo1})
    session_id = resp1.json()["session_id"]

    resp2 = await client.post(
        "/cart/add", json={"session_id": session_id, "event_id": event_id, "photo_id": photo2}
    )
    assert resp2.status_code == 201
    data = resp2.json()
    assert data["session_id"] == session_id
    assert len(data["items"]) == 2
    assert data["pricing"]["total"] == 2000


async def test_add_same_photo_twice_is_idempotent(auth_client, client, storage_service, test_session_factory, seed_photo):
    event_id = await _create_event(auth_client)
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())

    resp1 = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    session_id = resp1.json()["session_id"]
    resp2 = await client.post(
        "/cart/add", json={"session_id": session_id, "event_id": event_id, "photo_id": photo_id}
    )
    assert len(resp2.json()["items"]) == 1


async def test_add_unknown_photo_returns_404(client):
    import uuid

    resp = await client.post(
        "/cart/add", json={"event_id": str(uuid.uuid4()), "photo_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 404


async def test_get_cart(auth_client, client, storage_service, test_session_factory, seed_photo):
    event_id = await _create_event(auth_client)
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())
    add_resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    session_id = add_resp.json()["session_id"]

    resp = await client.get(f"/cart/{session_id}")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


async def test_get_unknown_cart_returns_404(client):
    import uuid

    resp = await client.get(f"/cart/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_remove_cart_item(auth_client, client, storage_service, test_session_factory, seed_photo):
    event_id = await _create_event(auth_client)
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())
    add_resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    session_id = add_resp.json()["session_id"]
    item_id = add_resp.json()["items"][0]["id"]

    del_resp = await client.delete(f"/cart/{item_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/cart/{session_id}")
    assert get_resp.json()["items"] == []


async def test_pack_pricing_reflected_in_cart(auth_client, client, storage_service, test_session_factory, seed_photo):
    resp = await auth_client.post(
        "/events",
        json={
            "name": "Gala Pack",
            "date": "2026-12-05T10:00:00Z",
            "location": "Abidjan",
            "pricing": {"unit_price": 1000, "packs": [{"count": 2, "price": 1500}]},
        },
    )
    event_id = resp.json()["id"]
    photo1 = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes((1, 1, 1)))
    photo2 = await seed_photo(event_id, storage_service, test_session_factory, "p2.jpg", _jpeg_bytes((2, 2, 2)))

    add1 = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo1})
    session_id = add1.json()["session_id"]
    add2 = await client.post("/cart/add", json={"session_id": session_id, "event_id": event_id, "photo_id": photo2})

    assert add2.json()["pricing"]["total"] == 1500
