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

    async def initialize(email, amount, reference, callback_url, metadata):
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
