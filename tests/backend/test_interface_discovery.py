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


@pytest.mark.asyncio
async def test_reticulum_discovery_get_and_patch(temp_dir):
    config = ConfigDict(
        {
            "reticulum": {
                "discover_interfaces": "true",
                "interface_discovery_sources": "abc,def",
                "required_discovery_value": "16",
                "autoconnect_discovered_interfaces": "2",
                "network_identity": "/tmp/net_id",
            },
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

        get_handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/discovery",
            "GET",
        )
        patch_handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/discovery",
            "PATCH",
        )
        assert get_handler and patch_handler

        # GET returns current reticulum discovery config
        get_response = await get_handler(MagicMock())
        get_data = json.loads(get_response.body)
        assert get_data["discovery"]["discover_interfaces"] == "true"
        assert get_data["discovery"]["interface_discovery_sources"] == "abc,def"
        assert get_data["discovery"]["required_discovery_value"] == "16"
        assert get_data["discovery"]["autoconnect_discovered_interfaces"] == "2"
        assert get_data["discovery"]["network_identity"] == "/tmp/net_id"

        # PATCH updates and persists
        new_config = {
            "discover_interfaces": False,
            "interface_discovery_sources": "",
            "required_discovery_value": 18,
            "autoconnect_discovered_interfaces": 5,
            "network_identity": "/tmp/other_id",
        }

        class PatchRequest:
            @staticmethod
            async def json():
                return new_config

        patch_response = await patch_handler(PatchRequest())
        patch_data = json.loads(patch_response.body)
        assert patch_data["discovery"]["discover_interfaces"] is False
        assert patch_data["discovery"]["interface_discovery_sources"] is None
        assert patch_data["discovery"]["required_discovery_value"] == 18
        assert patch_data["discovery"]["autoconnect_discovered_interfaces"] == 5
        assert patch_data["discovery"]["network_identity"] == "/tmp/other_id"
        assert config["reticulum"]["discover_interfaces"] is False
        assert "interface_discovery_sources" not in config["reticulum"]
        assert config["reticulum"]["required_discovery_value"] == 18
        assert config["reticulum"]["autoconnect_discovered_interfaces"] == 5
        assert config["reticulum"]["network_identity"] == "/tmp/other_id"
        assert config.write_called


@pytest.mark.asyncio
async def test_interface_add_includes_discovery_fields(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

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

        add_handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/interfaces/add",
            "POST",
        )
        assert add_handler

        payload = {
            "allow_overwriting_interface": False,
            "name": "TestIface",
            "type": "TCPClientInterface",
            "target_host": "example.com",
            "target_port": "4242",
            "discoverable": "yes",
            "discovery_name": "Region A",
            "announce_interval": 720,
            "reachable_on": "/usr/bin/get_ip.sh",
            "discovery_stamp_value": 22,
            "discovery_encrypt": True,
            "publish_ifac": True,
            "latitude": 10.1,
            "longitude": 20.2,
            "height": 30,
            "discovery_frequency": 915000000,
            "discovery_bandwidth": 125000,
            "discovery_modulation": "LoRa",
        }

        class AddRequest:
            @staticmethod
            async def json():
                return payload

        response = await add_handler(AddRequest())
        data = json.loads(response.body)
        assert "Interface has been added" in data["message"]
        saved = config["interfaces"]["TestIface"]
        assert saved["discoverable"] == "yes"
        assert saved["discovery_name"] == "Region A"
        assert saved["announce_interval"] == 720
        assert saved["reachable_on"] == "/usr/bin/get_ip.sh"
        assert saved["discovery_stamp_value"] == 22
        assert saved["discovery_encrypt"] is True
        assert saved["publish_ifac"] is True
        assert saved["latitude"] == 10.1
        assert saved["longitude"] == 20.2
        assert saved["height"] == 30
        assert saved["discovery_frequency"] == 915000000
        assert saved["discovery_bandwidth"] == 125000
        assert saved["discovery_modulation"] == "LoRa"
        assert config.write_called
