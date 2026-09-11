import io
import uuid
import zipfile

import pytest
from httpx import AsyncClient
from PIL import Image

from app.models.order import Order, OrderStatus

pytestmark = pytest.mark.asyncio


def _jpeg_bytes(color=(10, 10, 10)) -> bytes:
    img = Image.new("RGB", (200, 200), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


async def _create_event(auth_client: AsyncClient, name: str, pricing: dict | None = None) -> tuple[str, str]:
    resp = await auth_client.post(
        "/events",
        json={
            "name": name,
            "date": "2026-12-15T10:00:00Z",
            "location": "Abidjan",
            "pricing": pricing or {"unit_price": 1000},
        },
    )
    return resp.json()["id"], resp.json()["kiosk_token"]


async def _create_order(
    auth_client, client, storage_service, test_session_factory, seed_photo, configure_payment_method,
    filenames=("p1.jpg",), pricing: dict | None = None, print_first: bool = False,
) -> tuple[str, str, str]:
    """Renvoie (order_id, event_id, kiosk_token)."""
    event_id, kiosk_token = await _create_event(auth_client, "Gala Download", pricing)
    await configure_payment_method(auth_client, event_id, "wave")

    session_id = None
    for i, filename in enumerate(filenames):
        photo_id = await seed_photo(event_id, storage_service, test_session_factory, filename, _jpeg_bytes((i, i, i)))
        add_resp = await client.post(
            "/cart/add", json={"event_id": event_id, "photo_id": photo_id, "session_id": session_id}
        )
        session_id = add_resp.json()["session_id"]
        if print_first and i == 0:
            item_id = add_resp.json()["items"][0]["id"]
            # Tirage papier : uniquement a la borne (jeton de l'evenement).
            await client.patch(f"/cart/{item_id}", json={"print_requested": True, "kiosk_token": kiosk_token})

    init_resp = await client.post(
        "/payments/init",
        json={"session_id": session_id, "contact_phone": "+2250700000000", "payment_method": "wave"},
    )
    return init_resp.json()["order_id"], event_id, kiosk_token


async def _mark_success(test_session_factory, order_id: str) -> None:
    # Isole le test du telechargement de celui de la validation du paiement
    # (couverte par test_payments.py).
    async with test_session_factory() as db:
        order = await db.get(Order, uuid.UUID(order_id))
        order.status = OrderStatus.SUCCESS
        await db.commit()


@pytest.fixture
def order_factory(auth_client, client, storage_service, test_session_factory, seed_photo, configure_payment_method):
    """Cree une commande ; renvoie son id, ou (id, event_id, kiosk_token)
    avec full=True."""

    async def _factory(paid: bool = True, full: bool = False, **kwargs):
        order_id, event_id, kiosk_token = await _create_order(
            auth_client, client, storage_service, test_session_factory, seed_photo, configure_payment_method,
            **kwargs,
        )
        if paid:
            await _mark_success(test_session_factory, order_id)
        return (order_id, event_id, kiosk_token) if full else order_id

    return _factory


async def test_download_blocked_before_payment(client, order_factory):
    order_id = await order_factory(paid=False)
    resp = await client.get(f"/download/{order_id}")
    assert resp.status_code == 403


async def test_download_available_after_payment(client, order_factory):
    order_id = await order_factory()

    resp = await client.get(f"/download/{order_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["photos"]) == 1
    photo = data["photos"][0]
    # Original servi en telechargement force, sous son nom d'origine...
    assert "/originals/" in photo["url"]
    assert "download=p1.jpg" in photo["url"]
    # ...mais la grille affiche la miniature, jamais l'original.
    assert "/thumbnails/" in photo["thumbnail_url"]


async def test_download_carries_print_requested(client, order_factory):
    order_id = await order_factory(pricing={"unit_price": 1000, "print_unit_price": 150}, print_first=True)

    resp = await client.get(f"/download/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["photos"][0]["print_requested"] is True


async def test_download_unknown_order_404(client):
    resp = await client.get(f"/download/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_zip_streams_all_photos(client, order_factory):
    order_id = await order_factory(filenames=("a.jpg", "b.jpg", "a.jpg"))

    resp = await client.get(f"/download/{order_id}/zip")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "attachment" in resp.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = sorted(zf.namelist())
        # Noms en double renommes plutot qu'ecrases.
        assert names == ["a.jpg", "a_1.jpg", "b.jpg"]
        assert zf.testzip() is None
        for name in names:
            Image.open(io.BytesIO(zf.read(name))).verify()


async def test_zip_blocked_before_payment(client, order_factory):
    order_id = await order_factory(paid=False)
    resp = await client.get(f"/download/{order_id}/zip")
    assert resp.status_code == 403


async def test_qr_available_after_payment(client, order_factory):
    order_id = await order_factory()

    resp = await client.get(f"/download/{order_id}/qr.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) > 0


PRINT_PRICING = {"unit_price": 1000, "print_unit_price": 150}


async def test_mark_printed_from_kiosk(client, order_factory):
    order_id, _, kiosk_token = await order_factory(full=True, pricing=PRINT_PRICING, print_first=True)
    client.headers.pop("Authorization", None)

    assert (await client.get(f"/download/{order_id}")).json()["printed_at"] is None

    # Invite sur son telephone (ni jeton borne, ni session organisateur) : refuse.
    assert (await client.post(f"/download/{order_id}/printed")).status_code == 403
    assert (await client.post(f"/download/{order_id}/printed", params={"kiosk_token": "faux"})).status_code == 403

    resp = await client.post(f"/download/{order_id}/printed", params={"kiosk_token": kiosk_token})
    assert resp.status_code == 200
    assert (await client.get(f"/download/{order_id}")).json()["printed_at"] is not None


async def test_mark_printed_by_organizer_and_listed(auth_client, order_factory):
    order_id, event_id, _ = await order_factory(full=True, pricing=PRINT_PRICING, print_first=True)

    orders = (await auth_client.get(f"/admin/events/{event_id}/orders")).json()
    assert orders[0]["print_count"] == 1
    assert orders[0]["printed_at"] is None

    assert (await auth_client.post(f"/download/{order_id}/printed")).status_code == 200
    orders = (await auth_client.get(f"/admin/events/{event_id}/orders")).json()
    assert orders[0]["printed_at"] is not None


async def test_mark_printed_requires_prints_and_payment(auth_client, order_factory):
    without_prints = await order_factory()
    assert (await auth_client.post(f"/download/{without_prints}/printed")).status_code == 400

    unpaid = await order_factory(paid=False, pricing=PRINT_PRICING, print_first=True)
    assert (await auth_client.post(f"/download/{unpaid}/printed")).status_code == 403


async def test_order_receipt_details(auth_client, order_factory):
    pricing = {"unit_price": 1000, "print_unit_price": 150, "packs": [{"count": 3, "price": 2500}]}
    order_id = await order_factory(pricing=pricing, print_first=True, filenames=("c.jpg", "a.jpg", "b.jpg"))

    receipt = (await auth_client.get(f"/admin/orders/{order_id}")).json()
    assert receipt["event_name"] == "Gala Download"
    assert receipt["photo_count"] == 3
    # Liste nominative, triee par nom de fichier.
    assert [item["photo"]["original_filename"] for item in receipt["items"]] == ["a.jpg", "b.jpg", "c.jpg"]
    assert receipt["print_count"] == 1
    # 3 x 1000 au prix unitaire + 150 de tirage, lot de 3 a 2500 : 500 de remise.
    assert receipt["photos_subtotal"] == 3000
    assert receipt["prints_total"] == 150
    assert receipt["discount_amount"] == 500
    assert receipt["total_amount"] == 2650
    assert receipt["download_url"].endswith(f"/order/{order_id}/download")


async def test_qr_blocked_before_payment(client, order_factory):
    order_id = await order_factory(paid=False)
    resp = await client.get(f"/download/{order_id}/qr.png")
    assert resp.status_code == 403
