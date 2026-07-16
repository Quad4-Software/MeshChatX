# SPDX-License-Identifier: 0BSD

"""Regression tests for I2P interface safety and recovery."""

from __future__ import annotations

import contextlib
import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS
from RNS.vendor.configobj import ConfigObj

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend import i2p_support


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


async def find_route_handler(app_instance, path, method):
    for route in app_instance.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


@contextlib.asynccontextmanager
async def make_app(temp_dir, config):
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

        yield app_instance


def make_request(payload):
    request = MagicMock()

    async def _json():
        return payload

    request.json = _json
    return request


def test_reorder_interfaces_i2p_last():
    interfaces = {
        "A": {"type": "AutoInterface", "interface_enabled": "true"},
        "I2P": {"type": "I2PInterface", "interface_enabled": "true"},
        "B": {"type": "TCPClientInterface", "interface_enabled": "true"},
    }
    assert i2p_support.reorder_interfaces_i2p_last(interfaces) is True
    assert list(interfaces.keys()) == ["A", "B", "I2P"]
    assert i2p_support.i2p_is_last(interfaces) is True


def test_enforce_single_enabled_i2p():
    interfaces = {
        "I2P1": {"type": "I2PInterface", "interface_enabled": "true"},
        "I2P2": {"type": "I2PInterface", "interface_enabled": "true"},
    }
    assert i2p_support.enforce_single_enabled_i2p(interfaces) is True
    assert i2p_support.is_interface_enabled(interfaces["I2P1"]) is True
    assert i2p_support.is_interface_enabled(interfaces["I2P2"]) is False


def test_disable_i2p_when_transport_off():
    interfaces = {
        "I2P": {"type": "I2PInterface", "interface_enabled": "true"},
    }
    assert (
        i2p_support.disable_i2p_when_transport_off(
            interfaces,
            {"enable_transport": "False"},
        )
        is True
    )
    assert i2p_support.is_interface_enabled(interfaces["I2P"]) is False


def test_guard_i2p_interfaces_in_config(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = True

[interfaces]
[[A]]
type = AutoInterface
interface_enabled = true
[[I2P]]
type = I2PInterface
interface_enabled = true
peers = aaa.b32.i2p
[[B]]
type = TCPClientInterface
interface_enabled = true
[[I2P2]]
type = I2PInterface
interface_enabled = true
peers = bbb.b32.i2p
""",
        encoding="utf-8",
    )
    assert i2p_support.guard_i2p_interfaces_in_config(str(config_path)) is True
    cfg = ConfigObj(str(config_path))
    names = list(cfg["interfaces"].keys())
    assert names[-1] in ("I2P", "I2P2")
    assert names[-2] in ("I2P", "I2P2")
    enabled = [
        n
        for n, iface in cfg["interfaces"].items()
        if iface.get("type") == "I2PInterface"
        and i2p_support.is_interface_enabled(iface)
    ]
    assert len(enabled) == 1


def test_guard_disables_i2p_without_transport(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = False

[interfaces]
[[I2P]]
type = I2PInterface
interface_enabled = true
peers = aaa.b32.i2p
""",
        encoding="utf-8",
    )
    assert i2p_support.guard_i2p_interfaces_in_config(str(config_path)) is True
    cfg = ConfigObj(str(config_path))
    assert i2p_support.is_interface_enabled(cfg["interfaces"]["I2P"]) is False


def test_validate_raw_rejects_adding_i2p():
    previous = {
        "A": {"type": "AutoInterface", "interface_enabled": "true"},
    }
    content = """[reticulum]
enable_transport = True
[interfaces]
[[A]]
type = AutoInterface
interface_enabled = true
[[I2P]]
type = I2PInterface
interface_enabled = true
peers = aaa.b32.i2p
"""
    err = i2p_support.validate_raw_config_i2p_policy(
        content,
        previous_interfaces=previous,
    )
    assert err == i2p_support.MSG_RAW_FORBIDDEN


def test_validate_raw_allows_deleting_i2p():
    previous = {
        "A": {"type": "AutoInterface", "interface_enabled": "true"},
        "I2P": {
            "type": "I2PInterface",
            "interface_enabled": "true",
            "peers": ["aaa.b32.i2p"],
        },
    }
    content = """[reticulum]
enable_transport = True
[interfaces]
[[A]]
type = AutoInterface
interface_enabled = true
"""
    assert (
        i2p_support.validate_raw_config_i2p_policy(
            content,
            previous_interfaces=previous,
        )
        is None
    )


