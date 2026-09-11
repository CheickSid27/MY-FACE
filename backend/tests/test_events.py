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


async def _photographe_headers(create_user, email: str = "photog-events@myface-test.com") -> dict:
    from app.core.security import create_access_token
    from app.models.user import UserRole

    user = await create_user(email, "password123", UserRole.PHOTOGRAPHE)
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


async def test_admin_sees_and_manages_all_events(auth_client: AsyncClient, create_user):
    photographe = await _photographe_headers(create_user)
    created = await auth_client.post("/events", json=_event_payload("Gala du photographe"), headers=photographe)
    event_id = created.json()["id"]

    # L'admin voit l'evenement du photographe, avec l'email de son organisateur...
    listing = (await auth_client.get("/events")).json()
    item = next(e for e in listing if e["id"] == event_id)
    assert item["organizer_email"] == "photog-events@myface-test.com"

    # ...et peut le gerer.
    assert (await auth_client.get(f"/events/{event_id}")).status_code == 200
    patched = await auth_client.patch(f"/events/{event_id}", json={"location": "Grand-Bassam"})
    assert patched.json()["location"] == "Grand-Bassam"


async def test_photographe_sees_only_own_events(auth_client: AsyncClient, create_user):
    await auth_client.post("/events", json=_event_payload("Gala admin"))
    photographe = await _photographe_headers(create_user, "photog-own@myface-test.com")
    await auth_client.post("/events", json=_event_payload("Gala perso"), headers=photographe)

    names = [e["name"] for e in (await auth_client.get("/events", headers=photographe)).json()]
    assert names == ["Gala perso"]


async def test_event_read_exposes_share_links(auth_client: AsyncClient):
    data = (await auth_client.post("/events", json=_event_payload())).json()
    assert data["guest_url"].endswith(f"/event/{data['id']}")
    assert data["kiosk_url"].endswith(f"/event/{data['id']}?kiosk={data['kiosk_token']}")


async def test_share_qr_png(auth_client: AsyncClient, client: AsyncClient):
    event_id = (await auth_client.post("/events", json=_event_payload())).json()["id"]
    for kind in ("guest", "kiosk"):
        resp = await auth_client.get(f"/events/{event_id}/qr.png", params={"kind": kind})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    client.headers.pop("Authorization", None)
    assert (await client.get(f"/events/{event_id}/qr.png")).status_code in (401, 403)


async def test_pricing_packs_and_discounts_saved_and_validated(auth_client: AsyncClient):
    event_id = (await auth_client.post("/events", json=_event_payload())).json()["id"]
    pricing = {
        "unit_price": 1000,
        "currency": "XOF",
        "packs": [{"count": 10, "price": 8000}],
        "discounts": [{"min_quantity": 20, "percent": 15}],
        "print_unit_price": 200,
    }
    resp = await auth_client.patch(f"/events/{event_id}", json={"pricing": pricing})
    assert resp.status_code == 200
    saved = resp.json()["pricing"]
    assert saved["packs"] == [{"count": 10, "price": 8000}]
    assert saved["discounts"] == [{"min_quantity": 20, "percent": 15}]

    for bad in (
        {**pricing, "unit_price": 0},
        {**pricing, "packs": [{"count": 1, "price": 500}]},
        {**pricing, "packs": [{"count": 5, "price": 4000}, {"count": 5, "price": 3500}]},
        {**pricing, "discounts": [{"min_quantity": 10, "percent": 100}]},
    ):
        assert (await auth_client.patch(f"/events/{event_id}", json={"pricing": bad})).status_code == 422


async def test_delete_event_blocked_when_paid_order(auth_client: AsyncClient, test_session_factory):
    import uuid

    from app.models.order import Order, OrderStatus, PaymentMethod

    event_id = (await auth_client.post("/events", json=_event_payload())).json()["id"]
    async with test_session_factory() as db:
        db.add(
            Order(
                event_id=uuid.UUID(event_id),
                contact_phone="+2250700000000",
                total_amount=1000,
                currency="XOF",
                status=OrderStatus.SUCCESS,
                payment_method=PaymentMethod.WAVE,
            )
        )
        await db.commit()

    resp = await auth_client.delete(f"/events/{event_id}")
    assert resp.status_code == 409
    assert (await auth_client.get(f"/events/{event_id}")).status_code == 200


async def test_delete_event_removes_stored_files(auth_client: AsyncClient, storage_service, test_session_factory, seed_photo):
    event_id = (await auth_client.post("/events", json=_event_payload())).json()["id"]
    other_id = (await auth_client.post("/events", json=_event_payload("Autre gala"))).json()["id"]
    await seed_photo(event_id, storage_service, test_session_factory, "a.jpg", b"fake")
    await seed_photo(other_id, storage_service, test_session_factory, "b.jpg", b"fake")

    resp = await auth_client.delete(f"/events/{event_id}")
    assert resp.status_code == 204
    assert not any(key.startswith(f"events/{event_id}/") for key in storage_service.objects)
    assert any(key.startswith(f"events/{other_id}/") for key in storage_service.objects)


async def test_indexing_summary_and_reindex(auth_client: AsyncClient, storage_service, test_session_factory, seed_photo):
    import uuid

    from app.models.photo import IndexingStatus, Photo

    event_id = (await auth_client.post("/events", json=_event_payload())).json()["id"]
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "a.jpg", b"not-an-image")
    async with test_session_factory() as db:
        photo = await db.get(Photo, uuid.UUID(photo_id))
        photo.indexing_status = IndexingStatus.FAILED
        await db.commit()

    summary = (await auth_client.get(f"/events/{event_id}/indexing")).json()
    assert summary == {"pending": 0, "processing": 0, "done": 0, "failed": 1, "faces": 0}

    resp = await auth_client.post(f"/events/{event_id}/reindex")
    assert resp.status_code == 202
    assert resp.json()["queued"] == 1

    # Fichier illisible : la re-indexation (executee en tache de fond apres
    # la reponse) aboutit de nouveau a un echec explicite, jamais a un blocage.
    summary = (await auth_client.get(f"/events/{event_id}/indexing")).json()
    assert summary["failed"] == 1
    assert summary["pending"] == 0


async def test_other_user_cannot_access_event(auth_client: AsyncClient, client: AsyncClient, create_user):
    from app.core.security import create_access_token
    from app.models.user import UserRole

    create_resp = await auth_client.post("/events", json=_event_payload())
    event_id = create_resp.json()["id"]

    other = await create_user("other@myface-test.com", "password123", UserRole.PHOTOGRAPHE)

    client.headers["Authorization"] = f"Bearer {create_access_token(str(other.id))}"
    resp = await client.get(f"/events/{event_id}")
    assert resp.status_code == 403
