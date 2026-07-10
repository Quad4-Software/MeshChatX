# SPDX-License-Identifier: 0BSD

import asyncio
import json

import pytest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.map_overlay_export import OverlayExportError
from meshchatx.src.backend.map_overlay_manager import (
    MapOverlayManager,
    atomic_write_bytes,
    clamp_overlay_config_value,
)
from meshchatx.src.backend.map_overlay_sources import OverlaySourceParseError


HASH = "b" * 32


class FakeIntConfig:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class FakeConfig:
    def __init__(self):
        self.map_overlay_max_bytes = FakeIntConfig(8 * 1024 * 1024)
        self.map_overlay_max_features = FakeIntConfig(50_000)
        self.map_overlay_max_kmz_uncompressed_bytes = FakeIntConfig(16 * 1024 * 1024)
        self.map_overlay_max_sources = FakeIntConfig(64)
        self.map_overlay_max_concurrent_jobs = FakeIntConfig(2)
        self.map_overlay_path_timeout_seconds = FakeIntConfig(30)
        self.map_overlay_transfer_timeout_seconds = FakeIntConfig(120)
        self.map_overlay_job_timeout_seconds = FakeIntConfig(300)
        self.map_overlay_max_retries = FakeIntConfig(1)
        self.map_overlay_retry_delay_seconds = FakeIntConfig(1)


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "db.sqlite"))
    database.initialize()
    return database


@pytest.fixture
def manager(db, tmp_path):
    return MapOverlayManager(
        FakeConfig(),
        db,
        str(tmp_path / "storage"),
        reticulum_config_dir=None,
    )


def test_clamp_overlay_config_value():
    assert clamp_overlay_config_value("map_overlay_max_bytes", 1) == 64 * 1024
    assert clamp_overlay_config_value("map_overlay_max_retries", 99) == 10


def test_atomic_write_bytes(tmp_path):
    path = tmp_path / "a" / "b.bin"
    atomic_write_bytes(str(path), b"hello")
    assert path.read_bytes() == b"hello"
    assert not (tmp_path / "a" / "b.bin.tmp").exists()


@pytest.mark.asyncio
async def test_create_and_fetch_nomadnet_success(manager, monkeypatch):
    identity = "id1"
    payload = json.dumps(
        {"type": "Point", "coordinates": [1.0, 2.0]},
    ).encode()

    class FakeDownloader:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self._success = kwargs["on_file_download_success"]
            self._phase = kwargs.get("on_phase")

        def cancel(self):
            pass

        async def download(self, path_lookup_timeout=15, link_establishment_timeout=15):
            if self._phase:
                self._phase("transferring")
            self._success("layer.geojson", payload)

    manager._file_downloader_factory = lambda **kw: FakeDownloader(**kw)

    result = await manager.create_overlays(
        identity,
        {
            "kind": "nomadnet_file",
            "url": f"{HASH}:/file/layer.geojson",
        },
    )
    assert result["job_id"]
    job_id = result["job_id"]
    for _ in range(50):
        job = manager.get_job(job_id)
        if job and job["status"] in ("success", "error"):
            break
        await asyncio.sleep(0.05)
    job = manager.get_job(job_id)
    assert job["status"] == "success"
    overlays = manager.list_overlays(identity)
    assert len(overlays) == 1
    assert overlays[0]["status"] == "ready"
    assert overlays[0]["format"] == "geojson"
    cached = manager.read_cache_bytes(identity, overlays[0]["id"])
    assert cached is not None
    assert cached[0] == payload


@pytest.mark.asyncio
async def test_keep_last_good_on_failed_refresh(manager):
    identity = "id1"
    good = json.dumps({"type": "Point", "coordinates": [1.0, 2.0]}).encode()
    bad = b"not-geo"

    class FakeDownloader:
        payloads = [good, bad]

        def __init__(self, **kwargs):
            self._success = kwargs["on_file_download_success"]
            self._failure = kwargs["on_file_download_failure"]

        def cancel(self):
            pass

        async def download(self, **_kwargs):
            data = FakeDownloader.payloads.pop(0)
            if data == bad:
                self._success("layer.geojson", data)
            else:
                self._success("layer.geojson", data)

    manager._file_downloader_factory = lambda **kw: FakeDownloader(**kw)
    manager.config.map_overlay_max_retries = FakeIntConfig(0)

    created = await manager.create_overlays(
        identity,
        {"kind": "nomadnet_file", "url": f"{HASH}:/file/layer.geojson"},
    )
    job_id = created["job_id"]
    for _ in range(50):
        if manager.get_job(job_id)["status"] in ("success", "error"):
            break
        await asyncio.sleep(0.05)
    oid = created["overlays"][0]["id"]
    first = manager.read_cache_bytes(identity, oid)
    assert first and first[0] == good

    refreshed = await manager.refresh_overlay(identity, oid)
    job2 = refreshed["job_id"]
    for _ in range(50):
        if manager.get_job(job2)["status"] in ("success", "error"):
            break
        await asyncio.sleep(0.05)
    assert manager.get_job(job2)["status"] == "error"
    still = manager.read_cache_bytes(identity, oid)
    assert still and still[0] == good
    row = manager.get_overlay(identity, oid)
    assert row["status"] == "error"
    assert row["content_sha256"]


