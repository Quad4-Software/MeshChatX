# SPDX-License-Identifier: 0BSD

"""Unit and route tests for the remote translation pack catalog."""

from __future__ import annotations

import hashlib
import os
from unittest.mock import MagicMock

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.http.routes.translation import register_translation_routes
from meshchatx.src.backend.translation_catalog import group_records_by_pair
from meshchatx.src.backend.translation_pack_manager import (
    TranslationPackError,
    TranslationPackManager,
)


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
        return {
            "enes": {
                "pair": "enes",
                "from": "en",
                "to": "es",
                "architecture": "base",
                "size": 100,
                "files": [],
            }
        }

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

    entry = {
        "pair": "enes",
        "from": "en",
        "to": "es",
        "architecture": "base",
        "size": 100,
        "files": [],
    }

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


def _zstd_compress(data: bytes) -> bytes:
    try:
        from compression import zstd

        return zstd.compress(data)
    except ImportError:
        pytest.skip("compression.zstd unavailable")


def _cdn_record(src, tgt, ftype, arch, name, payload, cdn_location=None):
    return {
        "name": name,
        "fileType": ftype,
        "sourceLanguage": src,
        "targetLanguage": tgt,
        "architecture": arch,
        "attachment": {
            "location": cdn_location or f"files/{name}.zst",
            "size": len(payload),
        },
        "decompressedSize": len(payload),
        "decompressedHash": hashlib.sha256(payload).hexdigest(),
    }


@pytest.fixture
async def cdn_server(tmp_path):
    """Local HTTP stand-in for the records API and the attachment CDN."""
    payloads = {
        "model.enes.intgemm.bin": b"model-bytes-enes",
        "lex.50.50.enes.s2t.bin": b"lex-bytes-enes",
        "vocab.enes.spm": b"vocab-bytes-enes",
    }
    records = [
        _cdn_record(
            "en",
            "es",
            "model",
            "base-memory",
            "model.enes.intgemm.bin",
            payloads["model.enes.intgemm.bin"],
        ),
        _cdn_record(
            "en",
            "es",
            "lex",
            "base-memory",
            "lex.50.50.enes.s2t.bin",
            payloads["lex.50.50.enes.s2t.bin"],
        ),
        _cdn_record(
            "en",
            "es",
            "vocab",
            "base-memory",
            "vocab.enes.spm",
            payloads["vocab.enes.spm"],
        ),
    ]

    async def records_handler(request):
        return web.json_response({"data": records})

    async def file_handler(request):
        name = request.match_info["name"]
        base = name.removesuffix(".zst")
        if base not in payloads:
            return web.Response(status=404)
        value = payloads[base]
        if isinstance(value, tuple) and value[0] == "raw":
            return web.Response(body=value[1])
        return web.Response(body=_zstd_compress(value))

    srv = web.Application()
    srv.router.add_get("/records", records_handler)
    srv.router.add_get("/files/{name}.zst", file_handler)
    server = TestServer(srv)
    client = TestClient(server)
    await client.start_server()
    base = str(client.make_url(""))
    return {"base": base, "records": records, "payloads": payloads, "client": client}


@pytest.mark.asyncio
async def test_fetch_catalog_over_http(cdn_server, monkeypatch):
    import meshchatx.src.backend.translation_catalog as cat

    monkeypatch.setattr(cat, "CATALOG_URL", f"{cdn_server['base']}/records")
    pairs = await cat.fetch_catalog(aiohttp.ClientTimeout(total=30))
    assert set(pairs) == {"enes"}
    entry = pairs["enes"]
    assert entry["architecture"] == "base-memory"
    assert {f["type"] for f in entry["files"]} == {"model", "lex", "vocab"}
    assert entry["size"] == sum(len(p) for p in cdn_server["payloads"].values())
    await cdn_server["client"].close()


@pytest.mark.asyncio
async def test_download_pair_files_over_http(cdn_server, tmp_path, monkeypatch):
    import meshchatx.src.backend.translation_catalog as cat

    monkeypatch.setattr(cat, "ATTACHMENT_CDN", cdn_server["base"])
    entry = cat.group_records_by_pair(cdn_server["records"])["enes"]
    written = await cat.download_pair_files(
        entry, str(tmp_path), aiohttp.ClientTimeout(total=30)
    )
    assert len(written) == 3
    pair_dir = tmp_path / "enes"
    for name, payload in cdn_server["payloads"].items():
        assert (pair_dir / name).read_bytes() == payload
    await cdn_server["client"].close()


@pytest.mark.asyncio
async def test_download_pair_files_checksum_mismatch_cleans_written(
    cdn_server, tmp_path, monkeypatch
):
    import meshchatx.src.backend.translation_catalog as cat

    monkeypatch.setattr(cat, "ATTACHMENT_CDN", cdn_server["base"])
    records = list(cdn_server["records"])
    bad = dict(records[0])
    bad["decompressedHash"] = "00" * 32
    records[0] = bad
    # Order matters here: a good file first, then the corrupt one.
    records = [records[1], bad, records[2]]
    entry = cat.group_records_by_pair(records)["enes"]
    with pytest.raises(TranslationPackError, match="Checksum mismatch"):
        await cat.download_pair_files(
            entry, str(tmp_path), aiohttp.ClientTimeout(total=30)
        )
    pair_dir = tmp_path / "enes"
    assert pair_dir.is_dir()
    assert list(pair_dir.iterdir()) == []
    await cdn_server["client"].close()


