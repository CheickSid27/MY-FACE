"""Conservation des donnees declaree a l'ARTCI (voir services/retention.py) :
photos et empreintes faciales supprimees 90 jours apres l'evenement,
numero de telephone des commandes efface apres 1 an, evenement de
demonstration exempte, et rien de supprime en mode simulation."""

import io
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import func, select, update

from app.core.config import get_settings
from app.core.security import create_access_token
from app.main import app
from app.models.event import Event
from app.models.face_embedding import FaceEmbedding
from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.photo import Photo
from app.models.user import UserRole
from app.services.retention import ANONYMIZED_PHONE, run_retention

pytestmark = pytest.mark.asyncio

settings = get_settings()
NOW = datetime.now(timezone.utc)


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (60, 40), color=(10, 20, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


async def _event(ac: AsyncClient, days_ago: int, name: str = "Mariage") -> str:
    date = (NOW - timedelta(days=days_ago)).isoformat()
    resp = await ac.post(
        "/events", json={"name": name, "date": date, "location": "Abidjan", "pricing": {"unit_price": 500}}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _photo_with_face(event_id: str, seed_photo, storage_service, session_factory) -> str:
    photo_id = await seed_photo(event_id, storage_service, session_factory, "IMG_1.jpg", _jpeg())
    crop_key = f"events/{event_id}/face-crops/{uuid.uuid4()}.jpg"
    await storage_service.upload(crop_key, b"crop", "image/jpeg")
    await storage_service.upload(f"events/{event_id}/previews-wm/{photo_id}.jpg", b"wm", "image/jpeg")
    async with session_factory() as db:
        db.add(
            FaceEmbedding(
                photo_id=uuid.UUID(photo_id),
                vector=[0.01] * 512,
                bounding_box={"x1": 0, "y1": 0, "x2": 10, "y2": 10},
                confidence=0.9,
                crop_key=crop_key,
            )
        )
        await db.commit()
    return photo_id


async def _admin(client: AsyncClient, create_user) -> AsyncClient:
    admin = await create_user("admin@myface-test.com", "testpassword123", UserRole.ADMIN)
    client.headers["Authorization"] = f"Bearer {create_access_token(str(admin.id))}"
    return client


async def _count(session_factory, model, *where) -> int:
    async with session_factory() as db:
        return (await db.execute(select(func.count()).select_from(model).where(*where))).scalar_one()


async def test_old_event_photos_and_faces_are_deleted(
    client, create_user, seed_photo, storage_service, test_session_factory
):
    admin = await _admin(client, create_user)
    old_id = await _event(admin, days_ago=120, name="Ancien")
    recent_id = await _event(admin, days_ago=10, name="Recent")
    await _photo_with_face(old_id, seed_photo, storage_service, test_session_factory)
    await _photo_with_face(recent_id, seed_photo, storage_service, test_session_factory)
    await storage_service.upload(f"events/{old_id}/payment_qr/wave.png", b"qr", "image/png")

    report = await run_retention(storage_service, test_session_factory, force=True)

    assert [e.event_id for e in report.events] == [uuid.UUID(old_id)]
    assert report.photos_deleted == 1
    assert await _count(test_session_factory, Photo, Photo.event_id == uuid.UUID(old_id)) == 0
    assert await _count(test_session_factory, FaceEmbedding) == 1  # celle de l'evenement recent
    assert not any(key.startswith(f"events/{old_id}/") and "payment_qr" not in key for key in storage_service.objects)
    # le QR marchand n'est pas une donnee des invites
    assert f"events/{old_id}/payment_qr/wave.png" in storage_service.objects
    assert any(key.startswith(f"events/{recent_id}/originals/") for key in storage_service.objects)

    public = (await client.get(f"/events/{old_id}/public")).json()
    assert public["photos_purged"] is True


async def test_simulation_deletes_nothing(client, create_user, seed_photo, storage_service, test_session_factory):
    admin = await _admin(client, create_user)
    old_id = await _event(admin, days_ago=200)
    await _photo_with_face(old_id, seed_photo, storage_service, test_session_factory)
    assert settings.retention_enabled is False

    report = await run_retention(storage_service, test_session_factory)

    assert len(report.events) == 1
    assert report.photos_deleted == 0
    assert await _count(test_session_factory, Photo) == 1
    assert await _count(test_session_factory, FaceEmbedding) == 1


async def test_exempt_event_is_kept(client, create_user, seed_photo, storage_service, test_session_factory):
    admin = await _admin(client, create_user)
    demo_id = await _event(admin, days_ago=300, name="Demo du site")
    await _photo_with_face(demo_id, seed_photo, storage_service, test_session_factory)

    resp = await admin.put(f"/admin/events/{demo_id}/retention", json={"exempt": True})
    assert resp.status_code == 200

    report = await run_retention(storage_service, test_session_factory, force=True)
    assert report.events == []
    assert await _count(test_session_factory, Photo) == 1
    assert (await client.get(f"/events/{demo_id}/public")).json()["photos_available_until"] is None


async def test_public_event_shows_deadline(client, create_user):
    admin = await _admin(client, create_user)
    event_id = await _event(admin, days_ago=10)
    public = (await client.get(f"/events/{event_id}/public")).json()
    deadline = datetime.fromisoformat(public["photos_available_until"].replace("Z", "+00:00"))
    expected = NOW - timedelta(days=10) + timedelta(days=settings.retention_photo_days)
    assert abs((deadline - expected).total_seconds()) < 5
    assert public["photos_purged"] is False


async def test_old_order_phone_numbers_are_erased(
    client, create_user, seed_photo, storage_service, test_session_factory
):
    admin = await _admin(client, create_user)
    event_id = await _event(admin, days_ago=10)
    photo_id = await seed_photo(event_id, storage_service, test_session_factory, "IMG_2.jpg", _jpeg())

    async with test_session_factory() as db:
        for days in (400, 30):
            order = Order(
                event_id=uuid.UUID(event_id),
                contact_phone="+2250701020304",
                total_amount=500,
                currency="XOF",
                status=OrderStatus.SUCCESS,
                payment_method=PaymentMethod.CASH,
                payment_reference=f"TEST-{days}",
            )
            order.items = [OrderItem(photo_id=uuid.UUID(photo_id), unit_price=500)]
            db.add(order)
            await db.flush()
            await db.execute(
                update(Order).where(Order.id == order.id).values(created_at=NOW - timedelta(days=days))
            )
        await db.commit()

    report = await run_retention(storage_service, test_session_factory, force=True)
    assert report.orders_anonymized == 1

    async with test_session_factory() as db:
        phones = dict((await db.execute(select(Order.payment_reference, Order.contact_phone))).all())
    assert phones == {"TEST-400": ANONYMIZED_PHONE, "TEST-30": "+2250701020304"}


async def test_retention_admin_routes(client, create_user, seed_photo, storage_service, test_session_factory):
    admin = await _admin(client, create_user)
    old_id = await _event(admin, days_ago=100, name="A supprimer")
    await _photo_with_face(old_id, seed_photo, storage_service, test_session_factory)

    resp = await admin.get("/admin/retention")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["photo_days"] == settings.retention_photo_days
    assert [e["name"] for e in data["events"]] == ["A supprimer"]
    assert data["events"][0]["photo_count"] == 1

    # sans RETENTION_ENABLED, « lancer maintenant » ne supprime rien
    run = await admin.post("/admin/retention/run")
    assert run.status_code == 200
    assert run.json()["photos_deleted"] == 0
    assert await _count(test_session_factory, Photo) == 1

    photographe = await create_user("photo@myface-test.com", "testpassword123", UserRole.PHOTOGRAPHE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other:
        other.headers["Authorization"] = f"Bearer {create_access_token(str(photographe.id))}"
        assert (await other.get("/admin/retention")).status_code == 403
        assert (await other.put(f"/admin/events/{old_id}/retention", json={"exempt": True})).status_code == 403

    async with test_session_factory() as db:
        assert (await db.get(Event, uuid.UUID(old_id))).retention_exempt is False
