"""Volet Statistiques (journal des actions) et annulation des inscriptions
non confirmees dans le delai."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.services.unverified_accounts import purge_unverified_accounts
from tests.test_securite_comptes import (  # noqa: F401
    EVENT,
    _admin,
    _register,
    emails,
    enforce_verification,
    make_client,
)

pytestmark = pytest.mark.asyncio
settings = get_settings()


async def test_unconfirmed_signup_is_cancelled_after_delay(
    make_client, emails, enforce_verification, db_session, storage_service, monkeypatch  # noqa: F811
):
    monkeypatch.setattr(settings, "unverified_account_purge_since", datetime.now(timezone.utc) - timedelta(days=1))
    photographe, tokens = await _register(make_client)
    me = (await photographe.get("/auth/me")).json()
    assert me["must_verify_email"] is True
    assert me["verification_deadline"] is not None

    # dans le delai : rien n'est supprime
    assert await purge_unverified_accounts(db_session, storage_service) == 0

    user = await db_session.get(User, me["id"])
    user.created_at = datetime.now(timezone.utc) - timedelta(minutes=settings.unverified_account_ttl_minutes + 1)
    await db_session.commit()
    assert await purge_unverified_accounts(db_session, storage_service) == 1
    db_session.expire_all()
    assert await db_session.get(User, me["id"]) is None
    logs = (await db_session.execute(select(ActivityLog.action))).scalars().all()
    assert "inscription_annulee" in logs

    # la meme adresse peut se reinscrire
    await _register(make_client)


async def test_old_unconfirmed_accounts_are_kept(
    make_client, emails, enforce_verification, db_session, storage_service  # noqa: F811
):
    """Comptes crees avant la regle : jamais supprimes, juste bloques."""
    photographe, _ = await _register(make_client)
    me = (await photographe.get("/auth/me")).json()
    user = await db_session.get(User, me["id"])
    user.created_at = settings.unverified_account_purge_since - timedelta(days=3)
    await db_session.commit()
    assert await purge_unverified_accounts(db_session, storage_service) == 0
    me = (await photographe.get("/auth/me")).json()
    assert me["must_verify_email"] is True
    assert me["verification_deadline"] is None


async def test_activity_log_filters_and_export(make_client, create_user, emails):  # noqa: F811
    photographe, _ = await _register(make_client)
    other, _ = await _register(make_client, email="autre.photographe@example.com")
    resp = await photographe.post("/events", json=EVENT)
    assert resp.status_code == 201, resp.text

    admin = await _admin(make_client, create_user)
    page = (await admin.get("/activity")).json()
    actions = [item["action"] for item in page["items"]]
    assert "evenement_cree" in actions and "inscription" in actions
    assert page["counts"]["inscription"] == 2
    assert page["actions"]["selfie"]

    only_events = (await admin.get("/activity?action=evenement_cree")).json()
    assert only_events["total"] == 1 and only_events["items"][0]["event_name"] == EVENT["name"]

    # un photographe ne voit que ce qui le concerne
    mine = (await photographe.get("/activity")).json()
    assert {item["action"] for item in mine["items"]} <= {"inscription", "evenement_cree", "connexion"}
    assert (await other.get("/activity?action=evenement_cree")).json()["total"] == 0

    csv = await admin.get("/activity/export.csv")
    assert csv.status_code == 200
    assert "Date;Heure;Action;Qui" in csv.text and "Événement créé" in csv.text
