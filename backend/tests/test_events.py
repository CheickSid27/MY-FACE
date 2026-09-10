import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _event_payload(name: str = "Mariage Kone") -> dict:
    return {
        "name": name,
        "date": "2026-09-20T18:00:00Z",
        "location": "Abidjan",
        "pricing": {"unit_price": 1000, "currency": "XOF"},
    }


async def test_create_event(auth_client: AsyncClient):
    resp = await auth_client.post("/events", json=_event_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Mariage Kone"
    assert data["kiosk_token"]
    assert data["pricing"]["unit_price"] == 1000


async def test_create_event_requires_auth(client: AsyncClient):
    resp = await client.post("/events", json=_event_payload())
    assert resp.status_code in (401, 403)


async def test_create_event_invalid_pricing_rejected(auth_client: AsyncClient):
    payload = _event_payload()
    payload["pricing"]["unit_price"] = -5
    resp = await auth_client.post("/events", json=payload)
    assert resp.status_code == 422


async def test_list_events(auth_client: AsyncClient):
    await auth_client.post("/events", json=_event_payload("Gala A"))
    await auth_client.post("/events", json=_event_payload("Gala B"))

    resp = await auth_client.get("/events")
    assert resp.status_code == 200
    names = [e["name"] for e in resp.json()]
    assert "Gala A" in names
    assert "Gala B" in names


async def test_get_event_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/events/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_update_event(auth_client: AsyncClient):
    create_resp = await auth_client.post("/events", json=_event_payload())
    event_id = create_resp.json()["id"]

    resp = await auth_client.patch(f"/events/{event_id}", json={"name": "Nouveau nom"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Nouveau nom"


async def test_delete_event(auth_client: AsyncClient):
    create_resp = await auth_client.post("/events", json=_event_payload())
    event_id = create_resp.json()["id"]

    resp = await auth_client.delete(f"/events/{event_id}")
    assert resp.status_code == 204

    get_resp = await auth_client.get(f"/events/{event_id}")
    assert get_resp.status_code == 404


async def test_get_event_public_no_auth_required(auth_client: AsyncClient, client: AsyncClient):
    create_resp = await auth_client.post("/events", json=_event_payload())
    event_id = create_resp.json()["id"]

    resp = await client.get(f"/events/{event_id}/public")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Mariage Kone"
    assert "kiosk_token" not in data
    assert "organizer_id" not in data


async def test_get_event_public_not_found(client: AsyncClient):
    resp = await client.get("/events/00000000-0000-0000-0000-000000000000/public")
    assert resp.status_code == 404


async def test_public_event_kiosk_detection(auth_client: AsyncClient, client: AsyncClient):
    """Le vrai kiosk_token n'est jamais renvoye par /public (seulement
    is_kiosk, calcule serveur), et un token errone/absent ne doit jamais
    activer le mode borne."""
    create_resp = await auth_client.post("/events", json=_event_payload())
    event_id = create_resp.json()["id"]
    real_token = create_resp.json()["kiosk_token"]

    no_token_resp = await client.get(f"/events/{event_id}/public")
    assert no_token_resp.json()["is_kiosk"] is False
    assert "kiosk_token" not in no_token_resp.json()

    wrong_token_resp = await client.get(f"/events/{event_id}/public", params={"kiosk_token": "wrong"})
    assert wrong_token_resp.json()["is_kiosk"] is False

    right_token_resp = await client.get(f"/events/{event_id}/public", params={"kiosk_token": real_token})
    assert right_token_resp.json()["is_kiosk"] is True
    assert "kiosk_token" not in right_token_resp.json()


async def test_other_user_cannot_access_event(auth_client: AsyncClient, client: AsyncClient, create_user):
    from app.core.security import create_access_token
    from app.models.user import UserRole

    create_resp = await auth_client.post("/events", json=_event_payload())
    event_id = create_resp.json()["id"]

    other = await create_user("other@myface-test.com", "password123", UserRole.PHOTOGRAPHE)

    client.headers["Authorization"] = f"Bearer {create_access_token(str(other.id))}"
    resp = await client.get(f"/events/{event_id}")
    assert resp.status_code == 403
