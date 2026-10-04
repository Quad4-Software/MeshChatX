# SPDX-License-Identifier: 0BSD

"""Tests for discovered-interface tuning.

Covers aging thresholds, the max-return cap, and the export/import endpoints
for the discovery storage dir.
"""

import base64
import configparser
import io
import json
import os
import shutil
import tempfile
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS
from RNS.Discovery import InterfaceDiscovery
from RNS.vendor import umsgpack

import meshchatx.meshchat as meshchat_mod
from meshchatx.meshchat import ReticulumMeshChat


class ConfigDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.write_called = False

    def write(self):
        self.write_called = True
        return True


@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    try:
        yield path
    finally:
        shutil.rmtree(path)


def build_identity():
    identity = MagicMock(spec=RNS.Identity)
    identity.hash = b"test_hash_32_bytes_long_01234567"
    identity.hexhash = identity.hash.hex()
    identity.get_private_key.return_value = b"test_private_key"
    return identity


def build_app(temp_dir, reticulum_section=None):
    config = ConfigDict(
        {
            "reticulum": reticulum_section or {},
            "interfaces": {},
        },
    )
    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
    ):
        mock_reticulum = mock_rns.return_value
        mock_reticulum.config = config
        mock_reticulum.configpath = "/tmp/mock_config"
        mock_reticulum.is_connected_to_shared_instance = False
        mock_reticulum.transport_enabled.return_value = True

        app_instance = ReticulumMeshChat(
            identity=build_identity(),
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app_instance.reload_reticulum = AsyncMock(return_value=True)
        return app_instance, config


async def find_route_handler(app_instance, path, method):
    for route in app_instance.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


class JsonRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def _write_rns_config(config_dir, section):
    cfg = configparser.ConfigParser()
    cfg["reticulum"] = section
    with open(os.path.join(config_dir, "config"), "w", encoding="utf-8") as f:
        cfg.write(f)


def test_apply_interface_discovery_thresholds_from_config(temp_dir):
    saved = (
        InterfaceDiscovery.THRESHOLD_UNKNOWN,
        InterfaceDiscovery.THRESHOLD_STALE,
        InterfaceDiscovery.THRESHOLD_REMOVE,
    )
    try:
        _write_rns_config(
            temp_dir,
            {
                "interface_discovery_unknown_after_days": "2",
                "interface_discovery_stale_after_days": "10",
                "interface_discovery_remove_after_days": "30",
            },
        )
        meshchat_mod._apply_interface_discovery_thresholds(temp_dir)

        assert InterfaceDiscovery.THRESHOLD_UNKNOWN == pytest.approx(2 * 86400)
        assert InterfaceDiscovery.THRESHOLD_STALE == pytest.approx(10 * 86400)
        assert InterfaceDiscovery.THRESHOLD_REMOVE == pytest.approx(30 * 86400)
    finally:
        (
            InterfaceDiscovery.THRESHOLD_UNKNOWN,
            InterfaceDiscovery.THRESHOLD_STALE,
            InterfaceDiscovery.THRESHOLD_REMOVE,
        ) = saved


def test_apply_interface_discovery_thresholds_defaults_and_invalid(temp_dir):
    saved = (
        InterfaceDiscovery.THRESHOLD_UNKNOWN,
        InterfaceDiscovery.THRESHOLD_STALE,
        InterfaceDiscovery.THRESHOLD_REMOVE,
    )
    try:
        _write_rns_config(
            temp_dir,
            {
                "interface_discovery_unknown_after_days": "notanumber",
                "interface_discovery_stale_after_days": "-5",
                # remove_after intentionally unset falls back to RNS default
            },
        )
        meshchat_mod._apply_interface_discovery_thresholds(temp_dir)

        assert InterfaceDiscovery.THRESHOLD_UNKNOWN == 24 * 60 * 60
        assert InterfaceDiscovery.THRESHOLD_STALE == 3 * 24 * 60 * 60
        assert InterfaceDiscovery.THRESHOLD_REMOVE == 7 * 24 * 60 * 60
    finally:
        (
            InterfaceDiscovery.THRESHOLD_UNKNOWN,
            InterfaceDiscovery.THRESHOLD_STALE,
            InterfaceDiscovery.THRESHOLD_REMOVE,
        ) = saved


@pytest.mark.asyncio
async def test_discovery_patch_max_return_and_thresholds(temp_dir):
    app_instance, config = build_app(temp_dir)
    patch_handler = await find_route_handler(
        app_instance,
        "/api/v1/reticulum/discovery",
        "PATCH",
    )
    get_handler = await find_route_handler(
        app_instance,
        "/api/v1/reticulum/discovery",
        "GET",
    )
    assert patch_handler and get_handler

    payload = {
        "discovered_interfaces_max_return": 2000,
        "interface_discovery_unknown_after_days": 2,
        "interface_discovery_stale_after_days": 10,
        "interface_discovery_remove_after_days": 30,
    }
    resp = await patch_handler(JsonRequest(payload))
    data = json.loads(resp.body)
    assert data["discovery"]["discovered_interfaces_max_return"] == 2000
    assert (
        app_instance.current_context.config.discovered_interfaces_max_return.get()
        == 2000
    )
    # app-only cap must not leak into the reticulum config file
    assert "discovered_interfaces_max_return" not in config["reticulum"]

    assert config["reticulum"]["interface_discovery_unknown_after_days"] == 2
    assert config["reticulum"]["interface_discovery_stale_after_days"] == 10
    assert config["reticulum"]["interface_discovery_remove_after_days"] == 30

    get_resp = await get_handler(MagicMock())
    get_data = json.loads(get_resp.body)
    assert get_data["discovery"]["discovered_interfaces_max_return"] == 2000
    assert get_data["discovery"]["interface_discovery_remove_after_days"] == 30


@pytest.mark.asyncio
async def test_discovery_patch_max_return_validation(temp_dir):
    app_instance, _config = build_app(temp_dir)
    patch_handler = await find_route_handler(
        app_instance,
        "/api/v1/reticulum/discovery",
        "PATCH",
    )

    for bad in (0, -1, 50001, "lots"):
        resp = await patch_handler(
            JsonRequest({"discovered_interfaces_max_return": bad}),
        )
        assert resp.status == 422, bad

    for bad in ("abc", 0, -2, 36501):
        resp = await patch_handler(
            JsonRequest({"interface_discovery_remove_after_days": bad}),
        )
        assert resp.status == 422, bad


def _make_discovery_file(directory, name, info):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, name), "wb") as f:
        f.write(umsgpack.packb(info))


