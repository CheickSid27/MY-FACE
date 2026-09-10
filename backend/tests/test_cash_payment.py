import io

import pytest
from httpx import AsyncClient
from PIL import Image

pytestmark = pytest.mark.asyncio


def _jpeg_bytes(color=(10, 10, 10)) -> bytes:
    img = Image.new("RGB", (200, 200), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


async def _create_event(auth_client: AsyncClient, cash_enabled: bool = True) -> str:
    resp = await auth_client.post(
        "/events",
        json={
            "name": "Bapteme Cash",
            "date": "2026-12-15T10:00:00Z",
            "location": "Abidjan",
            "pricing": {"unit_price": 1000},
        },
    )
    event_id = resp.json()["id"]
    if cash_enabled:
        await auth_client.patch(f"/events/{event_id}", json={"cash_enabled": True})
    return event_id


async def _create_cart(auth_client, client, storage_service, test_session_factory, seed_photo, event_id) -> str:
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())
    add_resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    return add_resp.json()["session_id"]


async def test_cash_payment_requires_event_opt_in(
    auth_client, client, storage_service, test_session_factory, seed_photo
):
    event_id = await _create_event(auth_client, cash_enabled=False)
    session_id = await _create_cart(auth_client, client, storage_service, test_session_factory, seed_photo, event_id)

    resp = await client.post(
        "/payments/init",
        json={"session_id": session_id, "contact_phone": "+2250700000000", "payment_method": "cash"},
    )
    assert resp.status_code == 400


async def test_cash_payment_goes_straight_to_awaiting_confirmation(
    auth_client, client, storage_service, test_session_factory, seed_photo
):
    event_id = await _create_event(auth_client, cash_enabled=True)
    session_id = await _create_cart(auth_client, client, storage_service, test_session_factory, seed_photo, event_id)

    resp = await client.post(
        "/payments/init",
        json={"session_id": session_id, "contact_phone": "+2250700000000", "payment_method": "cash"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "awaiting_confirmation"
    assert data["payment_method"] == "cash"
    assert "comptoir" in data["instructions"].lower()

    # Pas de QR pour l'especes : ces champs restent absents/nuls.
    assert data.get("qr_image_url") is None

    # Le staff confirme ensuite comme pour le flux QR classique.
    status_resp = await client.get(f"/payments/status/{data['order_id']}")
    assert status_resp.json()["status"] == "awaiting_confirmation"


async def test_cash_order_carries_print_selection(
    auth_client, client, storage_service, test_session_factory, seed_photo
):
    resp = await auth_client.post(
        "/events",
        json={
            "name": "Gala Cash Print",
            "date": "2026-12-16T10:00:00Z",
            "location": "Abidjan",
            "pricing": {"unit_price": 1000, "print_unit_price": 150},
        },
    )
    event_id = resp.json()["id"]
    await auth_client.patch(f"/events/{event_id}", json={"cash_enabled": True})

    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())
    add_resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    session_id = add_resp.json()["session_id"]
    item_id = add_resp.json()["items"][0]["id"]
    await client.patch(f"/cart/{item_id}", json={"print_requested": True})

    init_resp = await client.post(
        "/payments/init",
        json={"session_id": session_id, "contact_phone": "+2250700000000", "payment_method": "cash"},
    )
    assert init_resp.status_code == 201
    assert init_resp.json()["total_amount"] == 1150
