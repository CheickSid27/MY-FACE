"""Paiement des packs par Paystack : ouverture du paiement, activation au
retour ou par le webhook signe, refus des signatures fausses et des montants
incomplets. Aucun appel reel a Paystack : le client est remplace."""

import hashlib
import hmac
import json

import pytest

from app.core.config import get_settings
from app.services import paystack
from tests.test_service_photographe import _admin, _create_event, _register, make_client  # noqa: F401

pytestmark = pytest.mark.asyncio

SECRET = "sk_test_cle_de_test"


@pytest.fixture
def fake_paystack(monkeypatch):
    """Paystack simule : `state["tx"]` donne l'etat renvoye par verify."""
    monkeypatch.setattr(get_settings(), "paystack_secret_key", SECRET)
    state: dict = {"init": [], "tx": None}

    async def initialize(email, amount, reference, callback_url, metadata, split=None):
        state["init"].append({"email": email, "amount": amount, "reference": reference, "callback": callback_url})
        return f"https://checkout.paystack.com/{reference}"

    async def verify(reference):
        status, amount = state["tx"] or ("ongoing", 0)
        return paystack.PaystackTransaction(reference=reference, status=status, amount=amount, currency="XOF")

    monkeypatch.setattr(paystack, "initialize_transaction", initialize)
    monkeypatch.setattr(paystack, "verify_transaction", verify)
    return state


def _signed(body: dict) -> tuple[bytes, dict]:
    raw = json.dumps(body).encode()
    sig = hmac.new(SECRET.encode(), raw, hashlib.sha512).hexdigest()
    return raw, {"x-paystack-signature": sig, "content-type": "application/json"}


async def test_paystack_purchase_activates_pack_on_return(make_client, fake_paystack):  # noqa: F811
    photographe = await _register(make_client)
    event_id = await _create_event(photographe)

    resp = await photographe.post(f"/events/{event_id}/pack-purchases/paystack", json={"pack": "evenement"})
    assert resp.status_code == 201, resp.text
    checkout = resp.json()
    assert checkout["authorization_url"].startswith("https://checkout.paystack.com/")
    sent = fake_paystack["init"][0]
    assert sent["amount"] == 10_000
    assert f"/admin/events/{event_id}?paystack={checkout['purchase_id']}" in sent["callback"]

    # page fermee sans payer : toujours en attente
    resp = await photographe.post(f"/pack-purchases/{checkout['purchase_id']}/paystack/verify")
    assert resp.json()["status"] == "pending"

    fake_paystack["tx"] = ("success", 10_000)
    resp = await photographe.post(f"/pack-purchases/{checkout['purchase_id']}/paystack/verify")
    assert resp.json()["status"] == "paid"
    pack = (await photographe.get(f"/events/{event_id}/pack")).json()
    assert pack["pack"]["key"] == "evenement"


async def test_paystack_webhook_needs_valid_signature_and_full_amount(make_client, fake_paystack):  # noqa: F811
    photographe = await _register(make_client)
    event_id = await _create_event(photographe)
    checkout = (await photographe.post(f"/events/{event_id}/pack-purchases/paystack", json={"pack": "pro"})).json()
    reference = fake_paystack["init"][0]["reference"]
    anon = await make_client()
    body = {"event": "charge.success", "data": {"reference": reference}}

    raw, headers = _signed(body)
    resp = await anon.post("/payments/paystack/webhook", content=raw, headers={**headers, "x-paystack-signature": "faux"})
    assert resp.status_code == 401

    # montant inferieur au prix : rien n'est active
    fake_paystack["tx"] = ("success", 100)
    assert (await anon.post("/payments/paystack/webhook", content=raw, headers=headers)).status_code == 200
    assert (await photographe.get(f"/events/{event_id}/pack")).json()["pack"]["key"] == "decouverte"

    fake_paystack["tx"] = ("success", 25_000)
    assert (await anon.post("/payments/paystack/webhook", content=raw, headers=headers)).status_code == 200
    assert (await photographe.get(f"/events/{event_id}/pack")).json()["pack"]["key"] == "pro"
    purchases = (await photographe.get(f"/events/{event_id}/pack")).json()["purchases"]
    assert [p["status"] for p in purchases if p["id"] == checkout["purchase_id"]] == ["paid"]


async def test_new_paystack_attempt_replaces_unfinished_one(make_client, fake_paystack):  # noqa: F811
    photographe = await _register(make_client)
    event_id = await _create_event(photographe)
    first = (await photographe.post(f"/events/{event_id}/pack-purchases/paystack", json={"pack": "evenement"})).json()
    second = await photographe.post(f"/events/{event_id}/pack-purchases/paystack", json={"pack": "evenement"})
    assert second.status_code == 201
    statuses = {p["id"]: p["status"] for p in (await photographe.get(f"/events/{event_id}/pack")).json()["purchases"]}
    assert statuses[first["purchase_id"]] == "cancelled"