@pytest.mark.asyncio
async def test_download_pair_files_http_error(cdn_server, tmp_path, monkeypatch):
    import meshchatx.src.backend.translation_catalog as cat

    monkeypatch.setattr(cat, "ATTACHMENT_CDN", cdn_server["base"])
    entry = {
        "pair": "enes",
        "files": [
            {
                "name": "model.missing.bin",
                "type": "model",
                "location": "files/missing.bin.zst",
                "compressed_size": 0,
                "decompressed_size": 0,
                "decompressed_hash": "",
            }
        ],
    }
    with pytest.raises(aiohttp.ClientResponseError):
        await cat.download_pair_files(
            entry, str(tmp_path), aiohttp.ClientTimeout(total=30)
        )
    await cdn_server["client"].close()


@pytest.mark.asyncio
async def test_download_pair_files_corrupt_zstd(cdn_server, tmp_path, monkeypatch):
    import meshchatx.src.backend.translation_catalog as cat

    monkeypatch.setattr(cat, "ATTACHMENT_CDN", cdn_server["base"])
    cdn_server["payloads"]["model.enes.intgemm.bin"] = ("raw", b"not-zstd-data")
    entry = {
        "pair": "enes",
        "files": [
            {
                "name": "model.enes.intgemm.bin",
                "type": "model",
                "location": "files/model.enes.intgemm.bin.zst",
                "compressed_size": 0,
                "decompressed_size": 0,
                "decompressed_hash": "",
            }
        ],
    }
    try:
        from compression.zstd import ZstdError
    except ImportError:
        ZstdError = Exception
    with pytest.raises(ZstdError):
        await cat.download_pair_files(
            entry, str(tmp_path), aiohttp.ClientTimeout(total=30)
        )
    await cdn_server["client"].close()


def test_install_files_dir_registers_pack(tmp_path):
    from meshchatx.src.backend.translation_pack_manager import TranslationPackManager

    mgr = TranslationPackManager(str(tmp_path / "storage"))
    staging = tmp_path / "staging"
    pair_dir = staging / "enes"
    pair_dir.mkdir(parents=True)
    for name in ("model.enes.bin", "lex.enes.bin", "vocab.enes.spm"):
        (pair_dir / name).write_bytes(b"x" * 16)
    installed = mgr.install_files_dir(str(pair_dir), "enes")
    assert installed == ["enes"]
    packs = mgr.list_installed()
    assert packs[0]["pair"] == "enes"
    assert (tmp_path / "storage" / "translation-packs" / "registry.json").exists()


def test_install_files_dir_rejects_wrong_dir(tmp_path):
    from meshchatx.src.backend.translation_pack_manager import TranslationPackManager

    mgr = TranslationPackManager(str(tmp_path / "storage"))
    with pytest.raises(TranslationPackError, match="Pair directory missing"):
        mgr.install_files_dir(str(tmp_path), "enes")


@pytest.mark.asyncio
async def test_fetch_route_all_partial_failure(catalog_http_client, monkeypatch):
    aio_app, mgr = catalog_http_client
    import meshchatx.src.backend.http.routes.translation as tr

    def _entry(pair):
        return {
            "pair": pair,
            "from": pair[:2],
            "to": pair[2:4],
            "architecture": "base",
            "size": 10,
            "files": [],
        }

    pairs = {"enes": _entry("enes"), "deen": _entry("deen")}

    async def fake_catalog(timeout):
        return pairs

    async def fake_download(pair_entry, dest_dir, timeout):
        import os

        if pair_entry["pair"] == "deen":
            raise RuntimeError("boom")
        pair_dir = os.path.join(dest_dir, "enes")
        os.makedirs(pair_dir, exist_ok=True)
        for name in ("model.enes.bin", "lex.enes.bin", "vocab.enes.spm"):
            with open(os.path.join(pair_dir, name), "wb") as fh:
                fh.write(b"x")
        return [pair_dir]

    monkeypatch.setattr(tr, "fetch_catalog", fake_catalog)
    monkeypatch.setattr(tr, "download_pair_files", fake_download)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await client.post("/api/v1/translation/packs/fetch", json={"all": True})
        assert resp.status == 207
        body = await resp.json()
        assert body["installed"] == ["enes"]
        assert body["failed"][0]["pair"] == "deen"
        installed = {p["pair"] for p in mgr.list_installed()}
        assert installed == {"enes"}
        # staging dirs are cleaned up even for the failed pair
        incoming = mgr.incoming_dir
        leftovers = (
            [d for d in os.listdir(incoming) if d != "enes"]
            if os.path.isdir(incoming)
            else []
        )
        assert leftovers == []


@pytest.mark.asyncio
async def test_fetch_route_rejects_missing_pair_arg(catalog_http_client):
    aio_app, _mgr = catalog_http_client
    async with TestClient(TestServer(aio_app)) as client:
        resp = await client.post("/api/v1/translation/packs/fetch", json={})
        assert resp.status == 400
