"""Photo de profil : recadree en carre 512 px, remplacee, retiree, visible
par les invites a cote du nom du photographe."""

import io

import pytest
from PIL import Image

from tests.test_service_photographe import _create_event, _register, make_client  # noqa: F401

pytestmark = pytest.mark.asyncio


def _png(size=(1200, 800), color=(30, 120, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


async def test_avatar_upload_replace_and_delete(make_client, storage_service):  # noqa: F811
    photographe = await _register(make_client)
    resp = await photographe.post("/auth/me/avatar", files={"file": ("moi.png", _png(), "image/png")})
    assert resp.status_code == 200, resp.text
    me = resp.json()
    version = me["avatar_version"]
    assert version

    keys = [k for k in storage_service.objects if "/avatar-" in k]
    assert len(keys) == 1
    with Image.open(io.BytesIO(storage_service.objects[keys[0]])) as img:
        assert img.size == (512, 512) and img.format == "JPEG"

    anon = await make_client()
    pic = await anon.get(f"/auth/avatars/{me['id']}?v={version}")
    assert pic.status_code == 200 and pic.headers["content-type"] == "image/jpeg"

    # nouvelle photo : l'ancienne est effacee, l'adresse change
    resp = await photographe.post("/auth/me/avatar", files={"file": ("moi2.png", _png(color=(200, 0, 0)), "image/png")})
    assert resp.json()["avatar_version"] != version
    assert len([k for k in storage_service.objects if "/avatar-" in k]) == 1

    # visible par les invites sur la page de l'evenement
    event_id = await _create_event(photographe)
    public = (await anon.get(f"/events/{event_id}/public")).json()
    assert public["photographer_id"] == me["id"]
    assert public["photographer_avatar_version"] == resp.json()["avatar_version"]

    resp = await photographe.delete("/auth/me/avatar")
    assert resp.json()["avatar_version"] is None
    assert not [k for k in storage_service.objects if "/avatar-" in k]
    assert (await anon.get(f"/auth/avatars/{me['id']}")).status_code == 404


async def test_avatar_rejects_non_images(make_client):  # noqa: F811
    photographe = await _register(make_client)
    resp = await photographe.post("/auth/me/avatar", files={"file": ("x.png", b"pas une image", "image/png")})
    assert resp.status_code == 400
    resp = await photographe.post("/auth/me/avatar", files={"file": ("x.gif", b"GIF89a", "image/gif")})
    assert resp.status_code == 400
