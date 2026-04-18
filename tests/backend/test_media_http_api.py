# SPDX-License-Identifier: 0BSD

"""HTTP integration tests for sticker, sticker-pack, and GIF APIs (aiohttp TestClient)."""

from __future__ import annotations

import base64

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from tests.backend.media_test_assets import GZIP_TGS_512, TINY_GIF, TINY_PNG

pytestmark = pytest.mark.usefixtures("require_loopback_tcp")


def _build_aio_app(app):
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw = app._define_routes(routes)
    aio_app = web.Application(middlewares=[auth_mw, mime_mw, sec_mw])
    aio_app.add_routes(routes)
    return aio_app


@pytest.fixture
def web_media_app(mock_app):
    mock_app.current_context.running = True
    mock_app.config.auth_enabled.set(False)
    return mock_app


@pytest.mark.asyncio
async def test_stickers_list_empty(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.get("/api/v1/stickers")
        assert r.status == 200
        body = await r.json()
        assert body == {"stickers": []}


@pytest.mark.asyncio
async def test_stickers_create_get_image_export_import_roundtrip(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    b64 = base64.b64encode(TINY_PNG).decode("ascii")
    async with TestClient(TestServer(aio_app)) as client:
        c = await client.post(
            "/api/v1/stickers",
            json={
                "name": "  A  ",
                "image_type": "png",
                "image_bytes": b64,
                "strict": False,
            },
        )
        assert c.status == 200
        st = (await c.json())["sticker"]
        sid = st["id"]

        img = await client.get(f"/api/v1/stickers/{sid}/image")
        assert img.status == 200
        assert img.headers.get("Content-Type", "").startswith("image/png")
        raw = await img.read()
        assert raw == TINY_PNG

        ex = await client.get("/api/v1/stickers/export")
        assert ex.status == 200
        doc = await ex.json()
        assert doc.get("format") == "meshchatx-stickers"
        assert doc.get("version") == 1
        assert isinstance(doc.get("stickers"), list)
        assert len(doc["stickers"]) >= 1

        imp = await client.post(
            "/api/v1/stickers/import",
            json={**doc, "replace_duplicates": True},
        )
        assert imp.status == 200
        data = await imp.json()
        assert data.get("imported", 0) >= 1


@pytest.mark.asyncio
async def test_stickers_create_missing_image_bytes(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post("/api/v1/stickers", json={"image_type": "png"})
        assert r.status == 400
        assert (await r.json()).get("error") == "missing_image_bytes"


@pytest.mark.asyncio
async def test_stickers_create_invalid_base64(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post(
            "/api/v1/stickers",
            json={"image_type": "png", "image_bytes": "@@@not-valid-base64!!!"},
        )
        assert r.status == 400
        assert (await r.json()).get("error") == "invalid_base64"


@pytest.mark.asyncio
async def test_stickers_create_bad_payload(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    b64 = base64.b64encode(b"not-a-png").decode("ascii")
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post(
            "/api/v1/stickers",
            json={"image_type": "png", "image_bytes": b64},
        )
        assert r.status == 400
        assert "error" in await r.json()


@pytest.mark.asyncio
async def test_stickers_image_not_found(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.get("/api/v1/stickers/999999/image")
        assert r.status == 404


@pytest.mark.asyncio
async def test_stickers_import_invalid_document(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post(
            "/api/v1/stickers/import",
            json={"format": "wrong", "version": 1},
        )
        assert r.status == 400
        body = await r.json()
        assert "error" in body


@pytest.mark.asyncio
async def test_sticker_packs_create_list_get_delete(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    async with TestClient(TestServer(aio_app)) as client:
        cr = await client.post(
            "/api/v1/sticker-packs",
            json={"title": "  Pack One  ", "pack_type": "static"},
        )
        assert cr.status == 200
        pack = (await cr.json())["pack"]
        pid = pack["id"]

        ls = await client.get("/api/v1/sticker-packs")
        assert ls.status == 200
        packs = (await ls.json())["packs"]
        assert any(p["id"] == pid for p in packs)

        g = await client.get(f"/api/v1/sticker-packs/{pid}")
        assert g.status == 200
        assert (await g.json())["pack"]["id"] == pid

        dl = await client.delete(f"/api/v1/sticker-packs/{pid}")
        assert dl.status == 200


@pytest.mark.asyncio
async def test_sticker_packs_install_minimal(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    b64 = base64.b64encode(TINY_PNG).decode("ascii")
    doc = {
        "format": "meshchatx-stickerpack",
        "version": 1,
        "pack": {
            "title": "Imported Pack",
            "short_name": "imp",
            "description": None,
            "type": "static",
            "author": None,
            "is_strict": False,
        },
        "stickers": [
            {"name": "a", "emoji": None, "image_type": "png", "image_bytes": b64},
        ],
    }
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post("/api/v1/sticker-packs/install", json=doc)
        assert r.status == 200
        data = await r.json()
        assert "pack" in data
        assert data.get("imported", 0) >= 1


@pytest.mark.asyncio
async def test_sticker_packs_install_invalid(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post(
            "/api/v1/sticker-packs/install",
            json={"format": "meshchatx-stickerpack", "version": 1},
        )
        assert r.status == 400


@pytest.mark.asyncio
async def test_gifs_create_get_image_use_export_import(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    b64 = base64.b64encode(TINY_GIF).decode("ascii")
    async with TestClient(TestServer(aio_app)) as client:
        c = await client.post(
            "/api/v1/gifs",
            json={"name": "g", "image_type": "gif", "image_bytes": b64},
        )
        assert c.status == 200
        gid = (await c.json())["gif"]["id"]

        img = await client.get(f"/api/v1/gifs/{gid}/image")
        assert img.status == 200
        assert "gif" in (img.headers.get("Content-Type") or "").lower()
        assert await img.read() == TINY_GIF

        u = await client.post(f"/api/v1/gifs/{gid}/use")
        assert u.status == 200

        ex = await client.get("/api/v1/gifs/export")
        assert ex.status == 200
        doc = await ex.json()
        assert doc.get("format") == "meshchatx-gifs"

        imp = await client.post(
            "/api/v1/gifs/import",
            json={**doc, "replace_duplicates": True},
        )
        assert imp.status == 200
        assert (await imp.json()).get("imported", 0) >= 1


@pytest.mark.asyncio
async def test_gifs_create_missing_image_bytes(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post("/api/v1/gifs", json={"image_type": "gif"})
        assert r.status == 400
        assert (await r.json()).get("error") == "missing_image_bytes"


@pytest.mark.asyncio
async def test_gifs_patch_requires_name(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    b64 = base64.b64encode(TINY_GIF).decode("ascii")
    async with TestClient(TestServer(aio_app)) as client:
        c = await client.post(
            "/api/v1/gifs",
            json={"image_type": "gif", "image_bytes": b64},
        )
        gid = (await c.json())["gif"]["id"]
        r = await client.patch(f"/api/v1/gifs/{gid}", json={})
        assert r.status == 400
        assert (await r.json()).get("error") == "missing_name"


@pytest.mark.asyncio
async def test_gifs_image_not_found(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.get("/api/v1/gifs/999999/image")
        assert r.status == 404


@pytest.mark.asyncio
async def test_stickers_strict_tgs_golden_bytes(web_media_app):
    aio_app = _build_aio_app(web_media_app)
    b64 = base64.b64encode(GZIP_TGS_512).decode("ascii")
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post(
            "/api/v1/stickers",
            json={
                "name": "anim",
                "image_type": "tgs",
                "image_bytes": b64,
                "strict": True,
            },
        )
        assert r.status == 200
        st = (await r.json())["sticker"]
        assert st.get("image_type") == "tgs"
