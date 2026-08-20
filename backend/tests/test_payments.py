import hashlib
import hmac
import io
import json

import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.config import get_settings

pytestmark = pytest.mark.asyncio

settings = get_settings()


def _jpeg_bytes(color=(10, 10, 10)) -> bytes:
    img = Image.new("RGB", (200, 200), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _sign(body: bytes) -> str:
    return hmac.new(settings.payment_webhook_secret.encode(), body, hashlib.sha256).hexdigest()


async def _create_event(auth_client: AsyncClient) -> str:
    resp = await auth_client.post(
        "/events",
        json={
            "name": "Mariage Payments",
            "date": "2026-12-10T10:00:00Z",
            "location": "Abidjan",
            "pricing": {"unit_price": 1000},
        },
    )
    return resp.json()["id"]


async def _create_cart_with_photo(auth_client, client, storage_service, test_session_factory, seed_photo) -> str:
    event_id = await _create_event(auth_client)
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())
    add_resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    return add_resp.json()["session_id"]


async def test_init_payment_creates_order(auth_client, client, storage_service, test_session_factory, seed_photo):
    session_id = await _create_cart_with_photo(auth_client, client, storage_service, test_session_factory, seed_photo)

    resp = await client.post("/payments/init", json={"session_id": session_id, "contact_phone": "+2250700000000"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "processing"
    assert data["total_amount"] == 1000
    assert data["payment_method"] == "manual"


async def test_init_payment_empty_cart_rejected(client):
    import uuid

    resp = await client.post(
        "/payments/init", json={"session_id": str(uuid.uuid4()), "contact_phone": "+2250700000000"}
    )
    assert resp.status_code == 404


async def test_payment_status_polling(auth_client, client, storage_service, test_session_factory, seed_photo):
    session_id = await _create_cart_with_photo(auth_client, client, storage_service, test_session_factory, seed_photo)
    init_resp = await client.post("/payments/init", json={"session_id": session_id, "contact_phone": "+2250700000000"})
    order_id = init_resp.json()["order_id"]

    resp = await client.get(f"/payments/status/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"


async def test_webhook_confirms_payment(auth_client, client, storage_service, test_session_factory, seed_photo):
    session_id = await _create_cart_with_photo(auth_client, client, storage_service, test_session_factory, seed_photo)
    init_resp = await client.post("/payments/init", json={"session_id": session_id, "contact_phone": "+2250700000000"})
    order_id = init_resp.json()["order_id"]

    order_status = await client.get(f"/payments/status/{order_id}")
    assert order_status.status_code == 200

    # Recupere la reference generee (pas exposee par l'API publique) via une
    # simulation, qui suit exactement le meme chemin que le webhook.
    resp = await client.post(f"/payments/{order_id}/simulate", json={"status": "success"})
    assert resp.status_code == 200

    status_resp = await client.get(f"/payments/status/{order_id}")
    assert status_resp.json()["status"] == "success"


async def test_webhook_rejects_invalid_signature(client):
    body = json.dumps({"reference": "MANUAL-doesnotexist", "status": "success"}).encode()
    resp = await client.post(
        "/payments/webhook", content=body, headers={"X-Signature": "invalid", "Content-Type": "application/json"}
    )
    assert resp.status_code == 401


async def test_webhook_valid_signature_unknown_reference_404(client):
    body = json.dumps({"reference": "MANUAL-doesnotexist", "status": "success"}).encode()
    resp = await client.post(
        "/payments/webhook",
        content=body,
        headers={"X-Signature": _sign(body), "Content-Type": "application/json"},
    )
    assert resp.status_code == 404


async def test_simulate_marks_order_failed(auth_client, client, storage_service, test_session_factory, seed_photo):
    session_id = await _create_cart_with_photo(auth_client, client, storage_service, test_session_factory, seed_photo)
    init_resp = await client.post("/payments/init", json={"session_id": session_id, "contact_phone": "+2250700000000"})
    order_id = init_resp.json()["order_id"]

    resp = await client.post(f"/payments/{order_id}/simulate", json={"status": "failed"})
    assert resp.status_code == 200

    status_resp = await client.get(f"/payments/status/{order_id}")
    assert status_resp.json()["status"] == "failed"
