"""Comptes et securite (inspection du 21/10/2026) : verification de l'adresse
e-mail des photographes, mot de passe oublie, sessions fermees au
changement de mot de passe, limites de connexion, evenements gratuits
limites, validation des formulaires."""

import io
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.core.config import get_settings
from app.core.security import create_access_token, create_email_verification_token
from app.main import app
from app.models.user import UserRole
from app.services.email import ConsoleEmailService, get_email_service

pytestmark = pytest.mark.asyncio

settings = get_settings()

PHOTOGRAPHE = {
    "email": "Nouveau.Studio@example.com",
    "password": "motdepasse123",
    "display_name": "Yao Kouassi",
    "studio_name": "Studio Yao",
    "phone": "+225 05 01 02 03 04",
    "city": "Bouake",
    "accept_terms": True,
}

EVENT = {
    "name": "Bapteme",
    "date": "2026-12-05T10:00:00Z",
    "location": "Yamoussoukro",
    "pricing": {"unit_price": 500},
}


@pytest_asyncio.fixture
async def emails(client: AsyncClient) -> ConsoleEmailService:
    """E-mails « envoyes » pendant le test, sans aucun envoi reel."""
    service = ConsoleEmailService()
    app.dependency_overrides[get_email_service] = lambda: service
    return service


@pytest_asyncio.fixture
async def make_client(client: AsyncClient):
    opened: list[AsyncClient] = []

    async def _make(token: str | None = None) -> AsyncClient:
        ac = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        if token:
            ac.headers["Authorization"] = f"Bearer {token}"
        opened.append(ac)
        return ac

    yield _make
    for ac in opened:
        await ac.aclose()


@pytest.fixture
def enforce_verification(monkeypatch):
    monkeypatch.setattr(settings, "email_verification_required", "true")


def _token_from_link(text: str) -> str:
    link = next(word for word in text.split() if word.startswith("http"))
    return parse_qs(urlparse(link).query)["token"][0]


async def _register(make_client, **overrides) -> tuple[AsyncClient, dict]:
    anon = await make_client()
    resp = await anon.post("/auth/register", json={**PHOTOGRAPHE, **overrides})
    assert resp.status_code == 201, resp.text
    tokens = resp.json()
    return await make_client(tokens["access_token"]), tokens


async def _admin(make_client, create_user) -> AsyncClient:
    admin = await create_user("admin@myface-test.com", "testpassword123", UserRole.ADMIN)
    return await make_client(create_access_token(str(admin.id)))


# --------------------------------------------------------------------------
# Verification de l'adresse e-mail
# --------------------------------------------------------------------------


async def test_register_sends_verification_link(make_client, emails):
    photographe, _ = await _register(make_client)

    me = (await photographe.get("/auth/me")).json()
    assert me["email"] == "nouveau.studio@example.com"
    assert me["email_verified"] is False

    assert len(emails.sent) == 1
    message = emails.sent[0]
    assert message.to == "nouveau.studio@example.com"
    assert "/verifier-email?token=" in message.text

    anon = await make_client()
    resp = await anon.post("/auth/verify-email", json={"token": _token_from_link(message.text)})
    assert resp.status_code == 200, resp.text
    assert (await photographe.get("/auth/me")).json()["email_verified"] is True

    # un deuxieme clic sur le meme lien ne casse rien
    assert (await anon.post("/auth/verify-email", json={"token": _token_from_link(message.text)})).status_code == 200


async def test_verify_email_rejects_bad_links(make_client, emails):
    photographe, tokens = await _register(make_client)
    anon = await make_client()

    # un jeton de connexion n'est pas un lien de confirmation
    resp = await anon.post("/auth/verify-email", json={"token": tokens["access_token"]})
    assert resp.status_code == 400
    # lien emis pour une autre adresse (adresse changee depuis)
    me = (await photographe.get("/auth/me")).json()
    other = create_email_verification_token(me["id"], "autre@example.com")
    assert (await anon.post("/auth/verify-email", json={"token": other})).status_code == 400
    assert (await anon.post("/auth/verify-email", json={"token": "n-importe-quoi"})).status_code == 400
    assert (await photographe.get("/auth/me")).json()["email_verified"] is False


async def test_unverified_photographer_cannot_publish(make_client, emails, enforce_verification):
    photographe, _ = await _register(make_client)

    assert (await photographe.get("/auth/me")).json()["must_verify_email"] is True
    resp = await photographe.post("/events", json=EVENT)
    assert resp.status_code == 403
    assert "Confirmez" in resp.json()["detail"]

    token = _token_from_link(emails.sent[0].text)
    await (await make_client()).post("/auth/verify-email", json={"token": token})
    assert (await photographe.post("/events", json=EVENT)).status_code == 201


async def test_admin_is_never_blocked_by_verification(make_client, create_user, enforce_verification):
    admin = await _admin(make_client, create_user)
    assert (await admin.post("/events", json=EVENT)).status_code == 201