def _valid_discovery_info(**kwargs):
    info = {
        "name": "peer-iface",
        "type": "TCPClientInterface",
        "reachable_on": "10.0.0.9",
        "port": 4242,
        "network_id": "aa" * 16,
        "transport_id": "bb" * 16,
        "last_heard": 1700000000,
    }
    info.update(kwargs)
    return info


@pytest.mark.asyncio
async def test_discovered_interfaces_export_and_import(temp_dir):
    app_instance, _ = build_app(temp_dir)
    export_handler = await find_route_handler(
        app_instance,
        "/api/v1/reticulum/discovered-interfaces/export",
        "GET",
    )
    import_handler = await find_route_handler(
        app_instance,
        "/api/v1/reticulum/discovered-interfaces/import",
        "POST",
    )
    assert export_handler and import_handler

    discovery_dir = os.path.join(temp_dir, "discovery", "interfaces")
    _make_discovery_file(discovery_dir, "aa" * 16, _valid_discovery_info())
    _make_discovery_file(discovery_dir, "bb" * 16, _valid_discovery_info(name="peer-2"))

    with patch.object(RNS.Reticulum, "storagepath", temp_dir):
        export_resp = await export_handler(MagicMock())
        assert export_resp.status == 200
        with zipfile.ZipFile(io.BytesIO(export_resp.body)) as zf:
            assert sorted(zf.namelist()) == ["aa" * 16, "bb" * 16]

    # import into a fresh dir: one valid, one bad name, one bad payload
    import_dir = os.path.join(temp_dir, "imported", "discovery", "interfaces")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("cc" * 16, umsgpack.packb(_valid_discovery_info(name="imported-peer")))
        zf.writestr("../escape", b"bad")
        zf.writestr("dd" * 16, b"not-msgpack")
        zf.writestr("ee" * 16, umsgpack.packb({"no_last_heard": True}))

    storage_root = os.path.join(temp_dir, "imported")
    with patch.object(RNS.Reticulum, "storagepath", storage_root):
        resp = await import_handler(
            JsonRequest({"data": base64.b64encode(buf.getvalue()).decode()}),
        )
        result = json.loads(resp.body)
        assert resp.status == 200
        assert result == {"imported": 1, "skipped": 3}
        assert os.path.isfile(os.path.join(import_dir, "cc" * 16))
        with open(os.path.join(import_dir, "cc" * 16), "rb") as f:
            info = umsgpack.unpackb(f.read())
        assert info["name"] == "imported-peer"


@pytest.mark.asyncio
async def test_discovered_interfaces_import_rejects_bad_payloads(temp_dir):
    app_instance, _ = build_app(temp_dir)
    import_handler = await find_route_handler(
        app_instance,
        "/api/v1/reticulum/discovered-interfaces/import",
        "POST",
    )

    storage_root = os.path.join(temp_dir, "imported")
    with patch.object(RNS.Reticulum, "storagepath", storage_root):
        resp = await import_handler(JsonRequest({}))
        assert resp.status == 400

        resp = await import_handler(JsonRequest({"data": "%%%not-base64%%%"}))
        assert resp.status == 400

        resp = await import_handler(
            JsonRequest({"data": base64.b64encode(b"not a zip").decode()}),
        )
        assert resp.status == 422
