"""Parties d'un evenement (mairie, reception...) : un seul evenement, des onglets."""

import io

import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.security import create_access_token
from app.models.user import UserRole

pytestmark = pytest.mark.asyncio


def _jpeg(color: tuple[int, int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), color=color).save(buffer, format="JPEG")
    return buffer.getvalue()


async def _event(auth_client: AsyncClient) -> str:
    resp = await auth_client.post(
        "/events",
        json={"name": "Mariage Awa & Koffi", "date": "2026-11-20T10:00:00Z", "location": "Abidjan",
              "pricing": {"unit_price": 450}},
    )
    return resp.json()["id"]


async def _upload(auth_client: AsyncClient, event_id: str, names: list[str], section_id: str | None = None) -> list[dict]:
    files = [("files", (n, _jpeg((10 * i, 40, 90)), "image/jpeg")) for i, n in enumerate(names)]
    url = f"/photos/upload?event_id={event_id}" + (f"&section_id={section_id}" if section_id else "")
    resp = await auth_client.post(url, files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()["uploaded"]


async def test_sections_tabs_and_upload(auth_client: AsyncClient, client: AsyncClient):
    event_id = await _event(auth_client)
    mairie = (await auth_client.post(f"/events/{event_id}/sections", json={
        "name": "Mairie", "starts_at": "2026-11-20T10:00:00Z", "location": "Mairie de Cocody"})).json()
    reception = (await auth_client.post(f"/events/{event_id}/sections", json={"name": "Réception"})).json()
    assert (mairie["position"], reception["position"]) == (0, 1)

    up_mairie = await _upload(auth_client, event_id, ["m1.jpg", "m2.jpg"], mairie["id"])
    assert all(p["section_id"] == mairie["id"] for p in up_mairie)
    await _upload(auth_client, event_id, ["r1.jpg"], reception["id"])
    await _upload(auth_client, event_id, ["libre.jpg"])

    # onglets : toutes les photos, puis une partie
    assert (await client.get(f"/events/{event_id}/photos")).json()["total"] == 4
    seule = (await client.get(f"/events/{event_id}/photos?section_id={mairie['id']}")).json()
    assert seule["total"] == 2 and {p["original_filename"] for p in seule["items"]} == {"m1.jpg", "m2.jpg"}

    # vue publique de l'evenement : les parties, dans l'ordre, avec leur nombre de photos
    public = (await client.get(f"/events/{event_id}/public")).json()
    assert [(s["name"], s["photo_count"], s["location"]) for s in public["sections"]] == [
        ("Mairie", 2, "Mairie de Cocody"), ("Réception", 1, None)]

    # reordonner : la reception passe en premier
    ordre = (await auth_client.patch(f"/events/{event_id}/sections/{reception['id']}", json={"position": 0})).json()
    assert [s["name"] for s in ordre] == ["Réception", "Mairie"]

    # ranger la photo libre dans la reception
    libre = (await client.get(f"/events/{event_id}/photos")).json()["items"]
    libre_id = next(p["id"] for p in libre if p["original_filename"] == "libre.jpg")
    moved = await auth_client.post(f"/events/{event_id}/photos/section",
                                   json={"photo_ids": [libre_id], "section_id": reception["id"]})
    assert moved.json() == {"moved": 1}
    assert (await client.get(f"/events/{event_id}/photos?section_id={reception['id']}")).json()["total"] == 2

    # supprimer une partie ne supprime jamais ses photos
    assert (await auth_client.delete(f"/events/{event_id}/sections/{mairie['id']}")).status_code == 204
    assert (await client.get(f"/events/{event_id}/photos")).json()["total"] == 4
    assert [s["name"] for s in (await client.get(f"/events/{event_id}/sections")).json()] == ["Réception"]


async def test_sections_belong_to_their_event(auth_client: AsyncClient, client: AsyncClient, create_user):
    event_a = await _event(auth_client)
    event_b = await _event(auth_client)
    partie_b = (await auth_client.post(f"/events/{event_b}/sections", json={"name": "Église"})).json()

    # une partie d'un autre evenement est refusee a l'envoi et au rangement
    files = [("files", ("x.jpg", _jpeg((1, 2, 3)), "image/jpeg"))]
    assert (await auth_client.post(f"/photos/upload?event_id={event_a}&section_id={partie_b['id']}", files=files)).status_code == 404
    assert (await auth_client.post(f"/events/{event_a}/photos/section",
                                   json={"photo_ids": ["00000000-0000-0000-0000-000000000001"],
                                         "section_id": partie_b["id"]})).status_code == 404

    # un photographe ne gere pas les parties d'un evenement qui n'est pas le sien
    autre = await create_user("autre@myface-test.com", "testpassword123", UserRole.PHOTOGRAPHE)
    client.headers["Authorization"] = f"Bearer {create_access_token(str(autre.id))}"
    assert (await client.post(f"/events/{event_a}/sections", json={"name": "Piège"})).status_code in (403, 404)
    assert (await client.delete(f"/events/{event_b}/sections/{partie_b['id']}")).status_code in (403, 404)


async def test_same_file_name_allowed_in_another_section(auth_client: AsyncClient):
    """Deux appareils numerotent pareil : IMG_0001 a la mairie et a la reception."""
    event_id = await _event(auth_client)
    mairie = (await auth_client.post(f"/events/{event_id}/sections", json={"name": "Mairie"})).json()
    reception = (await auth_client.post(f"/events/{event_id}/sections", json={"name": "Réception"})).json()
    await _upload(auth_client, event_id, ["IMG_0001.jpg"], mairie["id"])
    await _upload(auth_client, event_id, ["IMG_0001.jpg"], reception["id"])

    files = [("files", ("IMG_0001.jpg", _jpeg((9, 9, 9)), "image/jpeg"))]
    again = await auth_client.post(f"/photos/upload?event_id={event_id}&section_id={mairie['id']}", files=files)
    assert again.json()["uploaded"] == [] and len(again.json()["errors"]) == 1   # doublon dans la meme partie
