# SPDX-License-Identifier: 0BSD

import base64
import json
import os
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.map_data_manager import (
    MAP_ASPECT,
    MapDataError,
    MapDataManager,
    coerce_map_request_body,
    parse_map_data_app_data,
)
from meshchatx.src.backend.map_geo_validator import GeoValidationError
from meshchatx.src.backend.map_overlay_manager import MapOverlayManager

HASH = "ab" * 16

GEOJSON = json.dumps(
    {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Camp"},
                "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
            },
        ],
    },
).encode()

REMOTE_KML = b"""<?xml version="1.0"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
  <Placemark><name>P</name>
    <Style><IconStyle><Icon><href>https://evil.example/i.png</href></Icon></IconStyle></Style>
    <Point><coordinates>1,2,0</coordinates></Point>
  </Placemark>
</Document></kml>"""


class FakeValue:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class FakeConfig:
    def __init__(self):
        self.map_overlay_max_bytes = FakeValue(8 * 1024 * 1024)
        self.map_overlay_max_features = FakeValue(50_000)
        self.map_overlay_max_kmz_uncompressed_bytes = FakeValue(16 * 1024 * 1024)
        self.map_overlay_max_sources = FakeValue(64)
        self.map_overlay_max_concurrent_jobs = FakeValue(2)
        self.map_overlay_path_timeout_seconds = FakeValue(30)
        self.map_overlay_transfer_timeout_seconds = FakeValue(120)
        self.map_overlay_job_timeout_seconds = FakeValue(300)
        self.map_overlay_max_retries = FakeValue(1)
        self.map_overlay_retry_delay_seconds = FakeValue(1)
        self.map_data_max_bytes = FakeValue(512 * 1024)
        self.map_data_announce_enabled = FakeValue(False)
        self.map_data_announce_interval = FakeValue(900)
        self.map_data_display_name = FakeValue("Camp maps")
        self.announce_store_map_data = FakeValue(True)
        self.announce_max_stored_map_data = FakeValue(1000)
        self.announce_fetch_limit_map_data = FakeValue(500)


class FakeIdentity:
    def __init__(self):
        self.hash = bytes.fromhex(HASH)


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "db.sqlite"))
    database.initialize()
    return database


@pytest.fixture
def manager(db, tmp_path):
    return MapDataManager(
        FakeConfig(),
        db,
        str(tmp_path / "storage"),
        FakeIdentity(),
    )


def test_parse_map_data_app_data_json():
    parsed = parse_map_data_app_data(b'{"v":1,"n":"Camp maps","c":3}')
    assert parsed["n"] == "Camp maps"
    assert parsed["c"] == 3


def test_parse_map_data_app_data_truncates_name():
    parsed = parse_map_data_app_data(
        json.dumps({"v": 1, "n": "x" * 80, "c": 1}).encode(),
    )
    assert len(parsed["n"]) == 32


def test_publish_stores_sanitized_geojson(manager):
    result = manager.publish_bytes(GEOJSON, name="Camp")
    row = result["map"]
    assert row["name"] == "Camp"
    assert row["format"] == "geojson"
    assert row["feature_count"] == 1
    listed = manager.list_published()
    assert len(listed) == 1
    assert listed[0]["map_id"] == row["map_id"]


def test_publish_strips_remote_kml_href(manager):
    result = manager.publish_bytes(REMOTE_KML, name="layer", hinted_format="kml")
    assert "remote_href" in result["stripped"]
    abs_path = manager.data_root() + "/" + result["map"]["path"]
    with open(abs_path, "rb") as fh:
        body = fh.read()
    assert b"https://evil.example" not in body


def test_publish_rejects_oversized(manager):
    manager.config.map_data_max_bytes.set(64 * 1024)
    with pytest.raises(MapDataError) as exc:
        manager.publish_bytes(b"{" + b"x" * (65 * 1024), name="big")
    assert exc.value.code == "file_too_large"


def test_publish_rejects_empty(manager):
    with pytest.raises(GeoValidationError):
        manager.publish_bytes(b"", name="empty")


