# SPDX-License-Identifier: 0BSD

"""End-to-end tests for the /api/v1/reticulum/interfaces/add endpoint.

Each test exercises one interface type and asserts that the rich set of
options exposed in the UI is persisted into the Reticulum config dict.
"""

import contextlib
import json
import shutil
import socket
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

        handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/interfaces/add",
            "POST",
        )
        assert handler
        yield handler


def make_request(payload):
    class Request:
        @staticmethod
        async def json():
            return payload

    return Request()


def _free_port(kind="tcp"):
    sock_type = socket.SOCK_STREAM if kind == "tcp" else socket.SOCK_DGRAM
    with contextlib.closing(socket.socket(socket.AF_INET, sock_type)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.asyncio
async def test_auto_interface_persists_full_options(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    async with make_app(temp_dir, config) as handler:
        payload = {
            "name": "AutoLAN",
            "type": "AutoInterface",
            "group_id": "homelab",
            "discovery_scope": "site",
            "discovery_port": 35000,
            "data_port": 35001,
            "multicast_address_type": "permanent",
            "devices": "eth0, wlan0",
            "ignored_devices": "tun0",
            "configured_bitrate": 5000000,
        }
        response = await handler(make_request(payload))
        body = json.loads(response.body)
        assert response.status == 200, body
        saved = config["interfaces"]["AutoLAN"]
        assert saved["type"] == "AutoInterface"
        assert saved["group_id"] == "homelab"
        assert saved["discovery_scope"] == "site"
        assert saved["discovery_port"] == 35000
        assert saved["data_port"] == 35001
        assert saved["multicast_address_type"] == "permanent"
        assert saved["devices"] == "eth0, wlan0"
        assert saved["ignored_devices"] == "tun0"
        assert saved["configured_bitrate"] == 5000000


@pytest.mark.asyncio
async def test_auto_interface_rejects_invalid_discovery_scope(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    async with make_app(temp_dir, config) as handler:
        payload = {
            "name": "AutoLAN",
            "type": "AutoInterface",
            "discovery_scope": "outerspace",
        }
        response = await handler(make_request(payload))
        body = json.loads(response.body)
        assert response.status == 422
        assert "discovery scope" in body["message"].lower()


@pytest.mark.asyncio
async def test_auto_interface_rejects_invalid_multicast_type(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    async with make_app(temp_dir, config) as handler:
        payload = {
            "name": "AutoLAN",
            "type": "AutoInterface",
            "multicast_address_type": "weird",
        }
        response = await handler(make_request(payload))
        body = json.loads(response.body)
        assert response.status == 422
        assert "multicast" in body["message"].lower()


@pytest.mark.asyncio
async def test_auto_interface_rejects_busy_data_port(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    busy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    busy.bind(("127.0.0.1", 0))
    busy_port = busy.getsockname()[1]
    try:
        async with make_app(temp_dir, config) as handler:
            payload = {
                "name": "AutoLAN",
                "type": "AutoInterface",
                "data_port": busy_port,
            }
            response = await handler(make_request(payload))
            body = json.loads(response.body)
            assert response.status == 409, body
            assert str(busy_port) in body["message"]
    finally:
        busy.close()


@pytest.mark.asyncio
async def test_tcp_client_persists_advanced_options(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    async with make_app(temp_dir, config) as handler:
        payload = {
            "name": "TCPClient",
            "type": "TCPClientInterface",
            "target_host": "example.com",
            "target_port": "4242",
            "kiss_framing": True,
            "i2p_tunneled": True,
            "connect_timeout": 12,
            "max_reconnect_tries": 7,
            "fixed_mtu": 480,
        }
        response = await handler(make_request(payload))
        body = json.loads(response.body)
        assert response.status == 200, body
        saved = config["interfaces"]["TCPClient"]
        assert saved["kiss_framing"] is True
        assert saved["i2p_tunneled"] is True
        assert saved["connect_timeout"] == 12
        assert saved["max_reconnect_tries"] == 7
        assert saved["fixed_mtu"] == 480


@pytest.mark.asyncio
async def test_tcp_server_persists_optional_options(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    free_port = _free_port("tcp")
    async with make_app(temp_dir, config) as handler:
        payload = {
            "name": "TCPServer",
            "type": "TCPServerInterface",
            "listen_ip": "127.0.0.1",
            "listen_port": free_port,
            "device": "eth0",
            "prefer_ipv6": True,
            "i2p_tunneled": True,
        }
        response = await handler(make_request(payload))
        body = json.loads(response.body)
        assert response.status == 200, body
        saved = config["interfaces"]["TCPServer"]
        assert saved["device"] == "eth0"
        assert saved["prefer_ipv6"] is True
        assert saved["i2p_tunneled"] is True


@pytest.mark.asyncio
async def test_tcp_server_rejects_busy_listen_port(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    busy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    busy.bind(("127.0.0.1", 0))
    busy.listen(1)
    busy_port = busy.getsockname()[1]
    try:
        async with make_app(temp_dir, config) as handler:
            payload = {
                "name": "TCPServer",
                "type": "TCPServerInterface",
                "listen_ip": "127.0.0.1",
                "listen_port": busy_port,
            }
            response = await handler(make_request(payload))
            body = json.loads(response.body)
            assert response.status == 409, body
            assert str(busy_port) in body["message"]
    finally:
        busy.close()


@pytest.mark.asyncio
async def test_udp_rejects_busy_listen_port(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    busy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    busy.bind(("127.0.0.1", 0))
    busy_port = busy.getsockname()[1]
    try:
        async with make_app(temp_dir, config) as handler:
            payload = {
                "name": "UDP1",
                "type": "UDPInterface",
                "listen_ip": "127.0.0.1",
                "listen_port": busy_port,
                "forward_ip": "255.255.255.255",
                "forward_port": busy_port,
            }
            response = await handler(make_request(payload))
            body = json.loads(response.body)
            assert response.status == 409, body
            assert "UDP" in body["message"]
    finally:
        busy.close()


@pytest.mark.asyncio
async def test_backbone_listener_mode_persists_options(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    free_port = _free_port("tcp")
    async with make_app(temp_dir, config) as handler:
        payload = {
            "name": "BackboneListen",
            "type": "BackboneInterface",
            "listen_ip": "127.0.0.1",
            "listen_port": free_port,
            "device": "eth0",
            "prefer_ipv6": True,
        }
        response = await handler(make_request(payload))
        body = json.loads(response.body)
        assert response.status == 200, body
        saved = config["interfaces"]["BackboneListen"]
        assert saved["listen_port"] == free_port
        assert saved["listen_ip"] == "127.0.0.1"
        assert saved["device"] == "eth0"
        assert saved["prefer_ipv6"] is True


@pytest.mark.asyncio
async def test_backbone_connector_mode_still_requires_remote(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    async with make_app(temp_dir, config) as handler:
        payload = {
            "name": "BackboneOut",
            "type": "BackboneInterface",
            "target_port": "4242",
            "transport_identity": "00" * 16,
        }
        response = await handler(make_request(payload))
        body = json.loads(response.body)
        assert response.status == 422
        assert "remote" in body["message"].lower()


@pytest.mark.asyncio
async def test_rnode_persists_flow_control_and_id_callsign(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    async with make_app(temp_dir, config) as handler:
        payload = {
            "name": "Radio",
            "type": "RNodeInterface",
            "port": "/dev/ttyUSB0",
            "frequency": 868000000,
            "bandwidth": 125000,
            "txpower": 7,
            "spreadingfactor": 8,
            "codingrate": 5,
            "flow_control": True,
            "id_callsign": "NOCALL",
            "id_interval": 600,
            "airtime_limit_long": 1.5,
            "airtime_limit_short": 33.0,
        }
        response = await handler(make_request(payload))
        body = json.loads(response.body)
        assert response.status == 200, body
        saved = config["interfaces"]["Radio"]
        assert saved["flow_control"] is True
        assert saved["id_callsign"] == "NOCALL"
        assert saved["id_interval"] == 600
        assert saved["airtime_limit_long"] == 1.5
        assert saved["airtime_limit_short"] == 33.0


@pytest.mark.asyncio
async def test_kiss_persists_full_serial_options(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    async with make_app(temp_dir, config) as handler:
        payload = {
            "name": "KISSRadio",
            "type": "KISSInterface",
            "port": "/dev/ttyACM0",
            "speed": 19200,
            "databits": 8,
            "parity": "N",
            "stopbits": 1,
            "preamble": 200,
            "txtail": 30,
            "persistence": 128,
            "slottime": 25,
            "flow_control": True,
            "id_callsign": "BEACON",
            "id_interval": 1200,
        }
        response = await handler(make_request(payload))
        body = json.loads(response.body)
        assert response.status == 200, body
        saved = config["interfaces"]["KISSRadio"]
        assert saved["speed"] == 19200
        assert saved["databits"] == 8
        assert saved["parity"] == "N"
        assert saved["stopbits"] == 1
        assert saved["preamble"] == 200
        assert saved["txtail"] == 30
        assert saved["persistence"] == 128
        assert saved["slottime"] == 25
        assert saved["flow_control"] is True
        assert saved["id_callsign"] == "BEACON"
        assert saved["id_interval"] == 1200


@pytest.mark.asyncio
async def test_ax25_kiss_persists_callsign_and_ssid(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    async with make_app(temp_dir, config) as handler:
        payload = {
            "name": "AX25",
            "type": "AX25KISSInterface",
            "port": "/dev/ttyACM1",
            "callsign": "N0CALL",
            "ssid": 7,
        }
        response = await handler(make_request(payload))
        body = json.loads(response.body)
        assert response.status == 200, body
        saved = config["interfaces"]["AX25"]
        assert saved["callsign"] == "N0CALL"
        assert saved["ssid"] == 7


@pytest.mark.asyncio
async def test_i2p_connectable_can_be_disabled(temp_dir):
    config = ConfigDict({"reticulum": {}, "interfaces": {}})

    async with make_app(temp_dir, config) as handler:
        payload = {
            "name": "I2POut",
            "type": "I2PInterface",
            "peers": ["abcdef.b32.i2p"],
            "connectable": False,
        }
        response = await handler(make_request(payload))
        body = json.loads(response.body)
        assert response.status == 200, body
        saved = config["interfaces"]["I2POut"]
        assert saved["connectable"] == "False"
        assert saved["peers"] == ["abcdef.b32.i2p"]
