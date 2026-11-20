# SPDX-License-Identifier: 0BSD
"""Local .pmtiles offline archives: manager helpers and HTTP range serving."""

import asyncio
import os
import shutil
import struct
import tempfile
from unittest.mock import MagicMock

import pytest
from aiohttp import FormData, web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.http.safe_file_response import file_response
from meshchatx.src.backend.map_manager import (
    MapManager,
    is_pmtiles_filename,
    read_pmtiles_header,
)


def _varint(out, v):
    while v > 0x7F:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v)


def _zxy_to_tile_id(z, x, y):
    if z == 0:
        return 0
    acc = ((1 << (z * 2)) - 1) // 3
    n = 1 << z
    tx, ty, d = x, y, 0
    s = n // 2
    while s > 0:
        rx = 1 if tx & s else 0
        ry = 1 if ty & s else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                tx, ty = n - 1 - tx, n - 1 - ty
            tx, ty = ty, tx
        s //= 2
    return acc + d


def build_pmtiles(tiles, tile_type=1):
    """Minimal v3 archive: header, uncompressed root dir, tile payloads."""
    entries = sorted(
        ((_zxy_to_tile_id(z, x, y), data) for z, x, y, data in tiles),
        key=lambda e: e[0],
    )
    dir_bytes = bytearray()
    _varint(dir_bytes, len(entries))
    last = 0
    for tid, _ in entries:
        _varint(dir_bytes, tid - last)
        last = tid
    for _ in entries:
        _varint(dir_bytes, 1)
    for _, data in entries:
        _varint(dir_bytes, len(data))
    cursor = 0
    for _, data in entries:
        _varint(dir_bytes, cursor + 1)
        cursor += len(data)

    tile_data_off = 127 + len(dir_bytes)
    tile_data_len = sum(len(d) for _, d in entries)
    head = bytearray(127)
    head[0:7] = b"PMTiles"
    head[7] = 3
    for off, val in (
        (8, 127),
        (16, len(dir_bytes)),
        (24, 0),
        (32, 0),
        (40, 0),
        (48, 0),
        (56, tile_data_off),
        (64, tile_data_len),
        (72, len(entries)),
        (80, len(entries)),
        (88, len(entries)),
    ):
        struct.pack_into("<Q", head, off, val)
    head[96] = 1
    head[97] = 1
    head[98] = 1
    head[99] = tile_type
    head[100] = 0
    head[101] = 15
    struct.pack_into("<i", head, 102, int(-180 * 1e7))
    struct.pack_into("<i", head, 106, int(-85 * 1e7))
    struct.pack_into("<i", head, 110, int(180 * 1e7))
    struct.pack_into("<i", head, 114, int(85 * 1e7))
    head[118] = 1

    body = bytearray(head)
    body += dir_bytes
    for _, data in entries:
        body += data
    return bytes(body)


TILE_PAYLOAD = b"\x1a\x0b\x0a\x01a\x12\x02\x32\x00\x78\x02"
PNG_PAYLOAD = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.map_offline_path.get.return_value = None
    cfg.map_mbtiles_dir.get.return_value = None
    return cfg


@pytest.fixture
def archive_path(temp_dir):
    p = os.path.join(temp_dir, "region.pmtiles")
    with open(p, "wb") as f:
        f.write(
            build_pmtiles(
                [
                    (0, 0, 0, TILE_PAYLOAD),
                    (1, 0, 0, TILE_PAYLOAD),
                    (1, 1, 0, TILE_PAYLOAD),
                    (1, 0, 1, TILE_PAYLOAD),
                    (1, 1, 1, TILE_PAYLOAD),
                ]
            )
        )
    return p


def test_is_pmtiles_filename():
    assert is_pmtiles_filename("Planet.PMTiles")
    assert not is_pmtiles_filename("map.mbtiles")
    assert not is_pmtiles_filename(None)


def test_read_pmtiles_header(archive_path):
    h = read_pmtiles_header(archive_path)
    assert h is not None
    assert h["format"] == "pmtiles"
    assert h["tile_type"] == 1
    assert h["tile_type_name"] == "mvt"
    assert h["minzoom"] == "0" and h["maxzoom"] == "15"
    assert h["tile_data_offset"] > 127


def test_read_pmtiles_header_rejects_garbage(temp_dir):
    p = os.path.join(temp_dir, "bad.pmtiles")
    with open(p, "wb") as f:
        f.write(b"\x89PNG" + b"\x00" * 200)
    assert read_pmtiles_header(p) is None
    with open(p, "wb") as f:
        f.write(b"PMTiles" + bytes([2]) + b"\x00" * 120)  # v2 rejected
    assert read_pmtiles_header(p) is None
    with open(p, "wb") as f:
        f.write(b"PMTiles")
    assert read_pmtiles_header(p) is None


