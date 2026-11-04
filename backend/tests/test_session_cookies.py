"""Session dans des cookies proteges (HttpOnly, SameSite=Strict) au lieu du
stockage du navigateur, que le code de la page peut lire."""

import pytest
from httpx import AsyncClient

from app.services.session_cookies import ACCESS_COOKIE, REFRESH_COOKIE

pytestmark = pytest.mark.asyncio


def _cookies(resp) -> dict[str, str]:
    """Cookies poses par la reponse, avec leurs attributs bruts."""
    out = {}
    for header in resp.headers.get_list("set-cookie"):
        name, rest = header.split("=", 1)
        out[name] = rest
    return out


def _value(raw: str) -> str:
    return raw.split(";", 1)[0]


async def test_login_sets_protected_cookies_and_they_work_alone(client: AsyncClient, admin_user):
    resp = await client.post("/auth/login", json={"email": "admin@myface-test.com", "password": "testpassword123"})
    assert resp.status_code == 200, resp.text
    cookies = _cookies(resp)
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        attrs = cookies[name].lower()
        assert "httponly" in attrs and "samesite=strict" in attrs and "path=/" in attrs

    access, refresh = _value(cookies[ACCESS_COOKIE]), _value(cookies[REFRESH_COOKIE])
    client.headers.pop("Authorization", None)
    client.cookies.clear()

    # le cookie seul suffit, sans en-tete Authorization
    me = await client.get("/auth/me", headers={"Cookie": f"{ACCESS_COOKIE}={access}"})
    assert me.status_code == 200 and me.json()["email"] == "admin@myface-test.com"

    # renouvellement sans corps : le cookie de renouvellement suffit
    renewed = await client.post("/auth/refresh", headers={"Cookie": f"{REFRESH_COOKIE}={refresh}"})
    assert renewed.status_code == 200, renewed.text
    assert ACCESS_COOKIE in _cookies(renewed)

    # deconnexion : les deux cookies sont effaces
    out = await client.post("/auth/logout")
    assert out.status_code == 204
    gone = _cookies(out)
    assert 'max-age=0' in gone[ACCESS_COOKIE].lower() and 'max-age=0' in gone[REFRESH_COOKIE].lower()


async def test_no_token_no_cookie_is_refused(client: AsyncClient):
    client.headers.pop("Authorization", None)
    client.cookies.clear()
    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.post("/auth/refresh")).status_code == 401
