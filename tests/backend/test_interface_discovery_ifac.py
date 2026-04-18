# SPDX-License-Identifier: 0BSD
"""
Tests for encrypted IFAC values surfaced via interface discovery announces.

When an upstream interface is configured with publish_ifac = yes, RNS embeds
the network_name (ifac_netname) and passphrase (ifac_netkey) into the
discovery announce payload, plus a ready-to-paste config_entry block. These
tests verify that:

1. The /api/v1/reticulum/discovered-interfaces endpoint passes those fields
   through to the frontend with both the raw RNS keys and the canonical
   config-style aliases (network_name/passphrase).
2. ReticulumMeshChat.normalize_discovered_ifac_fields handles bytes payloads,
   missing values, and non-list inputs without raising.
3. discovery_filter_candidates includes network_name so users can whitelist
   or blacklist by IFAC network name.
"""

import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS

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


async def find_route_handler(app_instance, path, method):
    for route in app_instance.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def test_normalize_handles_non_list_input():
    assert (
        ReticulumMeshChat.normalize_discovered_ifac_fields({"foo": "bar"})
        == {"foo": "bar"}
    )
    assert ReticulumMeshChat.normalize_discovered_ifac_fields(None) is None


def test_normalize_aliases_string_ifac_fields():
    interfaces = [
        {
            "name": "kin.earth",
            "type": "BackboneInterface",
            "reachable_on": "rns.kin.earth",
            "port": 4242,
            "ifac_netname": "kin.earth",
            "ifac_netkey": "asty8vT8spXNQdCnPVMATbCKkwUxuzG9",
            "config_entry": "[[kin.earth]]\n  type = BackboneInterface\n  enabled = yes",
        },
    ]

    normalized = ReticulumMeshChat.normalize_discovered_ifac_fields(interfaces)

    assert normalized[0]["ifac_netname"] == "kin.earth"
    assert normalized[0]["ifac_netkey"] == "asty8vT8spXNQdCnPVMATbCKkwUxuzG9"
    assert normalized[0]["network_name"] == "kin.earth"
    assert normalized[0]["passphrase"] == "asty8vT8spXNQdCnPVMATbCKkwUxuzG9"
    assert normalized[0]["publish_ifac"] is True
    assert normalized[0]["config_entry"].startswith("[[kin.earth]]")


def test_normalize_decodes_bytes_ifac_fields():
    interfaces = [
        {
            "name": "bytes-iface",
            "type": "BackboneInterface",
            "ifac_netname": b"bytes_net",
            "ifac_netkey": b"bytes_key",
            "config_entry": b"[[bytes-iface]]\n  type = BackboneInterface",
        },
    ]
    normalized = ReticulumMeshChat.normalize_discovered_ifac_fields(interfaces)
    assert normalized[0]["network_name"] == "bytes_net"
    assert normalized[0]["passphrase"] == "bytes_key"
    assert normalized[0]["config_entry"].startswith("[[bytes-iface]]")


def test_normalize_missing_ifac_fields_yields_none_aliases():
    interfaces = [
        {
            "name": "open-iface",
            "type": "TCPClientInterface",
            "reachable_on": "10.0.0.1",
            "port": 4242,
        },
    ]
    normalized = ReticulumMeshChat.normalize_discovered_ifac_fields(interfaces)
    assert normalized[0]["ifac_netname"] is None
    assert normalized[0]["ifac_netkey"] is None
    assert normalized[0]["network_name"] is None
    assert normalized[0]["passphrase"] is None
    assert normalized[0]["publish_ifac"] is False
    assert normalized[0]["config_entry"] is None


def test_normalize_skips_non_dict_entries():
    interfaces = [
        "not a dict",
        {"name": "ok", "ifac_netname": "n", "ifac_netkey": "k"},
    ]
    normalized = ReticulumMeshChat.normalize_discovered_ifac_fields(interfaces)
    assert normalized[0] == "not a dict"
    assert normalized[1]["network_name"] == "n"
    assert normalized[1]["passphrase"] == "k"


def test_discovery_filter_candidates_includes_network_name():
    iface = {
        "name": "node-1",
        "type": "BackboneInterface",
        "network_name": "kin.earth",
        "ifac_netname": "kin.earth",
    }
    candidates = ReticulumMeshChat.discovery_filter_candidates(iface)
    assert "kin.earth" in candidates


def test_filter_discovered_interfaces_whitelist_by_network_name():
    interfaces = [
        {"name": "good", "type": "BackboneInterface", "network_name": "kin.earth"},
        {"name": "bad", "type": "BackboneInterface", "network_name": "other.net"},
    ]
    filtered = ReticulumMeshChat.filter_discovered_interfaces(
        interfaces,
        whitelist_patterns="kin.earth",
        blacklist_patterns="",
    )
    names = [i["name"] for i in filtered]
    assert names == ["good"]