def test_list_and_get_pmtiles(mock_config, temp_dir, archive_path):
    mm = MapManager(mock_config, temp_dir)
    lst = mm.list_pmtiles()
    assert len(lst) == 1
    assert lst[0]["name"] == "region.pmtiles"
    assert lst[0]["type"] == "pmtiles"
    assert lst[0]["header"]["tile_type_name"] == "mvt"

    assert mm.get_pmtiles_path("region.pmtiles") == archive_path
    # basename() strips directory parts so traversal resolves inside the jail
    assert mm.get_pmtiles_path("../region.pmtiles") == archive_path
    assert mm.get_pmtiles_path("..%2Fregion.pmtiles") is None
    assert mm.get_pmtiles_path("..") is None
    assert mm.get_pmtiles_path(".") is None
    assert mm.get_pmtiles_path("missing.pmtiles") is None
    assert mm.get_pmtiles_path("region.pmtiles\x00.png") is None
    other = os.path.join(temp_dir, "notpmtiles.mbtiles")
    open(other, "wb").close()
    assert mm.get_pmtiles_path("notpmtiles.mbtiles") is None


def test_symlink_outside_dir_rejected(mock_config, temp_dir, archive_path):
    outside = tempfile.mkdtemp()
    try:
        target = os.path.join(outside, "escape.pmtiles")
        with open(target, "wb") as f:
            f.write(b"PMTiles" + bytes([3]) + b"\x00" * 120)
        link = os.path.join(temp_dir, "escape.pmtiles")
        os.symlink(target, link)
        mm = MapManager(mock_config, temp_dir)
        assert mm.get_pmtiles_path("escape.pmtiles") is None
    finally:
        shutil.rmtree(outside, ignore_errors=True)


def test_delete_pmtiles(mock_config, temp_dir, archive_path):
    mock_config.map_offline_path.get.return_value = archive_path
    mm = MapManager(mock_config, temp_dir)
    assert mm.delete_pmtiles("region.pmtiles")
    assert not os.path.exists(archive_path)
    mock_config.map_offline_path.set.assert_any_call(None)
    mock_config.map_offline_enabled.set.assert_any_call(False)
    assert not mm.delete_pmtiles("region.pmtiles")


def test_get_metadata_pmtiles(mock_config, temp_dir, archive_path):
    mock_config.map_offline_path.get.return_value = archive_path
    mm = MapManager(mock_config, temp_dir)
    md = mm.get_metadata()
    assert md["format"] == "pmtiles"
    assert md["minzoom"] == "0"


def _serve_app(path):
    app = web.Application()

    async def serve(request):
        return file_response(path)

    app.router.add_get("/archive", serve)
    return app


@pytest.mark.asyncio
async def test_range_requests(archive_path):
    size = os.path.getsize(archive_path)
    async with TestClient(TestServer(_serve_app(archive_path))) as client:
        r = await client.get("/archive")
        assert r.status == 200
        assert r.headers.get("Accept-Ranges") == "bytes"
        assert "Last-Modified" in r.headers
        await r.release()

        r = await client.get("/archive", headers={"Range": "bytes=0-126"})
        assert r.status == 206
        body = await r.read()
        assert len(body) == 127
        assert body[:7] == b"PMTiles"
        assert r.headers["Content-Range"] == f"bytes 0-126/{size}"
        await r.release()

        # tail range, open-ended
        r = await client.get("/archive", headers={"Range": f"bytes={size - 10}-"})
        assert r.status == 206
        assert len(await r.read()) == 10
        await r.release()

        # out of bounds -> 416
        r = await client.get("/archive", headers={"Range": f"bytes={size + 100}-"})
        assert r.status == 416
        await r.release()

        # malformed range -> 416
        r = await client.get("/archive", headers={"Range": "bytes=zzz-1"})
        assert r.status == 416
        await r.release()

        # HEAD must not hang or read the file
        r = await client.head("/archive")
        assert r.status == 200
        await r.release()


@pytest.mark.asyncio
async def test_conditional_requests(archive_path):
    async with TestClient(TestServer(_serve_app(archive_path))) as client:
        r = await client.get("/archive", headers={"Range": "bytes=0-9"})
        assert r.status == 206
        last_mod = r.headers.get("Last-Modified")
        await r.release()

        # If-Range with the same Last-Modified keeps serving 206
        r = await client.get(
            "/archive",
            headers={"Range": "bytes=0-9", "If-Range": last_mod},
        )
        assert r.status == 206
        await r.release()

        # If-Range with a stale date falls back to the full entity (200)
        r = await client.get(
            "/archive",
            headers={"Range": "bytes=0-9", "If-Range": "Wed, 01 Jan 2020 00:00:00 GMT"},
        )
        assert r.status == 200
        body = await r.read()
        assert len(body) == os.path.getsize(archive_path)

        # If-Modified-Since unchanged -> 304
        r = await client.get("/archive", headers={"If-Modified-Since": last_mod})
        assert r.status == 304
        await r.release()


