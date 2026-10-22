"""Espace MYFACE Pro : accueil, ventes a confirmer de tous les evenements,
fil des notifications."""

import pytest

from app.models.order import Order, OrderStatus
from tests.test_payments import _init_wave_order, cart_factory  # noqa: F401
from tests.test_service_photographe import _create_event, _register, make_client  # noqa: F401

pytestmark = pytest.mark.asyncio


async def test_summary_counts_orders_to_confirm_and_sales(client, cart_factory, test_session_factory):  # noqa: F811
    session_id = await cart_factory()
    order = await _init_wave_order(client, session_id)
    assert (await client.post(f"/payments/{order['order_id']}/mark-paid")).status_code == 200

    summary = (await client.get("/workspace/summary")).json()
    assert summary["orders_to_confirm"] == 1
    assert summary["event"]["name"] == "Mariage Payments"
    assert any(item["kind"] == "orders" for item in summary["todo"])

    waiting = (await client.get("/workspace/orders")).json()
    assert [o["id"] for o in waiting] == [order["order_id"]]
    assert waiting[0]["event_name"] == "Mariage Payments"

    activity = (await client.get("/workspace/activity")).json()
    assert activity[0]["kind"] == "order_waiting"

    assert (await client.post(f"/admin/orders/{order['order_id']}/confirm", json={"approved": True})).status_code == 200
    summary = (await client.get("/workspace/summary")).json()
    assert summary["orders_to_confirm"] == 0
    assert summary["sales_today"] == 1000
    paid = (await client.get("/workspace/orders?view=paid")).json()
    assert [o["status"] for o in paid] == ["success"]


async def test_photographer_sees_only_own_events_and_payment_reminder(make_client):  # noqa: F811
    photographe = await _register(make_client)
    event_id = await _create_event(photographe)
    summary = (await photographe.get("/workspace/summary")).json()
    assert summary["events_count"] == 1
    assert summary["event"]["id"] == event_id
    assert any(item["kind"] == "no_payment" for item in summary["todo"])
    assert (await photographe.get("/workspace/orders")).json() == []

    other = await _register(make_client, email="autre@example.com")
    assert (await other.get("/workspace/summary")).json()["events_count"] == 0
