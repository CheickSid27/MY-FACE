"""Base injoignable un instant pendant l'indexation : la photo est reessayee."""

import asyncio
import uuid

import pytest
from sqlalchemy.exc import OperationalError

from app.services import face_indexing

pytestmark = pytest.mark.asyncio


def test_transient_errors_are_recognized():
    try:
        try:
            raise asyncio.TimeoutError()
        except asyncio.TimeoutError as inner:
            raise RuntimeError("session") from inner
    except RuntimeError as exc:
        assert face_indexing._is_transient(exc)
    assert face_indexing._is_transient(OperationalError("select 1", {}, Exception("connexion fermee")))
    assert not face_indexing._is_transient(ValueError("image illisible"))


async def test_photo_retried_when_database_unreachable(monkeypatch):
    calls: list[uuid.UUID] = []
    answers = iter([False, False, True])

    async def fake_index(photo_id, storage, session_factory):
        calls.append(photo_id)
        return next(answers)

    monkeypatch.setattr(face_indexing, "index_photo_faces", fake_index)
    monkeypatch.setattr(face_indexing, "RETRY_DELAY_S", 0)
    photo_id = uuid.uuid4()
    await face_indexing.index_photos_faces([photo_id], storage=object(), session_factory=object())
    assert calls == [photo_id] * 3
    assert not face_indexing.is_scheduled(photo_id)


async def test_normal_end_is_not_retried(monkeypatch):
    calls = []

    async def fake_index(photo_id, storage, session_factory):
        calls.append(photo_id)
        return None  # photo introuvable : fin normale, pas de nouvel essai

    monkeypatch.setattr(face_indexing, "index_photo_faces", fake_index)
    await face_indexing.index_photos_faces([uuid.uuid4()], storage=object(), session_factory=object())
    assert len(calls) == 1