@pytest.mark.asyncio
async def test_sparse_large_file_ranges(temp_dir):
    """A multi-GB sparse file must serve single ranges without reading it all."""
    path = os.path.join(temp_dir, "huge.pmtiles")
    with open(path, "wb") as f:
        f.write(build_pmtiles([(0, 0, 0, TILE_PAYLOAD)]))
        f.seek(3 * 1024 * 1024 * 1024 - 1)
        f.write(b"\x00")
    async with TestClient(TestServer(_serve_app(path))) as client:
        r = await client.get("/archive", headers={"Range": "bytes=0-126"})
        assert r.status == 206
        body = await r.read()
        assert body[:7] == b"PMTiles"
        assert r.headers["Content-Range"].endswith(f"/{3 * 1024 * 1024 * 1024}")


def test_upload_magic_gate(mock_config, temp_dir):
    """get_metadata-driven validation rejects non-archives with the .pmtiles name."""
    p = os.path.join(temp_dir, "fake.pmtiles")
    with open(p, "wb") as f:
        f.write(b"SQLite format 3\x00" + b"\x00" * 1000)
    mock_config.map_offline_path.get.return_value = p
    mm = MapManager(mock_config, temp_dir)
    assert mm.get_metadata() is None


def _upload_app(temp_dir):
    """Real upload_map_offline route with a fake MeshChat app object."""
    from aiohttp import web as _web

    from meshchatx.src.backend.http.routes.map import register_map_routes

    routes = _web.RouteTableDef()

    class FakeConfig:
        def __init__(self):
            self._path = {"v": None}
            self.map_offline_path = MagicMock()
            self.map_offline_path.get.side_effect = lambda: self._path["v"]
            self.map_offline_path.set.side_effect = lambda v: self._path.__setitem__(
                "v", v
            )
            self.map_offline_enabled = MagicMock()
            self.map_mbtiles_dir = MagicMock()
            self.map_mbtiles_dir.get.return_value = None

    class FakeApp:
        pass

    fake = FakeApp()
    fake.config = FakeConfig()
    fake.map_manager = MapManager(fake.config, temp_dir)
    register_map_routes(routes, fake)
    application = _web.Application()
    application.router.add_routes(routes)
    return application


@pytest.mark.asyncio
async def test_concurrent_upload_same_name(temp_dir):
    """Two same-name uploads must leave one complete file, never interleaved."""
    payload_a = build_pmtiles([(0, 0, 0, TILE_PAYLOAD)])
    payload_b = build_pmtiles([(0, 0, 0, TILE_PAYLOAD), (1, 0, 0, TILE_PAYLOAD)])
    async with TestClient(TestServer(_upload_app(temp_dir))) as client:
        url = "/api/v1/map/offline"

        def post(data):
            form = FormData()
            form.add_field(
                "file",
                data,
                filename="region.pmtiles",
                content_type="application/octet-stream",
            )
            return client.post(url, data=form)

        r1, r2 = await asyncio.gather(post(payload_a), post(payload_b))
        assert r1.status in (200, 400)
        assert r2.status in (200, 400)
    dest = os.path.join(temp_dir, "region.pmtiles")
    assert os.path.exists(dest)
    with open(dest, "rb") as f:
        final = f.read()
    # Atomic rename: dest is one complete upload, never a chunk splice.
    assert final in (payload_a, payload_b)
    # No staging leftovers.
    leftovers = [n for n in os.listdir(temp_dir) if ".upload-" in n]
    assert leftovers == []


@pytest.mark.asyncio
async def test_upload_rejects_garbage_before_commit(temp_dir):
    """Garbage bytes with a .pmtiles name must not replace a valid file."""
    good = build_pmtiles([(0, 0, 0, TILE_PAYLOAD)])
    dest = os.path.join(temp_dir, "region.pmtiles")
    with open(dest, "wb") as f:
        f.write(good)
    async with TestClient(TestServer(_upload_app(temp_dir))) as client:
        form = FormData()
        form.add_field(
            "file",
            b"not a pmtiles file at all",
            filename="region.pmtiles",
            content_type="application/octet-stream",
        )
        r = await client.post("/api/v1/map/offline", data=form)
        assert r.status == 400
    with open(dest, "rb") as f:
        assert f.read() == good


@pytest.mark.asyncio
async def test_delete_while_serving(archive_path):
    """Unlinking mid-read does not corrupt an in-flight range response."""
    async with TestClient(TestServer(_serve_app(archive_path))) as client:
        mm_dir = os.path.dirname(archive_path)
        mm_config = MagicMock()
        mm_config.map_offline_path.get.return_value = archive_path
        mm_config.map_mbtiles_dir.get.return_value = None
        mm = MapManager(mm_config, mm_dir)

        r = await client.get("/archive", headers={"Range": "bytes=0-126"})
        assert r.status == 206
        assert mm.delete_pmtiles(os.path.basename(archive_path))
        body = await r.read()
        assert body[:7] == b"PMTiles"
