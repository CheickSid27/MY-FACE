import hashlib
import hmac
import io
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.config import get_settings
from app.models.order import Order, OrderStatus

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


async def _create_cart_with_photo(
    auth_client, client, storage_service, test_session_factory, seed_photo, configure_payment_method
) -> str:
    event_id = await _create_event(auth_client)
    await configure_payment_method(auth_client, event_id, "wave")
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p1.jpg", _jpeg_bytes())
    add_resp = await client.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})
    return add_resp.json()["session_id"]


async def _init_wave_order(client: AsyncClient, session_id: str, phone: str = "+2250700000000") -> dict:
    resp = await client.post(
        "/payments/init",
        json={"session_id": session_id, "contact_phone": phone, "payment_method": "wave"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _age_order(test_session_factory, order_id: str, minutes: int) -> None:
    async with test_session_factory() as db:
        order = await db.get(Order, uuid.UUID(order_id))
        order.created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        await db.commit()


@pytest.fixture
def cart_factory(auth_client, client, storage_service, test_session_factory, seed_photo, configure_payment_method):
    async def _factory() -> str:
        return await _create_cart_with_photo(
            auth_client, client, storage_service, test_session_factory, seed_photo, configure_payment_method
        )

    return _factory


async def test_init_qr_payment_creates_pending_order(client, cart_factory):
    session_id = await cart_factory()
    data = await _init_wave_order(client, session_id)
    assert data["status"] == "pending"
    assert data["payment_method"] == "wave"
    assert data["total_amount"] == 1000
    assert data["qr_image_url"]
    assert data["merchant_phone"] == "0700000000"


async def test_init_payment_requires_payment_method(client, cart_factory):
    """Plus de repli silencieux vers l'adaptateur 'manual' : il creait des
    commandes 'processing' que personne ne pouvait ni payer ni confirmer."""
    session_id = await cart_factory()
    resp = await client.post("/payments/init", json={"session_id": session_id, "contact_phone": "+2250700000000"})
    assert resp.status_code == 422


async def test_init_payment_manual_rejected(client, cart_factory):
    session_id = await cart_factory()
    resp = await client.post(
        "/payments/init",
        json={"session_id": session_id, "contact_phone": "+2250700000000", "payment_method": "manual"},
    )
    assert resp.status_code == 400


async def test_init_payment_unconfigured_method_rejected(client, cart_factory):
    session_id = await cart_factory()
    resp = await client.post(
        "/payments/init",
        json={"session_id": session_id, "contact_phone": "+2250700000000", "payment_method": "orange_money"},
    )
    assert resp.status_code == 400


async def test_init_payment_unknown_cart_404(client):
    resp = await client.post(
        "/payments/init",
        json={"session_id": str(uuid.uuid4()), "contact_phone": "+2250700000000", "payment_method": "wave"},
    )
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "phone",
    [
        "1123456",  # pas d'indicatif
        "+225 12345678",  # Cote d'Ivoire : 10 chiffres requis
        "+225 0900000000",  # Cote d'Ivoire : prefixe mobile 01/05/07 requis
        "+999 123456789",  # indicatif inconnu
    ],
)
async def test_init_payment_rejects_invalid_phone(client, cart_factory, phone):
    session_id = await cart_factory()
    resp = await client.post(
        "/payments/init", json={"session_id": session_id, "contact_phone": phone, "payment_method": "wave"}
    )
    assert resp.status_code == 422


async def test_init_payment_normalizes_phone_to_e164(client, cart_factory, test_session_factory):
    session_id = await cart_factory()
    data = await _init_wave_order(client, session_id, phone="+225 07 01-02.03 04")
    async with test_session_factory() as db:
        order = await db.get(Order, uuid.UUID(data["order_id"]))
        assert order.contact_phone == "+2250701020304"


async def test_full_qr_flow_mark_paid_then_admin_confirm(client, auth_client, cart_factory, fake_sms):
    session_id = await cart_factory()
    order_id = (await _init_wave_order(client, session_id, phone="+225 07 01 02 03 04"))["order_id"]

    status_resp = await client.get(f"/payments/status/{order_id}")
    assert status_resp.json()["status"] == "pending"

    paid_resp = await client.post(f"/payments/{order_id}/mark-paid")
    assert paid_resp.status_code == 200
    assert paid_resp.json()["status"] == "awaiting_confirmation"

    # Declarer deux fois ne change rien.
    again = await client.post(f"/payments/{order_id}/mark-paid")
    assert again.status_code == 409

    assert fake_sms.sent == []
    confirm = await auth_client.post(f"/admin/orders/{order_id}/confirm", json={"approved": True})
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "success"

    # SMS de confirmation au numero normalise (format attendu par Africa's
    # Talking), avec le lien de telechargement.
    assert len(fake_sms.sent) == 1
    phone, message = fake_sms.sent[0]
    assert phone == "+2250701020304"
    assert f"/order/{order_id}/download" in message

    download = await client.get(f"/download/{order_id}")
    assert download.status_code == 200


async def test_admin_reject_marks_failed(client, auth_client, cart_factory):
    session_id = await cart_factory()
    order_id = (await _init_wave_order(client, session_id))["order_id"]
    await client.post(f"/payments/{order_id}/mark-paid")

    reject = await auth_client.post(f"/admin/orders/{order_id}/confirm", json={"approved": False})
    assert reject.json()["status"] == "failed"
    assert (await client.get(f"/payments/status/{order_id}")).json()["status"] == "failed"


async def test_admin_order_detail_lists_photos(client, auth_client, cart_factory):
    session_id = await cart_factory()
    order_id = (await _init_wave_order(client, session_id))["order_id"]

    resp = await auth_client.get(f"/admin/orders/{order_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["photo_count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["unit_price"] == 1000
    assert data["items"][0]["photo"]["thumbnail_url"]


async def test_stale_pending_order_expires(client, cart_factory, test_session_factory):
    session_id = await cart_factory()
    order_id = (await _init_wave_order(client, session_id))["order_id"]
    await _age_order(test_session_factory, order_id, settings.order_pending_ttl_minutes + 5)

    status_resp = await client.get(f"/payments/status/{order_id}")
    assert status_resp.json()["status"] == "cancelled"

    late = await client.post(f"/payments/{order_id}/mark-paid")
    assert late.status_code == 409


async def test_awaiting_confirmation_never_expires(client, auth_client, cart_factory, test_session_factory):
    """Le client dit avoir paye : seul l'organisateur tranche, jamais
    l'expiration automatique (de l'argent a peut-etre ete envoye)."""
    session_id = await cart_factory()
    order_id = (await _init_wave_order(client, session_id))["order_id"]
    await client.post(f"/payments/{order_id}/mark-paid")
    await _age_order(test_session_factory, order_id, settings.order_pending_ttl_minutes * 10)

    event_id = (await client.get(f"/cart/{session_id}")).json()["event_id"]
    orders = (await auth_client.get(f"/admin/events/{event_id}/orders")).json()
    assert orders[0]["status"] == "awaiting_confirmation"


async def test_admin_list_expires_stale_orders(client, auth_client, cart_factory, test_session_factory):
    session_id = await cart_factory()
    order_id = (await _init_wave_order(client, session_id))["order_id"]
    await _age_order(test_session_factory, order_id, settings.order_pending_ttl_minutes + 1)

    event_id = (await client.get(f"/cart/{session_id}")).json()["event_id"]
    stats = (await auth_client.get(f"/admin/events/{event_id}/stats")).json()
    assert stats["orders_cancelled"] == 1
    assert stats["orders_pending"] == 0


async def test_admin_cancel_then_force_validate(client, auth_client, cart_factory):
    session_id = await cart_factory()
    order_id = (await _init_wave_order(client, session_id))["order_id"]

    cancel = await auth_client.post(f"/admin/orders/{order_id}/cancel")
    assert cancel.json()["status"] == "cancelled"
    assert (await auth_client.post(f"/admin/orders/{order_id}/cancel")).status_code == 409

    # Le client avait en fait paye (transfert visible par l'organisateur) :
    # validation manuelle possible meme apres annulation.
    confirm = await auth_client.post(f"/admin/orders/{order_id}/confirm", json={"approved": True})
    assert confirm.json()["status"] == "success"
    assert (await auth_client.post(f"/admin/orders/{order_id}/confirm", json={"approved": True})).status_code == 409


async def test_webhook_confirms_payment(client, cart_factory, test_session_factory):
    session_id = await cart_factory()
    order_id = (await _init_wave_order(client, session_id))["order_id"]

    # Reference generee cote serveur (pas exposee par l'API publique) :
    # recuperee en base pour simuler un vrai webhook operateur signe.
    async with test_session_factory() as db:
        order = await db.get(Order, uuid.UUID(order_id))
        reference = order.payment_reference

    body = json.dumps({"reference": reference, "status": "success"}).encode()
    resp = await client.post(
        "/payments/webhook", content=body, headers={"X-Signature": _sign(body), "Content-Type": "application/json"}
    )
    assert resp.status_code == 200

    status_resp = await client.get(f"/payments/status/{order_id}")
    assert status_resp.json()["status"] == "success"


async def test_webhook_marks_order_failed(client, cart_factory, test_session_factory):
    session_id = await cart_factory()
    order_id = (await _init_wave_order(client, session_id))["order_id"]

    async with test_session_factory() as db:
        order = await db.get(Order, uuid.UUID(order_id))
        reference = order.payment_reference

    body = json.dumps({"reference": reference, "status": "failed"}).encode()
    resp = await client.post(
        "/payments/webhook", content=body, headers={"X-Signature": _sign(body), "Content-Type": "application/json"}
    )
    assert resp.status_code == 200
    assert (await client.get(f"/payments/status/{order_id}")).json()["status"] == OrderStatus.FAILED.value


async def test_webhook_rejects_invalid_signature(client):
    body = json.dumps({"reference": "QR-doesnotexist", "status": "success"}).encode()
    resp = await client.post(
        "/payments/webhook", content=body, headers={"X-Signature": "invalid", "Content-Type": "application/json"}
    )
    assert resp.status_code == 401


async def test_webhook_valid_signature_unknown_reference_404(client):
    body = json.dumps({"reference": "QR-doesnotexist", "status": "success"}).encode()
    resp = await client.post(
        "/payments/webhook",
        content=body,
        headers={"X-Signature": _sign(body), "Content-Type": "application/json"},
    )
    assert resp.status_code == 404


async def test_payment_status_unknown_order_404(client):
    resp = await client.get(f"/payments/status/{uuid.uuid4()}")
    assert resp.status_code == 404