def test_disable_all_i2p_in_config(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = True
[interfaces]
[[I2P]]
type = I2PInterface
interface_enabled = true
peers = aaa.b32.i2p
""",
        encoding="utf-8",
    )
    assert i2p_support.disable_all_i2p_in_config(str(config_path)) is True
    cfg = ConfigObj(str(config_path))
    assert i2p_support.is_interface_enabled(cfg["interfaces"]["I2P"]) is False


@pytest.mark.asyncio
async def test_add_i2p_requires_transport(temp_dir):
    config = ConfigDict(
        {
            "reticulum": {"enable_transport": "False"},
            "interfaces": {},
        },
    )
    async with make_app(temp_dir, config) as app:
        handler = await find_route_handler(
            app,
            "/api/v1/reticulum/interfaces/add",
            "POST",
        )
        response = await handler(
            make_request(
                {
                    "name": "I2POut",
                    "type": "I2PInterface",
                    "peers": ["abcdef.b32.i2p"],
                },
            ),
        )
        body = json.loads(response.body)
        assert response.status == 422
        assert "Transport" in body["message"]


@pytest.mark.asyncio
async def test_add_second_i2p_rejected(temp_dir):
    config = ConfigDict(
        {
            "reticulum": {"enable_transport": "True"},
            "interfaces": {
                "ExistingI2P": {
                    "type": "I2PInterface",
                    "interface_enabled": "true",
                    "peers": ["aaa.b32.i2p"],
                },
            },
        },
    )
    async with make_app(temp_dir, config) as app:
        handler = await find_route_handler(
            app,
            "/api/v1/reticulum/interfaces/add",
            "POST",
        )
        response = await handler(
            make_request(
                {
                    "name": "I2P2",
                    "type": "I2PInterface",
                    "peers": ["bbb.b32.i2p"],
                },
            ),
        )
        body = json.loads(response.body)
        assert response.status == 422
        assert "Only one I2P" in body["message"]


@pytest.mark.asyncio
async def test_add_i2p_is_placed_last(temp_dir):
    config = ConfigDict(
        {
            "reticulum": {"enable_transport": "True"},
            "interfaces": {
                "A": {"type": "AutoInterface", "interface_enabled": "true"},
            },
        },
    )
    async with make_app(temp_dir, config) as app:
        handler = await find_route_handler(
            app,
            "/api/v1/reticulum/interfaces/add",
            "POST",
        )
        response = await handler(
            make_request(
                {
                    "name": "I2POut",
                    "type": "I2PInterface",
                    "peers": ["abcdef.b32.i2p"],
                },
            ),
        )
        body = json.loads(response.body)
        assert response.status == 200, body
        assert list(config["interfaces"].keys())[-1] == "I2POut"


@pytest.mark.asyncio
async def test_import_rejects_i2p(temp_dir):
    config = ConfigDict(
        {
            "reticulum": {"enable_transport": "True"},
            "interfaces": {},
        },
    )
    async with make_app(temp_dir, config) as app:
        handler = await find_route_handler(
            app,
            "/api/v1/reticulum/interfaces/import",
            "POST",
        )
        response = await handler(
            make_request(
                {
                    "config": """[[I2POut]]
type = I2PInterface
peers = aaa.b32.i2p
""",
                    "selected_interface_names": ["I2POut"],
                },
            ),
        )
        body = json.loads(response.body)
        assert response.status == 422
        assert "cannot be imported" in body["message"]


@pytest.mark.asyncio
async def test_import_preview_hides_i2p(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})
    async with make_app(temp_dir, config) as app:
        handler = await find_route_handler(
            app,
            "/api/v1/reticulum/interfaces/import-preview",
            "POST",
        )
        response = await handler(
            make_request(
                {
                    "config": """[[TCP]]
type = TCPClientInterface
target_host = 1.2.3.4
target_port = 4242
[[I2POut]]
type = I2PInterface
peers = aaa.b32.i2p
""",
                },
            ),
        )
        body = json.loads(response.body)
        assert response.status == 200, body
        names = [iface["name"] for iface in body["interfaces"]]
        assert "TCP" in names
        assert "I2POut" not in names


@pytest.mark.asyncio
async def test_raw_put_rejects_new_i2p(temp_dir):
    config_path = f"{temp_dir}/config"
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write(
            """[reticulum]
enable_transport = True
[interfaces]
[[A]]
type = AutoInterface
interface_enabled = true
""",
        )
    config = ConfigDict(
        {
            "reticulum": {"enable_transport": "True"},
            "interfaces": {
                "A": {"type": "AutoInterface", "interface_enabled": "true"},
            },
        },
    )
    async with make_app(temp_dir, config) as app:
        handler = await find_route_handler(
            app,
            "/api/v1/reticulum/config/raw",
            "PUT",
        )
        response = await handler(
            make_request(
                {
                    "content": """[reticulum]
enable_transport = True
[interfaces]
[[A]]
type = AutoInterface
interface_enabled = true
[[I2P]]
type = I2PInterface
interface_enabled = true
peers = aaa.b32.i2p
""",
                },
            ),
        )
        body = json.loads(response.body)
        assert response.status == 422
        assert "raw config" in body["error"].lower() or "I2P" in body["error"]


def test_create_reticulum_retries_after_disabling_i2p(tmp_path, monkeypatch):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = True
[interfaces]
[[I2P]]
type = I2PInterface
interface_enabled = true
peers = aaa.b32.i2p
""",
        encoding="utf-8",
    )
    calls = {"n": 0}

    class FakeReticulum:
        def __init__(self, *_args, **_kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("I2P brick")

    monkeypatch.setattr("meshchatx.meshchat.RNS.Reticulum", FakeReticulum)
    from meshchatx import meshchat as meshchat_mod

    instance = meshchat_mod._create_reticulum_instance(str(tmp_path))
    assert isinstance(instance, FakeReticulum)
    assert calls["n"] == 2
    cfg = ConfigObj(str(config_path))
    assert i2p_support.is_interface_enabled(cfg["interfaces"]["I2P"]) is False
