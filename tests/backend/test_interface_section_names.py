# SPDX-License-Identifier: 0BSD

"""ConfigObj-safe Reticulum interface section names."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import RNS
from RNS.vendor.configobj import ConfigObj

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.community_interfaces import CommunityInterfacesManager
from meshchatx.src.backend.interface_editor import InterfaceEditor


def test_sanitize_interface_section_name_strips_brackets():
    assert (
        InterfaceEditor.sanitize_interface_section_name("MSK SZAO [HaLow Bridge]")
        == "MSK SZAO (HaLow Bridge)"
    )
    assert InterfaceEditor.sanitize_interface_section_name("  foo[bar]  ") == "foo(bar)"
    assert InterfaceEditor.sanitize_interface_section_name("") == ""
    assert InterfaceEditor.sanitize_interface_section_name(None) == ""


def test_configobj_write_succeeds_but_reload_fails_for_brackets():
    """RNS ConfigObj writes bracket section names, then NestingError on reload."""
    path = Path(tempfile.mktemp(suffix=".cfg"))
    try:
        cfg = ConfigObj(str(path))
        cfg["interfaces"] = {}
        cfg["interfaces"]["MSK SZAO [HaLow Bridge]"] = {
            "type": "TCPClientInterface",
            "target_host": "example.com",
            "target_port": "4242",
        }
        cfg.write()
        with pytest.raises(Exception):
            ConfigObj(str(path))
    finally:
        path.unlink(missing_ok=True)


def test_configobj_accepts_sanitized_section_names():
    path = Path(tempfile.mktemp(suffix=".cfg"))
    try:
        name = InterfaceEditor.sanitize_interface_section_name(
            "MSK SZAO [HaLow Bridge]"
        )
        cfg = ConfigObj(str(path))
        cfg["interfaces"] = {}
        cfg["interfaces"][name] = {
            "type": "TCPClientInterface",
            "target_host": "example.com",
            "target_port": "4242",
        }
        cfg.write()
        reloaded = ConfigObj(str(path))
        assert name in reloaded["interfaces"]
    finally:
        path.unlink(missing_ok=True)


def test_community_manager_normalizes_bracket_names(tmp_path):
    doc = {
        "interfaces": [
            {
                "name": "MSK SZAO [HaLow Bridge]",
                "type": "TCPClientInterface",
                "target_host": "dreadgurizta.ru",
                "target_port": 4242,
            }
        ]
    }
    path = tmp_path / "community_interfaces.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    manager = CommunityInterfacesManager(public_override_path=str(path))
    assert manager.interfaces[0]["name"] == "MSK SZAO (HaLow Bridge)"


class _ConfigDict(dict):
    def __init__(self, *args, fail_write=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_write = fail_write
        self.write_called = False

    def write(self):
        self.write_called = True
        if self.fail_write:
            raise RuntimeError("NestingError: Cannot compute the section depth")
        return True


async def _find_add_handler(app_instance):
    for route in app_instance.get_routes():
        if route.path == "/api/v1/reticulum/interfaces/add" and route.method == "POST":
            return route.handler
    return None


@pytest.mark.asyncio
async def test_add_interface_sanitizes_brackets_and_writes(tmp_path):
    config = _ConfigDict({"reticulum": {}, "interfaces": {}})
    identity = MagicMock(spec=RNS.Identity)
    identity.hash = b"test_hash_32_bytes_long_01234567"
    identity.hexhash = identity.hash.hex()
    identity.get_private_key.return_value = b"test_private_key"

    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
    ):
        mock_reticulum = mock_rns.return_value
        mock_reticulum.config = config
        mock_reticulum.configpath = str(tmp_path / "config")
        mock_reticulum.is_connected_to_shared_instance = False
        mock_reticulum.transport_enabled.return_value = True

        app = ReticulumMeshChat(
            identity=identity,
            storage_dir=str(tmp_path),
            reticulum_config_dir=str(tmp_path),
        )
        handler = await _find_add_handler(app)
        assert handler is not None

        class Request:
            @staticmethod
            async def json():
                return {
                    "name": "MSK SZAO [HaLow Bridge]",
                    "type": "TCPClientInterface",
                    "target_host": "dreadgurizta.ru",
                    "target_port": 4242,
                    "enabled": True,
                }

        response = await handler(Request())
        body = json.loads(response.body)
        assert response.status == 200, body
        assert "MSK SZAO (HaLow Bridge)" in config["interfaces"]
        assert "MSK SZAO [HaLow Bridge]" not in config["interfaces"]
        assert config.write_called is True


@pytest.mark.asyncio
async def test_failed_write_rolls_back_dirty_interfaces(tmp_path):
    config = _ConfigDict({"reticulum": {}, "interfaces": {}}, fail_write=True)
    identity = MagicMock(spec=RNS.Identity)
    identity.hash = b"test_hash_32_bytes_long_01234567"
    identity.hexhash = identity.hash.hex()
    identity.get_private_key.return_value = b"test_private_key"

    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
    ):
        mock_reticulum = mock_rns.return_value
        mock_reticulum.config = config
        mock_reticulum.configpath = str(tmp_path / "config")
        mock_reticulum.is_connected_to_shared_instance = False
        mock_reticulum.transport_enabled.return_value = True

        app = ReticulumMeshChat(
            identity=identity,
            storage_dir=str(tmp_path),
            reticulum_config_dir=str(tmp_path),
        )
        handler = await _find_add_handler(app)
        assert handler is not None

        class Request:
            @staticmethod
            async def json():
                return {
                    "name": "Good Node",
                    "type": "TCPClientInterface",
                    "target_host": "example.com",
                    "target_port": 4242,
                    "enabled": True,
                }

        response = await handler(Request())
        body = json.loads(response.body)
        assert response.status == 500, body
        assert "Failed to write Reticulum config" in body["message"]
        assert config["interfaces"] == {}
