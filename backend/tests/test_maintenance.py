"""Mode maintenance : bouton de l'admin, message vu par les invites."""

import io

import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.security import create_access_token
from app.models.user import UserRole
from app.services import maintenance

pytestmark = pytest.mark.asyncio


def _as(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


async def test_maintenance_button_and_guest_message(client: AsyncClient, admin_user):
    maintenance.reset_cache()
    assert (await client.get("/meta/status")).json() == {"maintenance": False, "message": None, "photographers": False}

    on = await client.put("/admin/settings/maintenance", json={"active": True, "message": "  "}, headers=_as(admin_user))
    assert on.status_code == 200, on.text
    assert on.json()["active"] is True and on.json()["since"]

    status = (await client.get("/meta/status")).json()
    assert status["maintenance"] is True
    assert status["message"] == maintenance.DEFAULT_MESSAGE

    since = on.json()["since"]
    edited = await client.put(
        "/admin/settings/maintenance", json={"active": True, "message": "Retour à 15 h."}, headers=_as(admin_user)
    )
    assert edited.json()["since"] == since          # corriger le message ne change pas « depuis »
    assert (await client.get("/meta/status")).json()["message"] == "Retour à 15 h."

    off = await client.put("/admin/settings/maintenance", json={"active": False, "message": None}, headers=_as(admin_user))
    assert off.json() == {"active": False, "message": None, "since": None, "photographers": False}
    assert (await client.get("/meta/status")).json() == {"maintenance": False, "message": None, "photographers": False}


async def test_only_admin_switches_maintenance(client: AsyncClient, create_user):
    assert (await client.put("/admin/settings/maintenance", json={"active": True})).status_code in (401, 403)
    photographe = await create_user("photo@myface-test.com", "testpassword123", UserRole.PHOTOGRAPHE)
    assert (await client.put("/admin/settings/maintenance", json={"active": True}, headers=_as(photographe))).status_code == 403
    assert (await client.get("/admin/settings/maintenance", headers=_as(photographe))).status_code == 403


def _photo() -> list:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), color=(30, 60, 90)).save(buffer, format="JPEG")
    return [("files", ("m.jpg", buffer.getvalue(), "image/jpeg"))]


async def test_server_refuses_orders_and_chosen_photographers(client: AsyncClient, admin_user, create_user):
    maintenance.reset_cache()
    photographe = await create_user("photo2@myface-test.com", "testpassword123", UserRole.PHOTOGRAPHE)
    event = await client.post(
        "/events", headers=_as(photographe),
        json={"name": "Soirée", "date": "2026-11-20T10:00:00Z", "location": "Abidjan", "pricing": {"unit_price": 450}},
    )
    event_id = event.json()["id"]
    upload = f"/photos/upload?event_id={event_id}"
    order = {"session_id": "00000000-0000-0000-0000-000000000001", "payment_method": "orange_money", "contact_phone": "+2250701020304"}

    # maintenance pour les invites seulement : commandes refusees, le photographe travaille
    await client.put("/admin/settings/maintenance", json={"active": True}, headers=_as(admin_user))
    refused = await client.post("/payments/init", json=order)
    assert refused.status_code == 503 and refused.json()["detail"] == maintenance.DEFAULT_MESSAGE
    assert (await client.post(upload, files=_photo(), headers=_as(photographe))).status_code != 503

    # photographes inclus : son envoi est refuse, l'admin passe toujours
    on = await client.put("/admin/settings/maintenance", json={"active": True, "photographers": True}, headers=_as(admin_user))
    assert on.json()["photographers"] is True
    assert (await client.get("/meta/status")).json()["photographers"] is True
    assert (await client.post(upload, files=_photo(), headers=_as(photographe))).status_code == 503
    assert (await client.post(upload, files=_photo(), headers=_as(admin_user))).status_code != 503

    # maintenance coupee : tout se rouvre (le panier inconnu donne alors 404)
    await client.put("/admin/settings/maintenance", json={"active": False}, headers=_as(admin_user))
    assert (await client.post("/payments/init", json=order)).status_code == 404