def test_unpublish_removes_file(manager):
    result = manager.publish_bytes(GEOJSON, name="Camp")
    map_id = result["map"]["map_id"]
    assert manager.unpublish(map_id) is True
    assert manager.list_published() == []
    assert manager.unpublish(map_id) is False


def test_catalog_payload(manager):
    manager.publish_bytes(GEOJSON, name="Camp")
    payload = manager._catalog_payload()
    assert len(payload["maps"]) == 1
    assert payload["maps"][0]["name"] == "Camp"
    assert payload["maps"][0]["format"] == "geojson"


def test_stop_deregisters_destination(manager):
    dest = MagicMock()
    manager._destination = dest
    manager._running = True
    manager._registered_map_paths = {"/map/aaaaaaaaaaaaaaaa"}
    with patch.object(RNS.Transport, "deregister_destination") as dereg:
        manager.stop()
    dest.deregister_request_handler.assert_any_call("/catalog")
    dest.deregister_request_handler.assert_any_call("/map/aaaaaaaaaaaaaaaa")
    dereg.assert_called_once_with(dest)
    assert manager._destination is None
    assert manager._running is False


@pytest.mark.asyncio
async def test_ingest_overlay_kind_map_data(manager, db, tmp_path):
    overlay = MapOverlayManager(
        manager.config,
        db,
        str(tmp_path / "overlay"),
        reticulum_config_dir=None,
    )
    manager._overlay_manager_getter = lambda: overlay
    published = manager.publish_bytes(GEOJSON, name="Camp")
    map_id = published["map"]["map_id"]

    async def fake_fetch_map_bytes(_dest, _map_id, **_kwargs):
        return GEOJSON

    async def fake_catalog(_dest):
        return {
            "maps": [
                {
                    "id": map_id,
                    "name": "Camp",
                    "format": "geojson",
                },
            ],
        }

    manager.fetch_map_bytes = fake_fetch_map_bytes
    manager.fetch_catalog = fake_catalog
    result = await manager.add_as_overlay(HASH, map_id)
    overlay_row = result["overlay"]
    assert overlay_row["kind"] == "map_data"
    assert overlay_row["status"] == "ready"
    assert overlay_row["format"] == "geojson"


def test_announce_app_data_is_slim(manager):
    dest = MagicMock()
    dest.hash.hex.return_value = "cd" * 16
    manager._destination = dest
    manager._running = True
    manager.publish_bytes(GEOJSON, name="Camp")
    manager.config.map_data_announce_enabled.set(True)
    status = manager.announce()
    dest.announce.assert_called_once()
    app_data = dest.announce.call_args.kwargs["app_data"]
    parsed = json.loads(app_data.decode("utf-8"))
    assert parsed["v"] == 1
    assert parsed["n"] == "Camp maps"
    assert parsed["c"] == 1
    assert len(app_data) < 128
    assert status["aspect"] == MAP_ASPECT


def test_list_heard_parses_slim_app_data(manager, db):
    app = json.dumps({"v": 1, "n": "Camp maps", "c": 3}, separators=(",", ":")).encode()
    db.announces.upsert_announce(
        {
            "destination_hash": HASH,
            "aspect": MAP_ASPECT,
            "identity_hash": HASH,
            "identity_public_key": "cHVi",
            "app_data": base64.b64encode(app).decode(),
            "rssi": None,
            "snr": None,
            "quality": None,
        },
    )
    heard = manager.list_heard()
    assert len(heard) == 1
    assert heard[0]["map_name"] == "Camp maps"
    assert heard[0]["map_count"] == 3


def _patch_destination(dest):
    real = RNS.Destination
    patcher = patch("meshchatx.src.backend.map_data_manager.RNS.Destination")
    dest_cls = patcher.start()
    dest_cls.IN = real.IN
    dest_cls.SINGLE = real.SINGLE
    dest_cls.ALLOW_ALL = real.ALLOW_ALL
    dest_cls.app_and_aspects_from_name.return_value = ("map-data-v1", ())
    dest_cls.return_value = dest
    return patcher, dest_cls


