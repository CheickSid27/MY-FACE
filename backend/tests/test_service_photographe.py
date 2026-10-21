"""Service photographe : inscription, packs (memes tarifs que Fokevani),
limites de photos, achat et validation des packs, mot de passe de galerie,
filigrane au nom du photographe, suspension de compte."""

import io

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.core.security import create_access_token
from app.main import app
from app.models.user import UserRole

pytestmark = pytest.mark.asyncio

PHOTOGRAPHE = {
    "email": "Studio.Lumiere@example.com",
    "password": "motdepasse123",
    "display_name": "Awa Kone",
    "studio_name": "Studio Lumiere",
    "phone": "+225 07 01 02 03 04",
    "city": "Abidjan",
    "accept_terms": True,
}


def _jpeg(color=(120, 80, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (240, 160), color=color).save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest_asyncio.fixture
async def make_client(client: AsyncClient):
    """Clients HTTP independants (anonyme, photographe, admin) : le client de
    la fixture `client` est partage et porte deja l'en-tete de l'admin quand
    `auth_client` est utilise."""
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


async def _register(make_client, **overrides) -> AsyncClient:
    anon = await make_client()
    resp = await anon.post("/auth/register", json={**PHOTOGRAPHE, **overrides})
    assert resp.status_code == 201, resp.text
    return await make_client(resp.json()["access_token"])


async def _admin(make_client, create_user) -> AsyncClient:
    admin = await create_user("admin@myface-test.com", "testpassword123", UserRole.ADMIN)
    return await make_client(create_access_token(str(admin.id)))


async def _create_event(ac: AsyncClient, **pricing) -> str:
    resp = await ac.post(
        "/events",
        json={
            "name": "Mariage Awa & Koffi",
            "date": "2026-11-20T15:00:00Z",
            "location": "Abidjan",
            "pricing": pricing or {"unit_price": 500},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# --------------------------------------------------------------------------
# Inscription et profil
# --------------------------------------------------------------------------
async def test_register_creates_photographer_and_logs_in(make_client):
    photographe = await _register(make_client)
    me = (await photographe.get("/auth/me")).json()
    assert me["email"] == "studio.lumiere@example.com"
    assert me["role"] == "photographe"
    assert me["studio_name"] == "Studio Lumiere"
    assert me["phone"] == "+2250701020304"
    assert me["is_active"] is True


async def test_register_rejects_duplicate_email_any_case(make_client):
    await _register(make_client)
    anon = await make_client()
    resp = await anon.post("/auth/register", json={**PHOTOGRAPHE, "email": "STUDIO.lumiere@example.com"})
    assert resp.status_code == 409


async def test_register_requires_terms_and_valid_phone(make_client):
    anon = await make_client()
    resp = await anon.post("/auth/register", json={**PHOTOGRAPHE, "accept_terms": False})
    assert resp.status_code == 422
    resp = await anon.post("/auth/register", json={**PHOTOGRAPHE, "phone": "12"})
    assert resp.status_code == 422


async def test_login_is_case_insensitive_for_registered_email(make_client):
    await _register(make_client)
    anon = await make_client()
    resp = await anon.post("/auth/login", json={"email": "studio.LUMIERE@example.com", "password": "motdepasse123"})
    assert resp.status_code == 200


async def test_profile_update(make_client):
    photographe = await _register(make_client)
    resp = await photographe.patch("/auth/me", json={"studio_name": "Lumiere Photo", "city": "Yamoussoukro"})
    assert resp.status_code == 200
    assert resp.json()["studio_name"] == "Lumiere Photo"
    assert resp.json()["city"] == "Yamoussoukro"


async def test_register_is_rate_limited(make_client):
    anon = await make_client()
    for i in range(10):
        resp = await anon.post("/auth/register", json={**PHOTOGRAPHE, "email": f"p{i}@example.com"})
        assert resp.status_code == 201
    resp = await anon.post("/auth/register", json={**PHOTOGRAPHE, "email": "p99@example.com"})
    assert resp.status_code == 429


# --------------------------------------------------------------------------
# Packs et limites
# --------------------------------------------------------------------------
async def test_packs_have_fokevani_prices(make_client):
    anon = await make_client()
    packs = {p["key"]: p for p in (await anon.get("/packs")).json()}
    assert (packs["decouverte"]["price"], packs["decouverte"]["photo_limit"]) == (0, 10)
    assert (packs["evenement"]["price"], packs["evenement"]["photo_limit"]) == (10_000, 500)
    assert (packs["pro"]["price"], packs["pro"]["photo_limit"]) == (25_000, 2_000)
    assert packs["sur_mesure"]["price"] is None
    assert packs["sur_mesure"]["purchasable"] is False


async def test_photographer_event_starts_with_free_pack(make_client):
    photographe = await _register(make_client)
    event_id = await _create_event(photographe)
    pack = (await photographe.get(f"/events/{event_id}/pack")).json()
    assert pack["pack"]["key"] == "decouverte"
    assert pack["unlimited"] is False
    assert (pack["photo_limit"], pack["photo_count"], pack["remaining"]) == (10, 0, 10)
    assert [(u["key"], u["amount_due"]) for u in pack["upgrades"]] == [("evenement", 10_000), ("pro", 25_000)]

    listed = (await photographe.get("/events")).json()
    assert listed[0]["pack"] == "decouverte"
    assert listed[0]["photo_limit"] == 10


async def test_upload_stops_at_pack_limit(make_client):
    photographe = await _register(make_client)
    event_id = await _create_event(photographe)
    files = [("files", (f"p{i}.jpg", _jpeg((i * 20 % 255, 60, 90)), "image/jpeg")) for i in range(12)]
    resp = await photographe.post(f"/photos/upload?event_id={event_id}", files=files)
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["uploaded"]) == 10
    assert len(data["errors"]) == 2
    assert "Limite du pack Découverte atteinte (10 photos)" in data["errors"][0]["error"]
    assert "pack Événement" in data["errors"][0]["error"]


async def test_admin_events_are_unlimited(make_client, create_user):
    admin = await _admin(make_client, create_user)
    event_id = await _create_event(admin)
    pack = (await admin.get(f"/events/{event_id}/pack")).json()
    assert pack["unlimited"] is True
    assert pack["photo_limit"] is None
    assert pack["upgrades"] == []
    resp = await admin.post(
        f"/events/{event_id}/pack-purchases",
        json={"pack": "pro", "payment_method": "wave", "payer_phone": "+2250701020304", "transaction_ref": "ABC123"},
    )
    assert resp.status_code == 400


async def test_pack_purchase_flow(make_client, create_user):
    photographe = await _register(make_client)
    admin = await _admin(make_client, create_user)
    event_id = await _create_event(photographe)
    achat = {"pack": "evenement", "payment_method": "wave", "payer_phone": "+2250701020304", "transaction_ref": "T-1001"}

    resp = await photographe.post(f"/events/{event_id}/pack-purchases", json=achat)
    assert resp.status_code == 201, resp.text
    purchase = resp.json()
    assert (purchase["status"], purchase["amount"]) == ("pending", 10_000)

    # un seul paiement en attente a la fois
    resp = await photographe.post(f"/events/{event_id}/pack-purchases", json={**achat, "pack": "pro"})
    assert resp.status_code == 409

    # le pack ne change qu'apres validation par MYFACE
    assert (await photographe.get(f"/events/{event_id}/pack")).json()["pack"]["key"] == "decouverte"
    assert (await photographe.get("/events")).json()[0]["pack_pending"] is True

    pending = (await admin.get("/admin/pack-purchases?status=pending")).json()
    assert len(pending) == 1
    assert pending[0]["photographer_name"] == "Studio Lumiere"
    assert pending[0]["transaction_ref"] == "T-1001"

    resp = await admin.post(f"/admin/pack-purchases/{purchase['id']}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"

    pack = (await photographe.get(f"/events/{event_id}/pack")).json()
    assert pack["pack"]["key"] == "evenement"
    assert (pack["photo_limit"], pack["amount_paid"]) == (500, 10_000)
    # passer a Pro ne coute que la difference
    assert [(u["key"], u["amount_due"]) for u in pack["upgrades"]] == [("pro", 15_000)]

    resp = await photographe.post(f"/events/{event_id}/pack-purchases", json={**achat, "pack": "pro", "transaction_ref": "T-1002"})
    assert resp.status_code == 201
    assert resp.json()["amount"] == 15_000
    resp = await admin.post(f"/admin/pack-purchases/{resp.json()['id']}/reject", json={"note": "Paiement introuvable"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert (await photographe.get(f"/events/{event_id}/pack")).json()["pack"]["key"] == "evenement"

    # deja traite
    assert (await admin.post(f"/admin/pack-purchases/{purchase['id']}/approve")).status_code == 409


async def test_cannot_buy_same_or_lower_pack_or_free_pack(make_client, create_user):
    photographe = await _register(make_client)
    admin = await _admin(make_client, create_user)
    event_id = await _create_event(photographe)
    achat = {"payment_method": "orange", "payer_phone": "+2250701020304", "transaction_ref": "OM-55"}

    assert (await photographe.post(f"/events/{event_id}/pack-purchases", json={**achat, "pack": "decouverte"})).status_code == 400
    assert (await photographe.post(f"/events/{event_id}/pack-purchases", json={**achat, "pack": "sur_mesure"})).status_code == 400

    await admin.put(f"/admin/events/{event_id}/pack", json={"pack": "pro"})
    assert (await photographe.post(f"/events/{event_id}/pack-purchases", json={**achat, "pack": "evenement"})).status_code == 409


async def test_photographer_can_cancel_pending_purchase(make_client):
    photographe = await _register(make_client)
    event_id = await _create_event(photographe)
    resp = await photographe.post(
        f"/events/{event_id}/pack-purchases",
        json={"pack": "pro", "payment_method": "mtn", "payer_phone": "+2250501020304", "transaction_ref": "MTN-9"},
    )
    purchase_id = resp.json()["id"]
    resp = await photographe.post(f"/pack-purchases/{purchase_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert (await photographe.get(f"/events/{event_id}/pack")).json()["pending_purchase"] is None


async def test_admin_assigns_custom_pack_with_limit(make_client, create_user):
    photographe = await _register(make_client)
    admin = await _admin(make_client, create_user)
    event_id = await _create_event(photographe)
    resp = await admin.put(
        f"/admin/events/{event_id}/pack",
        json={"pack": "sur_mesure", "photo_limit_override": 50, "note": "Carnet 5 evenements"},
    )
    assert resp.status_code == 200, resp.text
    pack = resp.json()
    assert (pack["pack"]["key"], pack["photo_limit"]) == ("sur_mesure", 50)
    assert pack["purchases"][0]["payment_method"] == "admin"
    assert pack["purchases"][0]["status"] == "paid"


async def test_photographer_cannot_use_admin_pack_routes(make_client):
    photographe = await _register(make_client)
    event_id = await _create_event(photographe)
    assert (await photographe.get("/admin/pack-purchases")).status_code == 403
    assert (await photographe.put(f"/admin/events/{event_id}/pack", json={"pack": "pro"})).status_code == 403
    assert (await photographe.get("/admin/users")).status_code == 403


async def test_photographer_cannot_see_other_photographer_event(make_client):
    premier = await _register(make_client)
    second = await _register(make_client, email="autre@example.com")
    event_id = await _create_event(premier)
    assert (await second.get(f"/events/{event_id}/pack")).status_code == 403
    assert (await second.get(f"/events/{event_id}")).status_code == 403
    assert (await second.get("/events")).json() == []


async def test_pack_payment_numbers_set_by_admin(make_client, create_user):
    photographe = await _register(make_client)
    admin = await _admin(make_client, create_user)
    assert (await photographe.get("/packs/payment-info")).json()["wave"] is None
    resp = await admin.put("/admin/settings/pack-payment", json={"wave": " 0758509403 ", "whatsapp": "+2250758509403"})
    assert resp.status_code == 200
    info = (await photographe.get("/packs/payment-info")).json()
    assert info["wave"] == "0758509403"
    assert info["whatsapp"] == "+2250758509403"
    assert (await photographe.put("/admin/settings/pack-payment", json={"wave": "1"})).status_code == 403


# --------------------------------------------------------------------------
# Options des packs payants : mot de passe de galerie, filigrane
# --------------------------------------------------------------------------
async def test_gallery_password_requires_paid_pack(make_client, create_user):
    photographe = await _register(make_client)
    admin = await _admin(make_client, create_user)
    event_id = await _create_event(photographe)
    resp = await photographe.patch(f"/events/{event_id}", json={"gallery_password": "mariage2026"})
    assert resp.status_code == 403
    assert "pack Événement" in resp.json()["detail"]

    await admin.put(f"/admin/events/{event_id}/pack", json={"pack": "evenement"})
    resp = await photographe.patch(f"/events/{event_id}", json={"gallery_password": "mariage2026"})
    assert resp.status_code == 200
    assert resp.json()["has_gallery_password"] is True


async def test_password_protected_gallery(make_client, create_user, seed_photo, storage_service, test_session_factory):
    photographe = await _register(make_client)
    admin = await _admin(make_client, create_user)
    event_id = await _create_event(photographe)
    await admin.put(f"/admin/events/{event_id}/pack", json={"pack": "evenement"})
    await seed_photo(event_id, storage_service, test_session_factory, "a.jpg", _jpeg())
    await photographe.patch(f"/events/{event_id}", json={"gallery_password": "mariage2026"})
    event = (await photographe.get(f"/events/{event_id}")).json()
    invite = await make_client()

    public = (await invite.get(f"/events/{event_id}/public")).json()
    assert public["password_required"] is True
    assert public["gallery_access"] is False
    assert public["photographer_name"] == "Studio Lumiere"

    assert (await invite.get(f"/events/{event_id}/photos")).status_code == 403
    assert (await invite.get(f"/events/{event_id}/clusters/public")).status_code == 403

    assert (await invite.post(f"/events/{event_id}/unlock", json={"password": "faux"})).status_code == 401
    resp = await invite.post(f"/events/{event_id}/unlock", json={"password": " mariage2026 "})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    resp = await invite.get(f"/events/{event_id}/photos", params={"access": token})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert (await invite.get(f"/events/{event_id}/public", params={"access": token})).json()["gallery_access"] is True

    # la borne et l'organisateur passent sans mot de passe
    assert (await invite.get(f"/events/{event_id}/photos", params={"kiosk_token": event["kiosk_token"]})).status_code == 200
    assert (await photographe.get(f"/events/{event_id}/photos")).status_code == 200

    # changer le mot de passe retire les acces deja donnes
    await photographe.patch(f"/events/{event_id}", json={"gallery_password": "nouveau2026"})
    assert (await invite.get(f"/events/{event_id}/photos", params={"access": token})).status_code == 403

    # retirer le mot de passe rouvre la galerie
    await photographe.patch(f"/events/{event_id}", json={"gallery_password": ""})
    assert (await invite.get(f"/events/{event_id}/photos")).status_code == 200


async def test_gallery_unlock_is_rate_limited(make_client, create_user):
    photographe = await _register(make_client)
    admin = await _admin(make_client, create_user)
    event_id = await _create_event(photographe)
    await admin.put(f"/admin/events/{event_id}/pack", json={"pack": "evenement"})
    await photographe.patch(f"/events/{event_id}", json={"gallery_password": "mariage2026"})
    invite = await make_client()
    for _ in range(10):
        assert (await invite.post(f"/events/{event_id}/unlock", json={"password": "faux"})).status_code == 401
    assert (await invite.post(f"/events/{event_id}/unlock", json={"password": "mariage2026"})).status_code == 429


async def test_custom_watermark_requires_paid_pack_and_uses_studio(make_client, create_user, storage_service):
    photographe = await _register(make_client)
    admin = await _admin(make_client, create_user)
    event_id = await _create_event(photographe)
    resp = await photographe.patch(f"/events/{event_id}", json={"watermark_text": "LUMIERE"})
    assert resp.status_code == 403

    await admin.put(f"/admin/events/{event_id}/pack", json={"pack": "evenement"})
    resp = await photographe.patch(f"/events/{event_id}", json={"watermark_text": "LUMIERE"})
    assert resp.status_code == 200
    assert resp.json()["watermark_text"] == "LUMIERE"

    files = [("files", ("p.jpg", _jpeg(), "image/jpeg"))]
    resp = await photographe.post(f"/photos/upload?event_id={event_id}", files=files)
    assert resp.status_code == 201
    wm_keys = [k for k in storage_service.objects if "/previews-wm/" in k]
    assert len(wm_keys) == 1


async def test_free_pack_watermark_stays_myface():
    from types import SimpleNamespace

    from app.services.packs import watermark_text_for

    owner = SimpleNamespace(role=UserRole.PHOTOGRAPHE, public_name="Studio Lumiere")
    gratuit = SimpleNamespace(pack="decouverte", watermark_text="LUMIERE")
    payant = SimpleNamespace(pack="evenement", watermark_text=None)
    assert watermark_text_for(gratuit, owner) == "MYFACE"
    assert watermark_text_for(payant, owner) == "Studio Lumiere"


# --------------------------------------------------------------------------
# Comptes : suspension, vue admin
# --------------------------------------------------------------------------
async def test_suspended_account_cannot_log_in(make_client, create_user):
    photographe = await _register(make_client)
    admin = await _admin(make_client, create_user)
    user_id = (await photographe.get("/auth/me")).json()["id"]

    resp = await admin.patch(f"/admin/users/{user_id}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    assert (await photographe.get("/auth/me")).status_code == 403
    anon = await make_client()
    resp = await anon.post("/auth/login", json={"email": PHOTOGRAPHE["email"], "password": PHOTOGRAPHE["password"]})
    assert resp.status_code == 403

    await admin.patch(f"/admin/users/{user_id}", json={"is_active": True})
    resp = await anon.post("/auth/login", json={"email": PHOTOGRAPHE["email"], "password": PHOTOGRAPHE["password"]})
    assert resp.status_code == 200


async def test_admin_users_list_shows_activity(make_client, create_user):
    photographe = await _register(make_client)
    admin = await _admin(make_client, create_user)
    event_id = await _create_event(photographe)
    resp = await photographe.post(
        f"/events/{event_id}/pack-purchases",
        json={"pack": "evenement", "payment_method": "wave", "payer_phone": "+2250701020304", "transaction_ref": "W-1"},
    )
    await admin.post(f"/admin/pack-purchases/{resp.json()['id']}/approve")

    users = {u["email"]: u for u in (await admin.get("/admin/users")).json()}
    p = users["studio.lumiere@example.com"]
    assert (p["event_count"], p["packs_paid_total"], p["packs_pending"]) == (1, 10_000, 0)
    assert p["studio_name"] == "Studio Lumiere"
