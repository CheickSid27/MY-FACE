"""Journal des requetes lisible (une ligne par requete avec sa duree)."""

import logging

import pytest
from httpx import AsyncClient

from app.services import request_log
from app.services.request_log import route_label

pytestmark = pytest.mark.asyncio


def test_ids_are_grouped():
    assert route_label("/events/5816f494-e0ea-4205-b2c0-3a43b5ee381c/photos") == "/events/{id}/photos"
    assert route_label("/events/code/K7M2QX9P") == "/events/code/{id}"


class _Collect(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def clear(self):
        self.records = []


async def test_each_request_is_logged_with_its_duration(client: AsyncClient, monkeypatch):
    # le logger « myface » ne remonte pas a la racine : on ecoute directement
    caplog = _Collect()
    logging.getLogger("myface.requetes").addHandler(caplog)
    resp = await client.get("/events/5816f494-e0ea-4205-b2c0-3a43b5ee381c/public")
    assert "server-timing" in resp.headers
    assert any("GET /events/{id}/public 404 en" in r.getMessage() for r in caplog.records)

    # au-dela du seuil : signale « LENT »
    monkeypatch.setattr(request_log, "SLOW_MS", 0)
    await client.get("/events/5816f494-e0ea-4205-b2c0-3a43b5ee381c/public")
    assert any(r.getMessage().startswith("LENT GET /events/{id}/public") for r in caplog.records)

    # les sondes de sante ne sont pas notees
    caplog.clear()
    await client.get("/health")
    assert not caplog.records
