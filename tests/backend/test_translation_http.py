# SPDX-License-Identifier: 0BSD

"""HTTP oracles for local translation pack routes."""

from __future__ import annotations

import io
import json
import os
import zipfile
from unittest.mock import MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.http.routes.translation import register_translation_routes
from meshchatx.src.backend.translation_pack_manager import TranslationPackManager


@pytest.fixture
def translation_http_client(tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    mgr = TranslationPackManager(str(storage))
    mesh_app = MagicMock()
    mesh_app.translation_pack_manager = mgr
    routes = web.RouteTableDef()
    register_translation_routes(routes, mesh_app)
    aio_app = web.Application()
    aio_app.add_routes(routes)
    return aio_app, mgr


def _pack_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("enes/model.enes.npz", b"model")
        zf.writestr("enes/lex.s2t.bin", b"lex")
        zf.writestr("enes/vocab.spm", b"vocab")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_list_packs_empty(translation_http_client):
    aio_app, _mgr = translation_http_client
    async with TestClient(TestServer(aio_app)) as client:
        resp = await client.get("/api/v1/translation/packs")
        assert resp.status == 200
        body = await resp.json()
        assert body["packs"] == []


@pytest.mark.asyncio
async def test_import_pack_and_list(translation_http_client):
    aio_app, mgr = translation_http_client
    async with TestClient(TestServer(aio_app)) as client:
        data = {"file": io.BytesIO(_pack_zip())}
        resp = await client.post("/api/v1/translation/packs/import", data=data)
        assert resp.status == 200
        body = await resp.json()
        assert body["pairs"] == ["enes"]

        resp = await client.get("/api/v1/translation/packs")
        body = await resp.json()
        assert len(body["packs"]) == 1
        assert body["packs"][0]["pair"] == "enes"
        assert mgr.safe_file_path("enes/model.enes.npz")


@pytest.mark.asyncio
async def test_import_pack_rejects_missing_field(translation_http_client):
    aio_app, _mgr = translation_http_client
    async with TestClient(TestServer(aio_app)) as client:
        resp = await client.post("/api/v1/translation/packs/import", data={})
        assert resp.status == 400


@pytest.mark.asyncio
async def test_remove_pack(translation_http_client):
    aio_app, _mgr = translation_http_client
    async with TestClient(TestServer(aio_app)) as client:
        data = {"file": io.BytesIO(_pack_zip())}
        await client.post("/api/v1/translation/packs/import", data=data)

        resp = await client.delete("/api/v1/translation/packs/enes")
        assert resp.status == 200
        assert (await resp.json())["removed"] == "enes"

        resp = await client.delete("/api/v1/translation/packs/enes")
        assert resp.status == 404


@pytest.mark.asyncio
async def test_serve_pack_file(translation_http_client):
    aio_app, _mgr = translation_http_client
    async with TestClient(TestServer(aio_app)) as client:
        data = {"file": io.BytesIO(_pack_zip())}
        await client.post("/api/v1/translation/packs/import", data=data)

        resp = await client.get("/translation-packs/enes/model.enes.npz")
        assert resp.status == 200
        assert await resp.read() == b"model"

        resp = await client.get("/translation-packs/../etc/passwd")
        assert resp.status == 404
