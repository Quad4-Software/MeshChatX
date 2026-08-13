# SPDX-License-Identifier: 0BSD

"""Oracle: Interfaces tiles must include every on-disk [[section]]."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.interface_config_parser import InterfaceConfigParser


DOTTED_CONFIG = """\
[reticulum]
enable_transport = False

[interfaces]
  [[Default Interface]]
    type = AutoInterface
    interface_enabled = True
  [[artyom.ddns.net]]
    type = TCPClientInterface
    interface_enabled = True
    target_host = 10.100.11.12
    target_port = 4242
    name = artyom.ddns.net
  [[Catz-Node (TCP)]]
    type = TCPClientInterface
    interface_enabled = True
    target_host = 1.2.3.4
    target_port = 4242
"""


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns_minimal():
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
    ):
        mock_rns_instance = mock_rns.return_value
        mock_rns_instance.configpath = "/tmp/mock_config"
        mock_rns_instance.is_connected_to_shared_instance = False
        mock_rns_instance.transport_enabled.return_value = True

        mock_id = MagicMock(spec=RNS.Identity)
        mock_id.hash = b"test_hash_32_bytes_long_01234567"
        mock_id.hexhash = mock_id.hash.hex()
        mock_id.get_private_key.return_value = b"test_private_key"
        yield mock_id


@pytest.fixture
def app(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=os.path.join(temp_dir, ".reticulum"),
        )
        instance.reticulum.config = {
            "reticulum": {},
            "interfaces": {
                "Default Interface": {
                    "type": "AutoInterface",
                    "interface_enabled": "True",
                },
                "Catz-Node (TCP)": {
                    "type": "TCPClientInterface",
                    "interface_enabled": "True",
                    "target_host": "1.2.3.4",
                    "target_port": "4242",
                },
            },
        }
        yield instance


def _find_handler(app_instance, method, path):
    for route in app_instance.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    raise AssertionError(f"Handler not found: {method} {path}")


def _write_disk_config(app_instance, text=DOTTED_CONFIG):
    path = app_instance._reticulum_config_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def _oracle_disk_names(text):
    return {iface["name"] for iface in InterfaceConfigParser.parse(text)}


@pytest.mark.asyncio
async def test_get_interfaces_includes_disk_only_dotted_name(app):
    _write_disk_config(app)
    oracle_names = _oracle_disk_names(DOTTED_CONFIG)
    assert "artyom.ddns.net" in oracle_names
    assert "artyom.ddns.net" not in app.reticulum.config["interfaces"]

    handler = _find_handler(app, "GET", "/api/v1/reticulum/interfaces")
    response = await handler(MagicMock())
    assert response.status == 200
    body = json.loads(response.body)
    listed = set(body["interfaces"].keys())
    assert oracle_names <= listed
    assert body["interfaces"]["artyom.ddns.net"]["type"] == "TCPClientInterface"
    assert body["interfaces"]["artyom.ddns.net"]["target_host"] == "10.100.11.12"


@pytest.mark.asyncio
async def test_delete_removes_disk_only_dotted_name(app):
    from RNS.vendor.configobj import ConfigObj

    path = _write_disk_config(app)
    live = ConfigObj(path)
    del live["interfaces"]["artyom.ddns.net"]
    live.filename = path
    app.reticulum.config = live
    app.reticulum.configpath = path
    assert "artyom.ddns.net" not in app.reticulum.config["interfaces"]

    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/delete")

    class Request:
        @staticmethod
        async def json():
            return {"name": "artyom.ddns.net"}

    response = await handler(Request())
    assert response.status == 200, json.loads(response.body)
    assert "artyom.ddns.net" not in app.reticulum.config["interfaces"]

    remaining_names = _oracle_disk_names(open(path, encoding="utf-8").read())
    assert "artyom.ddns.net" not in remaining_names
    assert "Default Interface" in remaining_names
    assert "Catz-Node (TCP)" in remaining_names


@pytest.mark.asyncio
async def test_raw_put_replaces_live_interfaces_from_file(app):
    handler = _find_handler(app, "PUT", "/api/v1/reticulum/config/raw")

    class Request:
        @staticmethod
        async def json():
            return {"content": DOTTED_CONFIG}

    response = await handler(Request())
    assert response.status == 200, json.loads(response.body)
    live_names = set(app.reticulum.config["interfaces"].keys())
    assert live_names == _oracle_disk_names(DOTTED_CONFIG)


@pytest.mark.asyncio
async def test_get_skips_non_dict_interface_values(app):
    app.reticulum.config["interfaces"]["broken"] = "not-a-section"
    handler = _find_handler(app, "GET", "/api/v1/reticulum/interfaces")
    response = await handler(MagicMock())
    assert response.status == 200
    body = json.loads(response.body)
    assert "broken" not in body["interfaces"]
    assert "Default Interface" in body["interfaces"]