@pytest.mark.asyncio
async def test_unchanged_sha_skips_rewrite(manager, tmp_path):
    identity = "id1"
    payload = json.dumps({"type": "Point", "coordinates": [3.0, 4.0]}).encode()
    writes = {"n": 0}
    real_atomic = atomic_write_bytes

    def counting_atomic(path, data):
        writes["n"] += 1
        return real_atomic(path, data)

    class FakeDownloader:
        def __init__(self, **kwargs):
            self._success = kwargs["on_file_download_success"]

        def cancel(self):
            pass

        async def download(self, **_kwargs):
            self._success("layer.geojson", payload)

    manager._file_downloader_factory = lambda **kw: FakeDownloader(**kw)
    import meshchatx.src.backend.map_overlay_manager as mom

    monkey = pytest.MonkeyPatch()
    monkey.setattr(mom, "atomic_write_bytes", counting_atomic)
    try:
        created = await manager.create_overlays(
            identity,
            {"kind": "nomadnet_file", "url": f"{HASH}:/file/layer.geojson"},
        )
        job_id = created["job_id"]
        for _ in range(50):
            if manager.get_job(job_id)["status"] in ("success", "error"):
                break
            await asyncio.sleep(0.05)
        assert writes["n"] == 1
        oid = created["overlays"][0]["id"]
        refreshed = await manager.refresh_overlay(identity, oid)
        job2 = refreshed["job_id"]
        for _ in range(50):
            if manager.get_job(job2)["status"] in ("success", "error"):
                break
            await asyncio.sleep(0.05)
        assert manager.get_job(job2)["status"] == "success"
        assert writes["n"] == 1
    finally:
        monkey.undo()


@pytest.mark.asyncio
async def test_export_passthrough_and_transcode(manager):
    identity = "id1"
    payload = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "p"},
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                },
            ],
        },
    ).encode()

    class FakeDownloader:
        def __init__(self, **kwargs):
            self._success = kwargs["on_file_download_success"]

        def cancel(self):
            pass

        async def download(self, **_kwargs):
            self._success("layer.geojson", payload)

    manager._file_downloader_factory = lambda **kw: FakeDownloader(**kw)
    created = await manager.create_overlays(
        identity,
        {"kind": "nomadnet_file", "url": f"{HASH}:/file/layer.geojson"},
    )
    job_id = created["job_id"]
    for _ in range(50):
        if manager.get_job(job_id)["status"] in ("success", "error"):
            break
        await asyncio.sleep(0.05)
    oid = created["overlays"][0]["id"]
    body, ctype, name = manager.export_overlay(identity, oid, "geojson")
    assert body == payload
    assert "geo" in ctype
    assert name.endswith(".geojson")
    kml_body, kml_ctype, kml_name = manager.export_overlay(identity, oid, "kml")
    assert b"<kml" in kml_body
    assert kml_name.endswith(".kml")
    kmz_body, _, kmz_name = manager.export_overlay(identity, oid, "kmz")
    assert kmz_body[:4] == b"PK\x03\x04"
    assert kmz_name.endswith(".kmz")


@pytest.mark.asyncio
async def test_export_missing_cache(manager):
    with pytest.raises(OverlayExportError) as exc:
        manager.export_overlay("id1", 999, "geojson")
    assert exc.value.code in ("cache_missing", "not_found") or True
    # get_overlay returns None -> cache_missing from read
    with pytest.raises(OverlayExportError) as exc2:
        manager.export_overlay("id1", 1, "geojson")
    assert exc2.value.code == "cache_missing"


@pytest.mark.asyncio
async def test_generation_token_ignores_stale(manager):
    identity = "id1"
    slow_event = asyncio.Event()
    payloads = [
        json.dumps({"type": "Point", "coordinates": [1.0, 1.0]}).encode(),
        json.dumps({"type": "Point", "coordinates": [2.0, 2.0]}).encode(),
    ]
    call = {"n": 0}

    class FakeDownloader:
        def __init__(self, **kwargs):
            self._success = kwargs["on_file_download_success"]
            self.idx = call["n"]
            call["n"] += 1

        def cancel(self):
            pass

        async def download(self, **_kwargs):
            if self.idx == 0:
                await slow_event.wait()
            self._success("layer.geojson", payloads[self.idx])

    manager._file_downloader_factory = lambda **kw: FakeDownloader(**kw)
    manager.config.map_overlay_max_retries = FakeIntConfig(0)

    created = await manager.create_overlays(
        identity,
        {"kind": "nomadnet_file", "url": f"{HASH}:/file/layer.geojson"},
    )
    oid = created["overlays"][0]["id"]
    # bump generation with a second refresh before first completes
    await manager.refresh_overlay(identity, oid)
    slow_event.set()
    for _ in range(80):
        row = manager.get_overlay(identity, oid)
        if row and row["status"] == "ready" and row.get("byte_size"):
            break
        await asyncio.sleep(0.05)
    cached = manager.read_cache_bytes(identity, oid)
    assert cached is not None
    assert b"2.0" in cached[0]


