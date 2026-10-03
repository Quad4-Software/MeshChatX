# SPDX-License-Identifier: 0BSD

"""Unit and route tests for the remote translation pack catalog."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.http.routes.translation import register_translation_routes
from meshchatx.src.backend.translation_catalog import group_records_by_pair
from meshchatx.src.backend.translation_pack_manager import TranslationPackManager


def _rec(pair_src, pair_tgt, ftype, arch="base-memory", name=None, size=10):
    return {
        "name": name or f"{ftype}.{pair_src}{pair_tgt}.bin",
        "fileType": ftype,
        "sourceLanguage": pair_src,
        "targetLanguage": pair_tgt,
        "architecture": arch,
        "attachment": {"location": f"loc/{ftype}", "size": size},
        "decompressedSize": size * 2,
        "decompressedHash": "ab" * 32,
    }


def _pair_records(src, tgt, arch="base-memory"):
    return [
        _rec(src, tgt, "model", arch),
        _rec(src, tgt, "lex", arch),
        _rec(src, tgt, "vocab", arch),
    ]


def test_group_records_prefers_base_over_tiny():
    recs = _pair_records("en", "es", "tiny") + _pair_records("en", "es", "base")
    pairs = group_records_by_pair(recs)
    assert pairs["enes"]["architecture"] == "base"


def test_group_records_falls_back_to_base_memory_and_tiny():
    recs = _pair_records("en", "es", "tiny") + _pair_records("de", "en", "base-memory")
    pairs = group_records_by_pair(recs)
    assert pairs["enes"]["architecture"] == "tiny"
    assert pairs["deen"]["architecture"] == "base-memory"


def test_group_records_skips_incomplete_pairs():
    recs = [r for r in _pair_records("en", "es") if r["fileType"] != "vocab"]
    pairs = group_records_by_pair(recs)
    assert "enes" not in pairs


def test_group_records_skips_unknown_arch():
    recs = _pair_records("en", "es", "nightly-weird")
    assert group_records_by_pair(recs) == {}


def test_group_records_maps_from_to():
    pairs = group_records_by_pair(_pair_records("ru", "en"))
    entry = pairs["ruen"]
    assert entry["from"] == "ru"
    assert entry["to"] == "en"
    assert entry["size"] == 60


@pytest.fixture
def catalog_http_client(tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    mgr = TranslationPackManager(str(storage))
    mesh_app = MagicMock()
    mesh_app.translation_pack_manager = mgr
    mesh_app.config = None
    routes = web.RouteTableDef()
    register_translation_routes(routes, mesh_app)
    aio_app = web.Application()
    aio_app.add_routes(routes)
    return aio_app, mgr


@pytest.mark.asyncio
async def test_catalog_route_returns_pairs(catalog_http_client, monkeypatch):
    aio_app, _mgr = catalog_http_client
    import meshchatx.src.backend.http.routes.translation as tr

    async def fake_catalog(timeout):
        return {"enes": {"pair": "enes", "from": "en", "to": "es",
                         "architecture": "base", "size": 100, "files": []}}

    monkeypatch.setattr(tr, "fetch_catalog", fake_catalog)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await client.get("/api/v1/translation/catalog")
        assert resp.status == 200
        body = await resp.json()
        assert body["pairs"][0]["pair"] == "enes"


@pytest.mark.asyncio
async def test_fetch_route_installs_pair(catalog_http_client, tmp_path, monkeypatch):
    aio_app, mgr = catalog_http_client
    import meshchatx.src.backend.http.routes.translation as tr

    entry = {"pair": "enes", "from": "en", "to": "es",
             "architecture": "base", "size": 100, "files": []}

    async def fake_catalog(timeout):
        return {"enes": entry}

    async def fake_download(pair_entry, dest_dir, timeout):
        import os
        pair_dir = os.path.join(dest_dir, "enes")
        os.makedirs(pair_dir, exist_ok=True)
        for name in ("model.enes.bin", "lex.enes.bin", "vocab.enes.spm"):
            with open(os.path.join(pair_dir, name), "wb") as fh:
                fh.write(b"x")
        return [pair_dir]

    monkeypatch.setattr(tr, "fetch_catalog", fake_catalog)
    monkeypatch.setattr(tr, "download_pair_files", fake_download)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await client.post(
            "/api/v1/translation/packs/fetch", json={"pair": "enes"}
        )
        assert resp.status == 200
        body = await resp.json()
        assert body["installed"] == ["enes"]
        assert mgr.list_installed()[0]["pair"] == "enes"


@pytest.mark.asyncio
async def test_fetch_route_unknown_pair(catalog_http_client, monkeypatch):
    aio_app, _mgr = catalog_http_client
    import meshchatx.src.backend.http.routes.translation as tr

    async def fake_catalog(timeout):
        return {}

    monkeypatch.setattr(tr, "fetch_catalog", fake_catalog)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await client.post(
            "/api/v1/translation/packs/fetch", json={"pair": "zzzz"}
        )
        assert resp.status == 404


@pytest.mark.asyncio
async def test_catalog_blocked_in_privacy_mode(tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    mgr = TranslationPackManager(str(storage))
    mesh_app = MagicMock()
    mesh_app.translation_pack_manager = mgr
    cfg = MagicMock()
    cfg.privacy_mode_enabled.get.return_value = True
    mesh_app.config = cfg
    routes = web.RouteTableDef()
    register_translation_routes(routes, mesh_app)
    aio_app = web.Application()
    aio_app.add_routes(routes)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await client.get("/api/v1/translation/catalog")
        assert resp.status >= 400
        resp2 = await client.post(
            "/api/v1/translation/packs/fetch", json={"pair": "enes"}
        )
        assert resp2.status >= 400


def test_zstd_decompress_roundtrip():
    from meshchatx.src.backend.translation_catalog import _decompress_zstd

    try:
        from compression import zstd
    except ImportError:
        pytest.skip("compression.zstd unavailable")
    payload = zstd.compress(b"pack-data")
    assert _decompress_zstd(payload) == b"pack-data"
