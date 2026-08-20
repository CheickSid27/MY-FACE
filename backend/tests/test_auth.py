import pytest
from httpx import AsyncClient

from app.models.user import User

pytestmark = pytest.mark.asyncio


async def test_login_success(client: AsyncClient, admin_user: User):
    resp = await client.post(
        "/auth/login", json={"email": "admin@myface-test.com", "password": "testpassword123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password(client: AsyncClient, admin_user: User):
    resp = await client.post(
        "/auth/login", json={"email": "admin@myface-test.com", "password": "wrongpassword"}
    )
    assert resp.status_code == 401


async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post(
        "/auth/login", json={"email": "nobody@myface-test.com", "password": "whatever123"}
    )
    assert resp.status_code == 401


async def test_refresh_token(client: AsyncClient, admin_user: User):
    login_resp = await client.post(
        "/auth/login", json={"email": "admin@myface-test.com", "password": "testpassword123"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_refresh_with_access_token_rejected(client: AsyncClient, admin_user: User):
    login_resp = await client.post(
        "/auth/login", json={"email": "admin@myface-test.com", "password": "testpassword123"}
    )
    access_token = login_resp.json()["access_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code in (401, 403)


async def test_me_with_valid_token(auth_client: AsyncClient, admin_user: User):
    resp = await auth_client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@myface-test.com"