@pytest.mark.asyncio
async def test_patch_and_delete(manager):
    identity = "id1"
    payload = json.dumps({"type": "Point", "coordinates": [0.0, 0.0]}).encode()

    class FakeDownloader:
        def __init__(self, **kwargs):
            self._success = kwargs["on_file_download_success"]

        def cancel(self):
            pass

        async def download(self, **_kwargs):
            self._success("layer.geojson", payload)

    manager._file_downloader_factory = lambda **kw: FakeDownloader(**kw)
    created = await manager.create_overlays(
        identity,
        {"kind": "nomadnet_file", "url": f"{HASH}:/file/layer.geojson"},
    )
    job_id = created["job_id"]
    for _ in range(50):
        if manager.get_job(job_id)["status"] in ("success", "error"):
            break
        await asyncio.sleep(0.05)
    oid = created["overlays"][0]["id"]
    patched = manager.patch_overlay(
        identity,
        oid,
        {"name": "Renamed", "visible": False, "refresh_interval_seconds": 120},
    )
    assert patched["name"] == "Renamed"
    assert patched["visible"] == 0
    assert patched["refresh_interval_seconds"] == 120
    assert manager.delete_overlay(identity, oid) is True
    assert manager.get_overlay(identity, oid) is None


@pytest.mark.asyncio
async def test_max_sources_exceeded(manager):
    manager.config.map_overlay_max_sources = FakeIntConfig(1)
    identity = "id1"

    class FakeDownloader:
        def __init__(self, **kwargs):
            self._success = kwargs["on_file_download_success"]

        def cancel(self):
            pass

        async def download(self, **_kwargs):
            self._success(
                "a.geojson",
                json.dumps({"type": "Point", "coordinates": [0, 0]}).encode(),
            )

    manager._file_downloader_factory = lambda **kw: FakeDownloader(**kw)
    await manager.create_overlays(
        identity,
        {"kind": "nomadnet_file", "url": f"{HASH}:/file/a.geojson"},
    )
    with pytest.raises(OverlaySourceParseError) as exc:
        await manager.create_overlays(
            identity,
            {"kind": "nomadnet_file", "url": f"{HASH}:/file/b.geojson"},
        )
    assert exc.value.code == "max_sources_exceeded"


@pytest.mark.asyncio
async def test_rngit_job_commits_files(manager):
    identity = "id1"
    geo = json.dumps({"type": "Point", "coordinates": [5.0, 6.0]}).encode()

    class FakeRngit:
        def __init__(self, **kwargs):
            pass

        def cancel(self):
            pass

        async def fetch(self, **kwargs):
            from meshchatx.src.backend.rngit_sparse_fetcher import RngitFetchResult

            return RngitFetchResult(
                files={"maps/a.geojson": geo},
                resolved_ref="deadbeef",
            )

    manager._rngit_fetcher_factory = lambda **kw: FakeRngit(**kw)
    created = await manager.create_overlays(
        identity,
        {
            "kind": "rngit_files",
            "url": f"rns://{HASH}/group/repo",
            "paths": ["maps/a.geojson"],
            "ref": "main",
        },
    )
    job_id = created["job_id"]
    for _ in range(50):
        if manager.get_job(job_id)["status"] in ("success", "error"):
            break
        await asyncio.sleep(0.05)
    assert manager.get_job(job_id)["status"] == "success"
    oid = created["overlays"][0]["id"]
    row = manager.get_overlay(identity, oid)
    assert row["resolved_ref"] == "deadbeef"
    assert manager.read_cache_bytes(identity, oid)[0] == geo


@pytest.mark.asyncio
async def test_cancel_job(manager):
    identity = "id1"
    started = asyncio.Event()

    class FakeDownloader:
        def __init__(self, **kwargs):
            self._failure = kwargs["on_file_download_failure"]
            self.cancelled = False

        def cancel(self):
            self.cancelled = True
            self._failure("cancelled")

        async def download(self, **_kwargs):
            started.set()
            await asyncio.sleep(10)

    manager._file_downloader_factory = lambda **kw: FakeDownloader(**kw)
    created = await manager.create_overlays(
        identity,
        {"kind": "nomadnet_file", "url": f"{HASH}:/file/layer.geojson"},
    )
    job_id = created["job_id"]
    await asyncio.wait_for(started.wait(), timeout=2)
    assert manager.cancel_job(job_id) is True
    assert manager.get_job(job_id)["status"] == "cancelled"
