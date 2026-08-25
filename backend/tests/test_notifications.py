import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_get_vapid_public_key(client: AsyncClient):
    resp = await client.get("/notifications/vapid-public-key")
    assert resp.status_code == 200
    assert "public_key" in resp.json()


async def test_subscribe_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/notifications/subscribe",
        json={"endpoint": "https://push.example.com/abc", "keys": {"p256dh": "x", "auth": "y"}},
    )
    assert resp.status_code in (401, 403)


async def test_subscribe_and_unsubscribe(auth_client: AsyncClient):
    payload = {
        "endpoint": "https://push.example.com/subscription-1",
        "keys": {"p256dh": "fake-p256dh-key", "auth": "fake-auth-secret"},
    }
    resp = await auth_client.post("/notifications/subscribe", json=payload)
    assert resp.status_code == 204

    # Re-souscrire avec le meme endpoint (ex: navigateur qui rafraichit ses
    # cles) doit mettre a jour, pas dupliquer (contrainte unique sur endpoint).
    resp2 = await auth_client.post("/notifications/subscribe", json=payload)
    assert resp2.status_code == 204

    resp3 = await auth_client.post("/notifications/unsubscribe", json={"endpoint": payload["endpoint"]})
    assert resp3.status_code == 204