@pytest.mark.asyncio
async def test_discovered_interfaces_endpoint_surfaces_ifac(temp_dir):
    """End-to-end: HTTP endpoint exposes IFAC values from RNS announce."""
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.InterfaceDiscovery") as mock_discovery_cls,
    ):
        mock_reticulum = mock_rns.return_value
        mock_reticulum.config = config
        mock_reticulum.configpath = "/tmp/mock_config"
        mock_reticulum.is_connected_to_shared_instance = False
        mock_reticulum.transport_enabled.return_value = True
        mock_reticulum.get_interface_stats.return_value = {"interfaces": []}

        cfg_block = (
            "[[kin.earth]]\n"
            "  type = BackboneInterface\n"
            "  enabled = yes\n"
            "  remote = rns.kin.earth\n"
            "  target_port = 4242\n"
            "  transport_identity = eea3d09f02143e157b3dae83060ee843\n"
            "  network_name = kin.earth\n"
            "  passphrase = asty8vT8spXNQdCnPVMATbCKkwUxuzG9"
        )

        mock_discovery_cls.return_value.list_discovered_interfaces.return_value = [
            {
                "name": "kin.earth",
                "type": "BackboneInterface",
                "reachable_on": "rns.kin.earth",
                "port": 4242,
                "transport_id": "eea3d09f02143e157b3dae83060ee843",
                "network_id": "abc123",
                "value": 16,
                "hops": 1,
                "status": "available",
                "last_heard": 1700000000,
                "ifac_netname": "kin.earth",
                "ifac_netkey": "asty8vT8spXNQdCnPVMATbCKkwUxuzG9",
                "config_entry": cfg_block,
            },
            {
                "name": "open-node",
                "type": "BackboneInterface",
                "reachable_on": "open.example",
                "port": 4242,
                "transport_id": "ff" * 16,
                "network_id": "def456",
                "value": 8,
                "hops": 2,
                "status": "available",
                "last_heard": 1700000001,
            },
        ]

        app_instance = ReticulumMeshChat(
            identity=build_identity(),
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/discovered-interfaces",
            "GET",
        )
        assert handler

        response = await handler(MagicMock())
        data = json.loads(response.body)
        ifaces = data["interfaces"]
        assert len(ifaces) == 2

        encrypted = next(i for i in ifaces if i["name"] == "kin.earth")
        assert encrypted["ifac_netname"] == "kin.earth"
        assert encrypted["ifac_netkey"] == "asty8vT8spXNQdCnPVMATbCKkwUxuzG9"
        assert encrypted["network_name"] == "kin.earth"
        assert encrypted["passphrase"] == "asty8vT8spXNQdCnPVMATbCKkwUxuzG9"
        assert encrypted["publish_ifac"] is True
        assert encrypted["config_entry"].startswith("[[kin.earth]]")
        assert "network_name = kin.earth" in encrypted["config_entry"]

        plain = next(i for i in ifaces if i["name"] == "open-node")
        assert plain["network_name"] is None
        assert plain["passphrase"] is None
        assert plain["publish_ifac"] is False


@pytest.mark.asyncio
async def test_discovered_interfaces_filter_works_with_ifac_network_name(temp_dir):
    """Whitelist/blacklist patterns can match an announce by its network_name."""
    config = ConfigDict(
        {
            "reticulum": {
                "interface_discovery_whitelist": "kin.earth",
            },
            "interfaces": {},
        },
    )

    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.InterfaceDiscovery") as mock_discovery_cls,
    ):
        mock_reticulum = mock_rns.return_value
        mock_reticulum.config = config
        mock_reticulum.configpath = "/tmp/mock_config"
        mock_reticulum.is_connected_to_shared_instance = False
        mock_reticulum.transport_enabled.return_value = True
        mock_reticulum.get_interface_stats.return_value = {"interfaces": []}

        mock_discovery_cls.return_value.list_discovered_interfaces.return_value = [
            {
                "name": "matching",
                "type": "BackboneInterface",
                "reachable_on": "10.0.0.1",
                "port": 4242,
                "ifac_netname": "kin.earth",
                "ifac_netkey": "secret",
            },
            {
                "name": "non-matching",
                "type": "BackboneInterface",
                "reachable_on": "10.0.0.2",
                "port": 4242,
                "ifac_netname": "other.net",
                "ifac_netkey": "other",
            },
        ]

        app_instance = ReticulumMeshChat(
            identity=build_identity(),
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/discovered-interfaces",
            "GET",
        )
        assert handler

        response = await handler(MagicMock())
        data = json.loads(response.body)
        names = [i["name"] for i in data["interfaces"]]
        assert names == ["matching"]
        assert data["interfaces"][0]["network_name"] == "kin.earth"
        assert data["interfaces"][0]["passphrase"] == "secret"