async def test_verification_not_required_without_email_sending(make_client, emails, monkeypatch):
    """Sans SMTP, personne ne pourrait confirmer son adresse : la regle ne
    s'applique pas (mode « auto »)."""
    monkeypatch.setattr(settings, "email_verification_required", "auto")
    monkeypatch.setattr(settings, "smtp_host", "")
    photographe, _ = await _register(make_client)
    assert (await photographe.get("/auth/me")).json()["must_verify_email"] is False
    assert (await photographe.post("/events", json=EVENT)).status_code == 201


async def test_resend_verification_is_limited(make_client, emails):
    photographe, _ = await _register(make_client)
    for _ in range(3):
        assert (await photographe.post("/auth/resend-verification")).json()["status"] == "sent"
    assert (await photographe.post("/auth/resend-verification")).status_code == 429
    assert len(emails.sent) == 4  # inscription + 3 renvois


async def test_admin_can_verify_by_hand(make_client, create_user, emails, enforce_verification):
    photographe, _ = await _register(make_client)
    admin = await _admin(make_client, create_user)
    user_id = (await photographe.get("/auth/me")).json()["id"]

    resp = await admin.patch(f"/admin/users/{user_id}", json={"email_verified": True})
    assert resp.status_code == 200
    assert resp.json()["email_verified"] is True
    assert (await photographe.post("/events", json=EVENT)).status_code == 201

    # un photographe ne peut pas se valider lui-meme
    assert (await photographe.patch(f"/admin/users/{user_id}", json={"email_verified": True})).status_code == 403


# --------------------------------------------------------------------------
# Mot de passe oublie, sessions
# --------------------------------------------------------------------------


async def test_forgot_password_full_flow(make_client, emails):
    await _register(make_client)
    emails.sent.clear()
    anon = await make_client()

    resp = await anon.post("/auth/forgot-password", json={"email": "NOUVEAU.studio@example.com"})
    assert resp.status_code == 202
    assert len(emails.sent) == 1
    token = _token_from_link(emails.sent[0].text)

    resp = await anon.post("/auth/reset-password", json={"token": token, "new_password": "nouveau2026"})
    assert resp.status_code == 204, resp.text

    login = await anon.post("/auth/login", json={"email": PHOTOGRAPHE["email"], "password": "nouveau2026"})
    assert login.status_code == 200
    old = await anon.post("/auth/login", json={"email": PHOTOGRAPHE["email"], "password": "motdepasse123"})
    assert old.status_code == 401
    # le lien ne sert qu'une fois
    again = await anon.post("/auth/reset-password", json={"token": token, "new_password": "encore2026x"})
    assert again.status_code == 400
    # recu dans sa boite : l'adresse est confirmee au passage
    relogged = await make_client(login.json()["access_token"])
    assert (await relogged.get("/auth/me")).json()["email_verified"] is True


async def test_forgot_password_does_not_reveal_accounts(make_client, emails):
    anon = await make_client()
    resp = await anon.post("/auth/forgot-password", json={"email": "personne@example.com"})
    assert resp.status_code == 202
    assert emails.sent == []


async def test_reset_password_rejects_other_tokens(make_client, emails):
    _, tokens = await _register(make_client)
    anon = await make_client()
    resp = await anon.post(
        "/auth/reset-password", json={"token": tokens["access_token"], "new_password": "nouveau2026"}
    )
    assert resp.status_code == 400