def test_start_without_published_maps_does_not_create_destination(manager):
    from tests.backend.eect.harness import eect_scenario

    with eect_scenario("map.data.announce_opt_in_until_publish"):
        with patch(
            "meshchatx.src.backend.map_data_manager.RNS.Destination",
            side_effect=AssertionError("destination must stay opt-in"),
        ):
            status = manager.start()
        assert manager._destination is None
        assert status["running"] is False
        assert status["published_count"] == 0
        assert status["announce_enabled"] is False


def test_announce_refuses_when_nothing_published(manager):
    manager.start()
    with pytest.raises(MapDataError) as exc:
        manager.announce()
    assert exc.value.code == "nothing_published"
    assert manager._destination is None


def test_publish_after_start_creates_destination_without_announce(manager):
    dest = MagicMock()
    dest.hash.hex.return_value = "cd" * 16
    patcher, dest_cls = _patch_destination(dest)
    try:
        manager.start()
        dest_cls.assert_not_called()
        manager.publish_bytes(GEOJSON, name="Camp")
        dest_cls.assert_called_once()
        dest.announce.assert_not_called()
        dest.register_request_handler.assert_called()
    finally:
        patcher.stop()


def test_publish_announces_when_enabled(manager):
    dest = MagicMock()
    dest.hash.hex.return_value = "cd" * 16
    manager.config.map_data_announce_enabled.set(True)
    patcher, _dest_cls = _patch_destination(dest)
    try:
        manager.start()
        dest.announce.assert_not_called()
        manager.publish_bytes(GEOJSON, name="Camp")
        dest.announce.assert_called()
    finally:
        patcher.stop()


def test_unpublish_last_map_tears_down_destination(manager):
    dest = MagicMock()
    dest.hash.hex.return_value = "cd" * 16
    patcher, _dest_cls = _patch_destination(dest)
    try:
        manager.start()
        result = manager.publish_bytes(GEOJSON, name="Camp")
        assert manager._destination is dest
        with patch.object(RNS.Transport, "deregister_destination") as dereg:
            manager.unpublish(result["map"]["map_id"])
        dereg.assert_called_once_with(dest)
        assert manager._destination is None
    finally:
        patcher.stop()


def test_catalog_responder_returns_json_bytes(manager):
    from tests.backend.eect.harness import eect_scenario

    with eect_scenario("map.data.catalog_bytes_over_link"):
        manager.publish_bytes(GEOJSON, name="Camp")
        body = manager._catalog_responder("/catalog", None, None, None, None, None)
        assert isinstance(body, (bytes, bytearray))
        parsed = json.loads(body)
        assert parsed["maps"][0]["name"] == "Camp"


def test_coerce_request_body_unwraps_list_payload():
    raw = b'{"maps":[]}'
    assert coerce_map_request_body(raw) == raw
    assert coerce_map_request_body([raw, {"name": b"catalog.json"}]) == raw
    with pytest.raises(MapDataError) as exc:
        coerce_map_request_body(None)
    assert exc.value.code == "empty_response"


@pytest.mark.asyncio
async def test_fetch_catalog_local_shortcut(manager):
    published = manager.publish_bytes(GEOJSON, name="Camp")
    dest = MagicMock()
    dest.hash = bytes.fromhex("cd" * 16)
    manager._destination = dest
    manager._running = True
    result = await manager.fetch_catalog("cd" * 16)
    assert result["maps"][0]["id"] == published["map"]["map_id"]
    assert result["maps"][0]["name"] == "Camp"


@pytest.mark.asyncio
async def test_link_request_accepts_list_wrapped_bytes(manager):
    body = json.dumps({"maps": [{"id": "a" * 16, "name": "Camp"}]}).encode()

    class LinkManager:
        async def open_link(self, *_args, **_kwargs):
            return object(), False, None

        def request(
            self,
            _dest,
            _aspect,
            _path,
            _data,
            on_response,
            _on_failed,
            _on_prog,
            timeout=None,
        ):
            class Receipt:
                response = [body, {"name": b"catalog.json"}]

            on_response(Receipt())

    manager._link_manager_getter = lambda: LinkManager()
    result = await manager.fetch_catalog("cd" * 16)
    assert result["maps"][0]["name"] == "Camp"


