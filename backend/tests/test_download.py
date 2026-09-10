import io
import uuid

import pytest
from httpx import AsyncClient
from PIL import Image

from app.models.order import Order, OrderStatus

pytestmark = pytest.mark.asyncio


def _jpeg_bytes(color=(10, 10, 10)) -> bytes:
    img = Image.new("RGB", (200, 200), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


async def _create_paid_order(auth_client, client, storage_service, test_session_factory, seed_photo) -> str:
    event_resp = await auth_client.post(
        "/events",
        json={
            "name": "Gala Download",
            "date": "2026-12-15T10:00:00Z",
            "location": "Abidjan",
            "pricing": {"unit_price": 1000},
        },
    )
    event_id = event_resp.json()["id"]
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())

    add_resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    session_id = add_resp.json()["session_id"]

    init_resp = await client.post(
        "/payments/init", json={"session_id": session_id, "contact_phone": "+2250700000000"}
    )
    order_id = init_resp.json()["order_id"]

    # Plus d'endpoint de simulation (paiement reel = QR marchand + validation
    # manuelle organisateur, voir routers/payments.py mark_paid + admin
    # confirm_order) : on passe l'etat en base directement pour isoler le
    # test du flux de telechargement de celui de confirmation du paiement.
    async with test_session_factory() as db:
        order = await db.get(Order, uuid.UUID(order_id))
        order.status = OrderStatus.SUCCESS
        await db.commit()

    return order_id


async def test_download_blocked_before_payment(auth_client, client, storage_service, test_session_factory, seed_photo):
    event_resp = await auth_client.post(
        "/events",
        json={
            "name": "Gala Unpaid",
            "date": "2026-12-16T10:00:00Z",
            "location": "Abidjan",
            "pricing": {"unit_price": 1000},
        },
    )
    event_id = event_resp.json()["id"]
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())
    add_resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    session_id = add_resp.json()["session_id"]
    init_resp = await client.post(
        "/payments/init", json={"session_id": session_id, "contact_phone": "+2250700000000"}
    )
    order_id = init_resp.json()["order_id"]

    resp = await client.get(f"/download/{order_id}")
    assert resp.status_code == 403


async def test_download_available_after_payment(auth_client, client, storage_service, test_session_factory, seed_photo):
    order_id = await _create_paid_order(auth_client, client, storage_service, test_session_factory, seed_photo)

    resp = await client.get(f"/download/{order_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["photos"]) == 1
    assert data["photos"][0]["url"].startswith("http://test-storage.local/")


async def test_download_carries_print_requested(
    auth_client, client, storage_service, test_session_factory, seed_photo
):
    event_resp = await auth_client.post(
        "/events",
        json={
            "name": "Gala Print",
            "date": "2026-12-18T10:00:00Z",
            "location": "Abidjan",
            "pricing": {"unit_price": 1000, "print_unit_price": 150},
        },
    )
    event_id = event_resp.json()["id"]
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())

    add_resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    session_id = add_resp.json()["session_id"]
    item_id = add_resp.json()["items"][0]["id"]
    await client.patch(f"/cart/{item_id}", json={"print_requested": True})

    init_resp = await client.post(
        "/payments/init", json={"session_id": session_id, "contact_phone": "+2250700000000"}
    )
    order_id = init_resp.json()["order_id"]

    async with test_session_factory() as db:
        order = await db.get(Order, uuid.UUID(order_id))
        order.status = OrderStatus.SUCCESS
        await db.commit()

    resp = await client.get(f"/download/{order_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["photos"]) == 1
    assert data["photos"][0]["print_requested"] is True


async def test_download_unknown_order_404(client):
    import uuid

    resp = await client.get(f"/download/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_qr_available_after_payment(auth_client, client, storage_service, test_session_factory, seed_photo):
    order_id = await _create_paid_order(auth_client, client, storage_service, test_session_factory, seed_photo)

    resp = await client.get(f"/download/{order_id}/qr.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) > 0


async def test_qr_blocked_before_payment(auth_client, client, storage_service, test_session_factory, seed_photo):
    event_resp = await auth_client.post(
        "/events",
        json={
            "name": "Gala QR Unpaid",
            "date": "2026-12-17T10:00:00Z",
            "location": "Abidjan",
            "pricing": {"unit_price": 1000},
        },
    )
    event_id = event_resp.json()["id"]
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())
    add_resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    session_id = add_resp.json()["session_id"]
    init_resp = await client.post(
        "/payments/init", json={"session_id": session_id, "contact_phone": "+2250700000000"}
    )
    order_id = init_resp.json()["order_id"]

    resp = await client.get(f"/download/{order_id}/qr.png")
    assert resp.status_code == 403