async def test_password_change_closes_other_sessions(make_client, create_user):
    user = await create_user("admin@myface-test.com", "testpassword123", UserRole.ADMIN)
    # session ouverte il y a une minute (jeton emis avant le changement)
    old_token = jwt.encode(
        {
            "sub": str(user.id),
            "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(minutes=1),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    other_session = await make_client(old_token)
    assert (await other_session.get("/auth/me")).status_code == 200

    current = await make_client(create_access_token(str(user.id)))
    resp = await current.post(
        "/auth/password", json={"current_password": "testpassword123", "new_password": "nouveau2026"}
    )
    assert resp.status_code == 200, resp.text
    assert (await other_session.get("/auth/me")).status_code == 401

    fresh = await make_client(resp.json()["access_token"])
    assert (await fresh.get("/auth/me")).status_code == 200


async def test_weak_passwords_are_refused(make_client):
    anon = await make_client()
    for weak in ("12345678", "motdepasse", "abcdefghij", "1234567890123"):
        resp = await anon.post("/auth/register", json={**PHOTOGRAPHE, "password": weak})
        assert resp.status_code == 422, weak


async def test_login_is_throttled_per_account(make_client, emails):
    await _register(make_client)
    anon = await make_client()
    for _ in range(10):
        resp = await anon.post("/auth/login", json={"email": PHOTOGRAPHE["email"], "password": "mauvais123"})
        assert resp.status_code == 401
    blocked = await anon.post("/auth/login", json={"email": PHOTOGRAPHE["email"], "password": "motdepasse123"})
    assert blocked.status_code == 429


async def test_successful_logins_are_not_throttled(make_client, emails):
    await _register(make_client)
    anon = await make_client()
    for _ in range(12):
        resp = await anon.post("/auth/login", json={"email": PHOTOGRAPHE["email"], "password": "motdepasse123"})
        assert resp.status_code == 200


async def test_admin_created_accounts_are_case_insensitive(make_client, create_user):
    admin = await _admin(make_client, create_user)
    resp = await admin.post(
        "/admin/users", json={"email": "Photo.Graphe@Example.com", "password": "password123", "role": "photographe"}
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "photo.graphe@example.com"
    assert resp.json()["email_verified"] is True
    dup = await admin.post(
        "/admin/users", json={"email": "PHOTO.GRAPHE@example.com", "password": "password123", "role": "photographe"}
    )
    assert dup.status_code == 409


# --------------------------------------------------------------------------
# Evenements gratuits, formulaires
# --------------------------------------------------------------------------


async def test_free_events_are_limited(make_client, create_user, emails):
    photographe, _ = await _register(make_client)
    ids = []
    for i in range(settings.free_events_per_account):
        resp = await photographe.post("/events", json={**EVENT, "name": f"Evenement {i}"})
        assert resp.status_code == 201
        ids.append(resp.json()["id"])

    resp = await photographe.post("/events", json=EVENT)
    assert resp.status_code == 403
    assert "événements gratuits" in resp.json()["detail"]

    # un evenement passe au pack Evenement libere une place
    admin = await _admin(make_client, create_user)
    assert (await admin.put(f"/admin/events/{ids[0]}/pack", json={"pack": "evenement"})).status_code == 200
    assert (await photographe.post("/events", json=EVENT)).status_code == 201


@pytest.mark.parametrize(
    "change",
    [
        {"name": "   "},
        {"location": ""},
        {"date": "1900-01-01T10:00:00Z"},
        {"pricing": {"unit_price": 500, "currency": "fcfa"}},
        {"pricing": {"unit_price": 50_000_000}},
        {"pricing": {"unit_price": 500, "packs": [{"count": 5, "price": 999_999_999}]}},
    ],
)
async def test_event_form_rejects_invalid_values(make_client, create_user, change):
    admin = await _admin(make_client, create_user)
    resp = await admin.post("/events", json={**EVENT, **change})
    assert resp.status_code == 422, change


async def test_event_names_are_trimmed(make_client, create_user):
    admin = await _admin(make_client, create_user)
    resp = await admin.post("/events", json={**EVENT, "name": "  Gala  ", "location": " Abidjan "})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Gala"
    assert resp.json()["location"] == "Abidjan"


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), color=(0, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


async def test_merchant_number_and_qr_are_checked(make_client, create_user, storage_service):
    admin = await _admin(make_client, create_user)
    event_id = (await admin.post("/events", json=EVENT)).json()["id"]
    url = f"/events/{event_id}/payment-methods/wave"

    resp = await admin.put(url, data={"phone_number": "07 01 02 03 04"}, files={"qr_image": ("qr.png", _png(), "image/png")})
    assert resp.status_code == 200, resp.text
    assert resp.json()["phone_number"] == "+2250701020304"
    assert f"events/{event_id}/payment_qr/wave.png" in storage_service.objects

    bad_number = await admin.put(url, data={"phone_number": "123456"})
    assert bad_number.status_code == 400
    not_an_image = await admin.put(
        url, data={"phone_number": "0701020304"}, files={"qr_image": ("qr.png", b"<html>pas une image</html>", "image/png")}
    )
    assert not_an_image.status_code == 400
    # le nom du fichier ne decide jamais du chemin dans le stockage
    tricky = await admin.put(
        url, data={"phone_number": "0701020304"}, files={"qr_image": ("x.png/../../evil", _png(), "image/png")}
    )
    assert tricky.status_code == 200
    assert not any("evil" in key for key in storage_service.objects)


async def test_myface_payment_numbers_are_checked(make_client, create_user):
    admin = await _admin(make_client, create_user)
    resp = await admin.put("/admin/settings/pack-payment", json={"wave": "07 58 50 94 03", "whatsapp": ""})
    assert resp.status_code == 200, resp.text
    assert resp.json()["wave"] == "+2250758509403"
    assert resp.json()["whatsapp"] is None
    assert (await admin.put("/admin/settings/pack-payment", json={"orange": "12"})).status_code == 422


async def test_geniuspay_is_closed_by_default(make_client):
    anon = await make_client()
    resp = await anon.post("/payments/geniuspay/init", json={"session_id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code == 404


async def test_api_documentation_hidden_in_production(make_client):
    anon = await make_client()
    resp = await anon.get("/openapi.json")
    assert resp.status_code == (404 if settings.is_production else 200)


async def test_sms_promise_only_when_sms_really_leave(make_client, monkeypatch):
    """Compte Africa's Talking « sandbox » : aucun SMS n'arrive, les pages
    invites ne doivent pas en promettre."""
    anon = await make_client()
    monkeypatch.setattr(settings, "africastalking_username", "sandbox")
    monkeypatch.setattr(settings, "africastalking_api_key", "cle-de-test")
    assert (await anon.get("/meta/features")).json()["sms"] is False
    monkeypatch.setattr(settings, "africastalking_username", "myface")
    assert (await anon.get("/meta/features")).json()["sms"] is True
