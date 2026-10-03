"""Photos offertes par l'organisateur : pas de paiement, telechargement direct."""
import io

import pytest
from httpx import AsyncClient
from PIL import Image

pytestmark = pytest.mark.asyncio


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (200, 200), color=(30, 30, 30)).save(buf, format="JPEG")
    return buf.getvalue()


async def _event(auth_client: AsyncClient, pricing: dict) -> str:
    resp = await auth_client.post(
        "/events",
        json={"name": "Gala offert", "date": "2026-12-15T10:00:00Z", "location": "Abidjan", "pricing": pricing},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _cart(client, storage_service, test_session_factory, seed_photo, event_id) -> str:
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())
    resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    return resp.json()["session_id"]


async def test_free_event_can_be_created_without_price(auth_client):
    event_id = await _event(auth_client, {"unit_price": 0, "offert": True})
    resp = await auth_client.get(f"/events/{event_id}")
    assert resp.json()["pricing"]["offert"] is True


async def test_paid_event_still_needs_a_price(auth_client):
    resp = await auth_client.post(
        "/events",
        json={"name": "Gala", "date": "2026-12-15T10:00:00Z", "location": "Abidjan", "pricing": {"unit_price": 0}},
    )
    assert resp.status_code == 422


async def test_free_cart_costs_nothing(auth_client, client, storage_service, test_session_factory, seed_photo):
    event_id = await _event(auth_client, {"unit_price": 0, "offert": True})
    session_id = await _cart(client, storage_service, test_session_factory, seed_photo, event_id)
    resp = await client.get(f"/cart/{session_id}")
    assert resp.json()["pricing"]["total"] == 0


async def test_free_order_is_paid_and_downloadable(auth_client, client, storage_service, test_session_factory, seed_photo):
    event_id = await _event(auth_client, {"unit_price": 0, "offert": True})
    session_id = await _cart(client, storage_service, test_session_factory, seed_photo, event_id)
    resp = await client.post("/payments/offert", json={"session_id": session_id, "contact_phone": "+2250700000000"})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert data["payment_method"] == "offert"
    assert data["total_amount"] == 0

    download = await client.get(f"/download/{data['order_id']}")
    assert download.status_code == 200


async def test_free_route_refused_for_paid_event(auth_client, client, storage_service, test_session_factory, seed_photo):
    event_id = await _event(auth_client, {"unit_price": 450})
    session_id = await _cart(client, storage_service, test_session_factory, seed_photo, event_id)
    resp = await client.post("/payments/offert", json={"session_id": session_id, "contact_phone": "+2250700000000"})
    assert resp.status_code == 400


async def test_download_says_offert(auth_client, client, storage_service, test_session_factory, seed_photo):
    event_id = await _event(auth_client, {"unit_price": 0, "offert": True})
    session_id = await _cart(client, storage_service, test_session_factory, seed_photo, event_id)
    order = (await client.post("/payments/offert", json={"session_id": session_id, "contact_phone": "+2250700000000"})).json()
    download = await client.get(f"/download/{order['order_id']}")
    assert download.json()["offert"] is True