def test_coerce_request_body_caps_unwrap_depth():
    nested = [[[[b'{"maps":[]}']]]]
    with pytest.raises(MapDataError) as exc:
        coerce_map_request_body(nested)
    assert exc.value.code == "invalid_response"


def test_publish_caps_count(manager, monkeypatch):
    monkeypatch.setattr(
        "meshchatx.src.backend.map_data_manager.MAX_PUBLISHED_MAPS",
        1,
    )
    manager.publish_bytes(GEOJSON, name="one")
    with pytest.raises(MapDataError) as exc:
        manager.publish_bytes(GEOJSON, name="two")
    assert exc.value.code == "max_published_exceeded"


@pytest.mark.skipif(os.name == "nt", reason="symlink follow is a POSIX case")
def test_published_symlink_is_not_served_or_deleted(manager, tmp_path):
    result = manager.publish_bytes(GEOJSON, name="Camp")
    map_id = result["map"]["map_id"]
    rel = result["map"]["path"]
    abs_path = os.path.join(manager.data_root(), rel)
    bait = tmp_path / "secret.bin"
    bait.write_bytes(b"keep-me")
    os.remove(abs_path)
    os.symlink(bait, abs_path)
    assert manager._resolve_published_file(map_id, rel) is None
    served = manager._make_map_responder(map_id)(
        "/map/" + map_id,
        None,
        None,
        None,
        None,
        None,
    )
    assert served is None
    assert manager.unpublish(map_id) is True
    assert bait.read_bytes() == b"keep-me"


def test_parse_catalog_drops_unknown_format_and_bad_hash(manager):
    body = json.dumps(
        {
            "maps": [
                {
                    "id": "a" * 16,
                    "name": "Camp",
                    "format": "exe",
                    "sha256": "not-a-hash",
                    "size": -3,
                },
                {
                    "id": "b" * 16,
                    "name": "Trail",
                    "format": "geojson",
                    "sha256": "ab" * 32,
                    "size": 12,
                },
            ],
        },
    ).encode()
    parsed = manager._parse_catalog_body(body, "cd" * 16)
    assert [m["id"] for m in parsed["maps"]] == ["b" * 16]
    assert parsed["maps"][0]["sha256"] == "ab" * 32


def test_parse_catalog_rejects_oversized_body(manager):
    from meshchatx.src.backend.map_data_manager import MAX_CATALOG_BYTES

    with pytest.raises(MapDataError) as exc:
        manager._parse_catalog_body(b"{" + b"x" * (MAX_CATALOG_BYTES + 1), "cd" * 16)
    assert exc.value.code == "invalid_catalog"


@pytest.mark.asyncio
async def test_fetch_map_bytes_strips_remote_kml(manager):
    async def fake_link(_dest, _path):
        return REMOTE_KML

    manager._link_request = fake_link
    body = await manager.fetch_map_bytes("cd" * 16, "a" * 16, hinted_format="kml")
    assert b"https://evil.example" not in body


@pytest.mark.asyncio
async def test_fetch_map_bytes_sha256_mismatch(manager):
    async def fake_link(_dest, _path):
        return GEOJSON

    manager._link_request = fake_link
    with pytest.raises(MapDataError) as exc:
        await manager.fetch_map_bytes(
            "cd" * 16,
            "a" * 16,
            expected_sha256="0" * 64,
        )
    assert exc.value.code == "sha256_mismatch"


@pytest.mark.asyncio
async def test_add_as_overlay_requires_catalog_entry(manager, db, tmp_path):
    overlay = MapOverlayManager(
        manager.config,
        db,
        str(tmp_path / "overlay"),
        reticulum_config_dir=None,
    )
    manager._overlay_manager_getter = lambda: overlay

    async def fake_catalog(_dest):
        return {"maps": []}

    manager.fetch_catalog = fake_catalog
    with pytest.raises(MapDataError) as exc:
        await manager.add_as_overlay(HASH, "a" * 16)
    assert exc.value.code == "not_found"
