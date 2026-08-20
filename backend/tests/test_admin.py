import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_list_users_requires_admin(client: AsyncClient):
    resp = await client.get("/admin/users")
    assert resp.status_code in (401, 403)


async def test_admin_can_list_users(auth_client: AsyncClient):
    resp = await auth_client.get("/admin/users")
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert "admin@myface-test.com" in emails


async def test_admin_can_create_photographe(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/admin/users",
        json={"email": "photographe1@myface-test.com", "password": "password123", "role": "photographe"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "photographe"


async def test_create_user_duplicate_email_rejected(auth_client: AsyncClient):
    payload = {"email": "dup@myface-test.com", "password": "password123", "role": "photographe"}
    first = await auth_client.post("/admin/users", json=payload)
    assert first.status_code == 201

    second = await auth_client.post("/admin/users", json=payload)
    assert second.status_code == 409


async def test_photographe_cannot_access_admin_users(auth_client: AsyncClient, client: AsyncClient, create_user):
    from app.core.security import create_access_token
    from app.models.user import UserRole

    photographe = await create_user("photog2@myface-test.com", "password123", UserRole.PHOTOGRAPHE)
    client.headers["Authorization"] = f"Bearer {create_access_token(str(photographe.id))}"

    resp = await client.get("/admin/users")
    assert resp.status_code == 403


async def test_admin_cannot_delete_self(auth_client: AsyncClient, admin_user):
    resp = await auth_client.delete(f"/admin/users/{admin_user.id}")
    assert resp.status_code == 400


async def test_admin_can_delete_user(auth_client: AsyncClient):
    create_resp = await auth_client.post(
        "/admin/users",
        json={"email": "todelete@myface-test.com", "password": "password123", "role": "photographe"},
    )
    user_id = create_resp.json()["id"]

    resp = await auth_client.delete(f"/admin/users/{user_id}")
    assert resp.status_code == 204

    list_resp = await auth_client.get("/admin/users")
    assert user_id not in [u["id"] for u in list_resp.json()]


async def test_cannot_delete_user_with_events(auth_client: AsyncClient):
    create_resp = await auth_client.post(
        "/admin/users",
        json={"email": "organizer@myface-test.com", "password": "password123", "role": "admin"},
    )
    user_id = create_resp.json()["id"]

    from app.core.security import create_access_token

    organizer_client_headers = {"Authorization": f"Bearer {create_access_token(user_id)}"}
    await auth_client.post(
        "/events",
        json={
            "name": "Evenement organisateur",
            "date": "2026-12-20T10:00:00Z",
            "location": "Abidjan",
            "pricing": {"unit_price": 1000},
        },
        headers=organizer_client_headers,
    )

    resp = await auth_client.delete(f"/admin/users/{user_id}")
    assert resp.status_code == 409