async def test_paystack_unavailable_without_key(make_client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(get_settings(), "paystack_secret_key", "")
    photographe = await _register(make_client)
    event_id = await _create_event(photographe)
    resp = await photographe.post(f"/events/{event_id}/pack-purchases/paystack", json={"pack": "evenement"})
    assert resp.status_code == 503
    assert (await (await make_client()).get("/meta/features")).json()["paystack"] is False


# --------------------------------------------------------------------------
# Photos achetees en ligne par les invites (evenements de MYFACE)
# --------------------------------------------------------------------------
from app.models.user import User, UserRole  # noqa: E402
from tests.test_payments import cart_factory  # noqa: E402, F401


async def _event_of_cart(client, session_id: str) -> str:
    return (await client.get(f"/cart/{session_id}")).json()["event_id"]


async def test_guest_pays_online_on_myface_event(client, cart_factory, fake_paystack):  # noqa: F811
    session_id = await cart_factory()
    event_id = await _event_of_cart(client, session_id)
    assert (await client.get(f"/events/{event_id}/public")).json()["online_payment"] is True

    resp = await client.post(
        "/payments/init",
        json={"session_id": session_id, "contact_phone": "+2250700000000", "payment_method": "paystack"},
    )
    assert resp.status_code == 201, resp.text
    order = resp.json()
    assert order["redirect_url"].startswith("https://checkout.paystack.com/")
    assert fake_paystack["init"][0]["amount"] == 1000
    assert f"/event/{event_id}/pay/{order['order_id']}" in fake_paystack["init"][0]["callback"]

    assert (await client.get(f"/payments/status/{order['order_id']}")).json()["status"] == "pending"
    fake_paystack["tx"] = ("success", 1000)
    assert (await client.get(f"/payments/status/{order['order_id']}")).json()["status"] == "success"


async def test_order_webhook_marks_order_paid(client, cart_factory, fake_paystack):  # noqa: F811
    session_id = await cart_factory()
    order = (
        await client.post(
            "/payments/init",
            json={"session_id": session_id, "contact_phone": "+2250700000000", "payment_method": "paystack"},
        )
    ).json()
    reference = fake_paystack["init"][0]["reference"]
    fake_paystack["tx"] = ("success", 1000)
    raw, headers = _signed({"event": "charge.success", "data": {"reference": reference}})
    assert (await client.post("/payments/paystack/webhook", content=raw, headers=headers)).status_code == 200
    assert (await client.get(f"/payments/status/{order['order_id']}")).json()["status"] == "success"


async def test_online_payment_only_for_myface_events(fake_paystack):
    assert paystack.online_payment_available(User(role=UserRole.ADMIN)) is True
    assert paystack.online_payment_available(User(role=UserRole.PHOTOGRAPHE)) is False
    assert paystack.online_payment_available(None) is False


async def test_kiosk_qr_only_for_paystack_pages(client):
    ok = await client.get("/payments/paystack-qr.png", params={"url": "https://checkout.paystack.com/abc123"})
    assert ok.status_code == 200 and ok.headers["content-type"] == "image/png"
    bad = await client.get("/payments/paystack-qr.png", params={"url": "https://exemple.com/piege"})
    assert bad.status_code == 400


# --------------------------------------------------------------------------
# Partage : ventes des photographes versees par Paystack (sous-comptes)
# --------------------------------------------------------------------------
async def test_photographer_payout_splits_guest_payments(make_client, fake_paystack, monkeypatch, seed_photo, storage_service, test_session_factory):  # noqa: F811
    saved = {}

    async def save_subaccount(existing_code, business_name, settlement_bank, account_number, description):
        saved.update(bank=settlement_bank, account=account_number, existing=existing_code)
        return existing_code or "ACCT_test123"

    monkeypatch.setattr(paystack, "save_subaccount", save_subaccount)
    split_sent = {}

    async def initialize(email, amount, reference, callback_url, metadata, split=None):
        split_sent.update(split or {})
        return f"https://checkout.paystack.com/{reference}"

    monkeypatch.setattr(paystack, "initialize_transaction", initialize)

    photographe = await _register(make_client)
    event_id = await _create_event(photographe)
    anon = await make_client()
    assert (await anon.get(f"/events/{event_id}/public")).json()["online_payment"] is False

    resp = await photographe.put("/auth/me/payout", json={"method": "wave", "account": "07 01 02 03 04", "name": "Awa Kone"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["enabled"] is True and resp.json()["account_masked"] == "•• 0304"
    assert saved == {"bank": "WAVE_CI", "account": "0701020304", "existing": None}
    assert (await anon.get(f"/events/{event_id}/public")).json()["online_payment"] is True

    from tests.test_payments import _jpeg_bytes

    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "p.jpg", _jpeg_bytes())
    session_id = (await anon.post("/cart/add", json={"event_id": event_id, "photo_id": photo_id})).json()["session_id"]
    resp = await anon.post(
        "/payments/init", json={"session_id": session_id, "contact_phone": "+2250700000000", "payment_method": "paystack"}
    )
    assert resp.status_code == 201, resp.text
    assert split_sent == {"subaccount": "ACCT_test123", "transaction_charge": 0, "bearer": "subaccount"}

    # desactive : retour au paiement direct
    assert (await photographe.delete("/auth/me/payout")).json()["enabled"] is False
    assert (await anon.get(f"/events/{event_id}/public")).json()["online_payment"] is False


async def test_admin_can_paste_a_subaccount_code(make_client, create_user, fake_paystack):  # noqa: F811
    photographe = await _register(make_client)
    me = (await photographe.get("/auth/me")).json()
    admin = await _admin(make_client, create_user)
    assert (await admin.put(f"/admin/users/{me['id']}/payout-code", json={"subaccount_code": "pas-un-code"})).status_code == 422
    resp = await admin.put(f"/admin/users/{me['id']}/payout-code", json={"subaccount_code": "ACCT_manuel42"})
    assert resp.status_code == 200
    rows = (await admin.get("/admin/users")).json()
    row = next(r for r in rows if r["id"] == me["id"])
    assert row["payout_enabled"] is True and row["paystack_subaccount_code"] == "ACCT_manuel42"
    assert (await photographe.get("/auth/me/payout")).json()["enabled"] is True
