# SPDX-License-Identifier: 0BSD

"""Tests for the Android local-link bridge and its HTTP routes.

The Java bridge is faked everywhere: these tests pin the Python contract
(state transitions, validation, error mapping) without an Android runtime.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend import android_locallink
from meshchatx.src.backend.http.routes.locallink import (
    _validate_join_params,
    register_locallink_routes,
)


@pytest.fixture(autouse=True)
def reset_locallink_state():
    """Each test starts from a clean bridge and state."""
    with android_locallink._bridge_lock:
        android_locallink._bridge = None
    android_locallink._activity = None
    android_locallink._nfc = None
    android_locallink._aware = None
    android_locallink._aware_listeners.clear()
    android_locallink._p2p_event.clear()
    with android_locallink._state_lock:
        android_locallink._state.update(
            {
                "hotspot_active": False,
                "hotspot_ssid": None,
                "hotspot_passphrase": None,
                "join_status": "idle",
                "join_network_connected": False,
                "p2p_active": False,
                "p2p_ssid": None,
                "p2p_passphrase": None,
                "nfc_sharing": False,
                "nfc_reading": False,
                "nfc_last_payload": None,
            }
        )
        android_locallink._aware_state.update(
            {"role": "off", "session": False, "peers": {}, "links": {}}
        )
    yield


def _make_app() -> web.Application:
    app = web.Application()
    app.meshchat = SimpleNamespace(platform="android")
    routes = web.RouteTableDef()
    register_locallink_routes(routes, app)
    app.add_routes(routes)
    return app


class _FakeBridge:
    """Stands in for org.meshchatx.locallink.LocalLink."""

    def __init__(self):
        self.calls = []
        self.probe = {
            "hotspot": True,
            "wifi_join_specifier": True,
            "wifi_aware": True,
            "wifi_aware_available": False,
            "wifi_direct": True,
            "nfc": True,
            "satellite": {"feature": False, "enabled": None},
        }

    def probeCapabilities(self):
        import json

        return json.dumps(self.probe)

    def startHotspot(self):
        self.calls.append(("startHotspot",))

    def stopHotspot(self):
        self.calls.append(("stopHotspot",))

    def joinWifiNetwork(self, ssid, passphrase):
        self.calls.append(("joinWifiNetwork", ssid, passphrase))

    def cancelJoin(self):
        self.calls.append(("cancelJoin",))


def _install_fake_bridge(bridge):
    with android_locallink._bridge_lock:
        android_locallink._bridge = bridge


# ---------------------------------------------------------------------------
# join parameter validation
# ---------------------------------------------------------------------------


class TestValidateJoinParams:
    def test_missing_ssid(self):
        ssid, psk, err = _validate_join_params({})
        assert err == "ssid is required"
        assert ssid is None and psk is None

    def test_non_string_ssid(self):
        assert _validate_join_params({"ssid": 42})[2] == "ssid is required"

    def test_blank_ssid(self):
        assert _validate_join_params({"ssid": "   "})[2] == "ssid is required"

    def test_ssid_too_long(self):
        assert _validate_join_params({"ssid": "x" * 33})[2] == "ssid too long"

    def test_valid_open_network(self):
        ssid, psk, err = _validate_join_params({"ssid": "MeshNet"})
        assert err is None and ssid == "MeshNet" and psk is None

    def test_empty_passphrase_becomes_open(self):
        _ssid, psk, err = _validate_join_params({"ssid": "Net", "passphrase": ""})
        assert err is None and psk is None

    def test_short_passphrase_rejected(self):
        assert _validate_join_params({"ssid": "N", "passphrase": "short"})[2] == (
            "passphrase must be 8-63 characters"
        )

    def test_long_passphrase_rejected(self):
        assert _validate_join_params({"ssid": "N", "passphrase": "x" * 64})[2] == (
            "passphrase must be 8-63 characters"
        )

    def test_non_string_passphrase(self):
        assert _validate_join_params({"ssid": "N", "passphrase": 123})[2] == (
            "passphrase must be a string"
        )

    def test_valid_wpa_network(self):
        ssid, psk, err = _validate_join_params(
            {"ssid": " MeshNet ", "passphrase": "correct horse"}
        )
        assert err is None and ssid == "MeshNet" and psk == "correct horse"


# ---------------------------------------------------------------------------
# bridge functions without Android
# ---------------------------------------------------------------------------


class TestBridgeUnavailable:
    def test_probe_capabilities_unsupported(self):
        data = android_locallink.probe_capabilities()
        assert data["supported"] is False
        assert data["hotspot"] is False
        assert data["wifi_aware"] is False

    def test_start_hotspot_unsupported(self):
        assert android_locallink.start_hotspot()["supported"] is False

    def test_stop_hotspot_unsupported(self):
        assert android_locallink.stop_hotspot()["supported"] is False

    def test_join_wifi_unsupported(self):
        assert android_locallink.join_wifi("N", None)["supported"] is False

    def test_leave_wifi_unsupported(self):
        assert android_locallink.leave_wifi()["supported"] is False


# ---------------------------------------------------------------------------
# bridge functions with a fake bridge
# ---------------------------------------------------------------------------


class TestBridgeBacked:
    def test_probe_merges_state(self):
        bridge = _FakeBridge()
        _install_fake_bridge(bridge)
        android_locallink._state["join_status"] = "requested"
        data = android_locallink.probe_capabilities()
        assert data["supported"] is True
        assert data["hotspot"] is True
        assert data["join_status"] == "requested"
        assert "satellite" in data

    def test_start_hotspot_success(self):
        bridge = _FakeBridge()

        def started():
            android_locallink._state["hotspot_active"] = True
            android_locallink._state["hotspot_ssid"] = "DIRECT-ab"
            android_locallink._state["hotspot_passphrase"] = "sekret123"
            android_locallink._hotspot_event.set()

        bridge.startHotspot = MagicMock(side_effect=lambda: started())
        _install_fake_bridge(bridge)
        result = android_locallink.start_hotspot(timeout=5.0)
        assert result == {
            "supported": True,
            "ok": True,
            "ssid": "DIRECT-ab",
            "passphrase": "sekret123",
            "error": None,
        }
        assert bridge.startHotspot.called

    def test_start_hotspot_failure_callback(self):
        bridge = _FakeBridge()
        bridge.startHotspot = MagicMock(
            side_effect=lambda: (
                android_locallink._state.update({"hotspot_error": "ERROR_NO_CHANNEL"}),
                android_locallink._hotspot_event.set(),
            )
        )
        _install_fake_bridge(bridge)
        result = android_locallink.start_hotspot(timeout=5.0)
        assert result["ok"] is False
        assert result["error"] == "ERROR_NO_CHANNEL"

    def test_start_hotspot_timeout(self):
        bridge = _FakeBridge()
        _install_fake_bridge(bridge)
        result = android_locallink.start_hotspot(timeout=0.05)
        assert result["ok"] is False
        assert "timed out" in result["error"]

    def test_start_hotspot_bridge_exception(self):
        bridge = _FakeBridge()
        bridge.startHotspot = MagicMock(side_effect=RuntimeError("boom"))
        _install_fake_bridge(bridge)
        result = android_locallink.start_hotspot()
        assert result["ok"] is False
        assert "boom" in result["error"]

    def test_stop_hotspot_clears_state(self):
        bridge = _FakeBridge()
        _install_fake_bridge(bridge)
        android_locallink._state["hotspot_active"] = True
        android_locallink._state["hotspot_ssid"] = "X"
        android_locallink._state["hotspot_passphrase"] = "p"
        result = android_locallink.stop_hotspot()
        assert result["ok"] is True
        assert android_locallink._state["hotspot_active"] is False
        assert android_locallink._state["hotspot_ssid"] is None
        assert android_locallink._state["hotspot_passphrase"] is None

    def test_join_wifi_requests(self):
        bridge = _FakeBridge()
        _install_fake_bridge(bridge)
        result = android_locallink.join_wifi("MeshNet", "sekret123")
        assert result == {"supported": True, "ok": True, "status": "requested"}
        assert ("joinWifiNetwork", "MeshNet", "sekret123") in bridge.calls
        assert android_locallink._state["join_status"] == "requested"

    def test_join_wifi_open_network(self):
        bridge = _FakeBridge()
        _install_fake_bridge(bridge)
        android_locallink.join_wifi("OpenNet", None)
        assert ("joinWifiNetwork", "OpenNet", "") in bridge.calls

    def test_leave_wifi(self):
        bridge = _FakeBridge()
        _install_fake_bridge(bridge)
        android_locallink._state["join_status"] = "available"
        android_locallink._state["join_network_connected"] = True
        result = android_locallink.leave_wifi()
        assert result["ok"] is True
        assert android_locallink._state["join_status"] == "idle"
        assert android_locallink._state["join_network_connected"] is False

    def test_install_noop_without_activity(self):
        assert android_locallink.install_android_locallink(None) is False


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------


class TestLocalLinkRoutes:
    @pytest.mark.asyncio
    async def test_capabilities_route(self):
        _install_fake_bridge(_FakeBridge())
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.get("/api/v1/locallink/capabilities")
            assert response.status == 200
            data = await response.json()
            assert data["supported"] is True
            assert data["hotspot"] is True

    @pytest.mark.asyncio
    async def test_capabilities_route_desktop(self):
        app = web.Application()
        app.meshchat = SimpleNamespace(platform="linux")
        routes = web.RouteTableDef()
        register_locallink_routes(routes, app)
        app.add_routes(routes)
        async with TestClient(TestServer(app)) as client:
            response = await client.get("/api/v1/locallink/capabilities")
            assert response.status == 200
            data = await response.json()
            assert data["supported"] is False

    @pytest.mark.asyncio
    async def test_hotspot_start_unsupported_platform(self):
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post("/api/v1/locallink/hotspot/start")
            assert response.status == 503

    @pytest.mark.asyncio
    async def test_hotspot_start_success(self):
        bridge = _FakeBridge()
        bridge.startHotspot = MagicMock(
            side_effect=lambda: (
                android_locallink._state.update(
                    {
                        "hotspot_active": True,
                        "hotspot_ssid": "DIRECT-ab",
                        "hotspot_passphrase": "sekret123",
                    }
                ),
                android_locallink._hotspot_event.set(),
            )
        )
        _install_fake_bridge(bridge)
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post("/api/v1/locallink/hotspot/start")
            assert response.status == 200
            data = await response.json()
            assert data["ok"] is True
            assert data["ssid"] == "DIRECT-ab"

    @pytest.mark.asyncio
    async def test_hotspot_stop_route(self):
        _install_fake_bridge(_FakeBridge())
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post("/api/v1/locallink/hotspot/stop")
            assert response.status == 200
            assert (await response.json())["ok"] is True

    @pytest.mark.asyncio
    async def test_join_validation_rejected(self):
        _install_fake_bridge(_FakeBridge())
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post(
                "/api/v1/locallink/wifi/join",
                json={"ssid": "x" * 40},
            )
            assert response.status == 400

    @pytest.mark.asyncio
    async def test_join_missing_ssid(self):
        _install_fake_bridge(_FakeBridge())
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post(
                "/api/v1/locallink/wifi/join",
                json={"passphrase": "sekret123"},
            )
            assert response.status == 400

    @pytest.mark.asyncio
    async def test_join_success(self):
        bridge = _FakeBridge()
        _install_fake_bridge(bridge)
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post(
                "/api/v1/locallink/wifi/join",
                json={"ssid": "MeshNet", "passphrase": "sekret123"},
            )
            assert response.status == 200
            data = await response.json()
            assert data["ok"] is True
            assert data["status"] == "requested"
            assert ("joinWifiNetwork", "MeshNet", "sekret123") in bridge.calls

    @pytest.mark.asyncio
    async def test_leave_route(self):
        _install_fake_bridge(_FakeBridge())
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post("/api/v1/locallink/wifi/leave")
            assert response.status == 200
            assert (await response.json())["ok"] is True


# ---------------------------------------------------------------------------
# WiFi Direct group
# ---------------------------------------------------------------------------


class _FakeAware:
    def __init__(self):
        self.calls = []

    def startPublish(self):
        self.calls.append(("startPublish",))

    def startSubscribe(self):
        self.calls.append(("startSubscribe",))

    def stop(self):
        self.calls.append(("stop",))

    def sendToPeer(self, peer_id, data):
        self.calls.append(("sendToPeer", peer_id, bytes(data)))
        return True

    def closePeer(self, peer_id):
        self.calls.append(("closePeer", peer_id))


class _FakeNfc:
    def __init__(self):
        self.payload = None
        self.reading = False

    def setSharePayload(self, payload):
        self.payload = payload

    def clearSharePayload(self):
        self.payload = None

    def startReader(self):
        self.reading = True

    def stopReader(self):
        self.reading = False


class TestP2PBridge:
    def test_start_p2p_success(self):
        bridge = _FakeBridge()
        bridge.p2pGroupCreate = MagicMock(
            side_effect=lambda: (
                android_locallink._state.update(
                    {
                        "p2p_active": True,
                        "p2p_ssid": "DIRECT-mc-abcd",
                        "p2p_passphrase": "grouppsk99",
                    }
                ),
                android_locallink._p2p_event.set(),
            )
        )
        _install_fake_bridge(bridge)
        result = android_locallink.start_p2p_group(timeout=5.0)
        assert result["ok"] is True
        assert result["ssid"] == "DIRECT-mc-abcd"
        assert result["passphrase"] == "grouppsk99"
        assert bridge.p2pGroupCreate.called

    def test_start_p2p_failure_callback(self):
        bridge = _FakeBridge()
        bridge.p2pGroupCreate = MagicMock(
            side_effect=lambda: (
                android_locallink._state.update({"p2p_error": "BUSY"}),
                android_locallink._p2p_event.set(),
            )
        )
        _install_fake_bridge(bridge)
        result = android_locallink.start_p2p_group(timeout=5.0)
        assert result["ok"] is False
        assert result["error"] == "BUSY"

    def test_start_p2p_timeout(self):
        bridge = _FakeBridge()
        bridge.p2pGroupCreate = MagicMock()
        _install_fake_bridge(bridge)
        result = android_locallink.start_p2p_group(timeout=0.05)
        assert result["ok"] is False
        assert "timed out" in result["error"]

    def test_start_p2p_bridge_exception(self):
        bridge = _FakeBridge()
        bridge.p2pGroupCreate = MagicMock(
            side_effect=RuntimeError("need NEARBY_WIFI_DEVICES")
        )
        _install_fake_bridge(bridge)
        result = android_locallink.start_p2p_group()
        assert result["ok"] is False
        assert "NEARBY_WIFI_DEVICES" in result["error"]

    def test_stop_p2p_clears_state(self):
        bridge = _FakeBridge()
        bridge.p2pGroupRemove = MagicMock()
        _install_fake_bridge(bridge)
        android_locallink._state["p2p_active"] = True
        android_locallink._state["p2p_ssid"] = "DIRECT-mc-x"
        android_locallink._state["p2p_passphrase"] = "p"
        result = android_locallink.stop_p2p_group()
        assert result["ok"] is True
        assert android_locallink._state["p2p_active"] is False
        assert android_locallink._state["p2p_ssid"] is None

    def test_p2p_unsupported(self):
        assert android_locallink.start_p2p_group()["supported"] is False
        assert android_locallink.stop_p2p_group()["supported"] is False

    def test_p2p_status(self):
        _install_fake_bridge(_FakeBridge())
        android_locallink._state["p2p_active"] = True
        android_locallink._state["p2p_ssid"] = "DIRECT-mc-z"
        status = android_locallink.p2p_status()
        assert status["supported"] is True
        assert status["active"] is True
        assert status["ssid"] == "DIRECT-mc-z"


class TestAwareBridge:
    def test_aware_unsupported(self):
        assert android_locallink.aware_start("subscribe")["supported"] is False
        assert android_locallink.aware_stop()["supported"] is False
        assert android_locallink.aware_send(1, b"x") is False

    def test_aware_start_roles(self):
        fake = _FakeAware()
        android_locallink._aware = fake
        result = android_locallink.aware_start("publish")
        assert result["ok"] is True and result["role"] == "publish"
        assert ("startPublish",) in fake.calls
        result = android_locallink.aware_start("subscribe")
        assert result["ok"] is True
        assert ("startSubscribe",) in fake.calls
        result = android_locallink.aware_start("bogus")
        assert result["ok"] is False

    def test_aware_stop_clears_state(self):
        fake = _FakeAware()
        android_locallink._aware = fake
        android_locallink._aware_state.update(
            {"role": "publish", "session": True, "peers": {1: True}, "links": {1: True}}
        )
        result = android_locallink.aware_stop()
        assert result["ok"] is True
        assert ("stop",) in fake.calls
        assert android_locallink._aware_state["role"] == "off"
        assert android_locallink._aware_state["links"] == {}

    def test_aware_send_and_close(self):
        fake = _FakeAware()
        android_locallink._aware = fake
        assert android_locallink.aware_send(7, b"frame") is True
        assert ("sendToPeer", 7, b"frame") in fake.calls
        android_locallink.aware_close_peer(7)
        assert ("closePeer", 7) in fake.calls

    def test_aware_listener_dispatch(self):
        seen = []
        android_locallink.register_aware_listener(
            lambda event, peer_id, data: seen.append((event, peer_id, data))
        )
        android_locallink._dispatch_aware("data", 3, b"payload")
        android_locallink._dispatch_aware("link_up", 3, None)
        assert seen == [("data", 3, b"payload"), ("link_up", 3, None)]

    def test_aware_listener_error_isolated(self):
        calls = []

        def bad(_e, _p, _d):
            raise RuntimeError("listener boom")

        android_locallink.register_aware_listener(bad)
        android_locallink.register_aware_listener(lambda e, p, d: calls.append(e))
        android_locallink._dispatch_aware("peer", 1, None)
        assert calls == ["peer"]


class TestNfcBridge:
    def test_nfc_unsupported(self):
        assert android_locallink.nfc_share("x")["supported"] is False
        assert android_locallink.nfc_read(True)["supported"] is False

    def test_nfc_share_set_and_clear(self):
        fake = _FakeNfc()
        android_locallink._nfc = fake
        result = android_locallink.nfc_share("meshchatx://share?x=1")
        assert result["ok"] is True and result["sharing"] is True
        assert fake.payload == "meshchatx://share?x=1"
        assert android_locallink._state["nfc_sharing"] is True
        result = android_locallink.nfc_share(None)
        assert result["ok"] is True and result["sharing"] is False
        assert fake.payload is None
        assert android_locallink._state["nfc_sharing"] is False

    def test_nfc_read_lifecycle(self):
        fake = _FakeNfc()
        android_locallink._nfc = fake
        assert android_locallink.nfc_read(True)["reading"] is True
        assert fake.reading is True
        assert android_locallink._state["nfc_reading"] is True
        assert android_locallink.nfc_read(False)["reading"] is False
        assert fake.reading is False

    def test_nfc_status_and_clear(self):
        fake = _FakeNfc()
        android_locallink._nfc = fake
        android_locallink._state["nfc_last_payload"] = "meshchatx://x"
        status = android_locallink.nfc_status()
        assert status["supported"] is True
        assert status["last_payload"] == "meshchatx://x"
        android_locallink.nfc_clear_last()
        assert android_locallink.nfc_status()["last_payload"] is None


# ---------------------------------------------------------------------------
# HTTP routes for stages 2-4
# ---------------------------------------------------------------------------


class TestNewRoutes:
    @pytest.mark.asyncio
    async def test_p2p_start_unsupported(self):
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post("/api/v1/locallink/p2p/start")
            assert response.status == 503

    @pytest.mark.asyncio
    async def test_p2p_start_success(self):
        bridge = _FakeBridge()
        bridge.p2pGroupCreate = MagicMock(
            side_effect=lambda: (
                android_locallink._state.update(
                    {
                        "p2p_active": True,
                        "p2p_ssid": "DIRECT-mc-ab",
                        "p2p_passphrase": "pskpskpsk1",
                    }
                ),
                android_locallink._p2p_event.set(),
            )
        )
        _install_fake_bridge(bridge)
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post("/api/v1/locallink/p2p/start")
            assert response.status == 200
            data = await response.json()
            assert data["ok"] is True
            assert data["ssid"] == "DIRECT-mc-ab"

    @pytest.mark.asyncio
    async def test_p2p_status_route(self):
        _install_fake_bridge(_FakeBridge())
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.get("/api/v1/locallink/p2p/status")
            assert response.status == 200
            assert (await response.json())["active"] is False

    @pytest.mark.asyncio
    async def test_aware_start_invalid_mode(self):
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post(
                "/api/v1/locallink/aware/start",
                json={"mode": "bogus"},
            )
            assert response.status == 400

    @pytest.mark.asyncio
    async def test_aware_start_success(self):
        android_locallink._aware = _FakeAware()
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post(
                "/api/v1/locallink/aware/start",
                json={"mode": "subscribe"},
            )
            assert response.status == 200
            assert (await response.json())["role"] == "subscribe"

    @pytest.mark.asyncio
    async def test_aware_status_route(self):
        android_locallink._aware = _FakeAware()
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.get("/api/v1/locallink/aware/status")
            assert response.status == 200
            data = await response.json()
            assert data["supported"] is True
            assert data["role"] == "off"

    @pytest.mark.asyncio
    async def test_nfc_share_payload_too_large(self):
        android_locallink._nfc = _FakeNfc()
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post(
                "/api/v1/locallink/nfc/share",
                json={"payload": "x" * 513},
            )
            assert response.status == 400

    @pytest.mark.asyncio
    async def test_nfc_share_success(self):
        android_locallink._nfc = _FakeNfc()
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post(
                "/api/v1/locallink/nfc/share",
                json={"payload": "meshchatx://share?k=v"},
            )
            assert response.status == 200
            data = await response.json()
            assert data["sharing"] is True

    @pytest.mark.asyncio
    async def test_nfc_read_lifecycle_routes(self):
        android_locallink._nfc = _FakeNfc()
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.post("/api/v1/locallink/nfc/read/start")
            assert response.status == 200
            assert (await response.json())["reading"] is True
            response = await client.post("/api/v1/locallink/nfc/read/stop")
            assert response.status == 200
            assert (await response.json())["reading"] is False

    @pytest.mark.asyncio
    async def test_nfc_status_route(self):
        android_locallink._nfc = _FakeNfc()
        async with TestClient(TestServer(_make_app())) as client:
            response = await client.get("/api/v1/locallink/nfc/status")
            assert response.status == 200
            data = await response.json()
            assert data["supported"] is True
            assert data["sharing"] is False


# ---------------------------------------------------------------------------
# Bug-hunt oracles
# ---------------------------------------------------------------------------


class _FakeJavaModule:
    """Minimal stand-in for Chaquopy's java module."""

    class _ProxyBase:
        pass

    class _LinkCls:
        def __init__(self, proxy):
            self.proxy = proxy

        @staticmethod
        def setAppContext(activity):
            _FakeJavaModule.app_context = activity

        @staticmethod
        def getAppContext():
            return _FakeJavaModule.app_context

    class _AwareCls:
        instance = None

        def __init__(self, context, proxy):
            self.context = context
            self.proxy = proxy
            _FakeJavaModule._AwareCls.instance = self

    class _NfcCls:
        def __init__(self, activity, proxy):
            self.activity = activity
            self.proxy = proxy

    app_context = None

    @staticmethod
    def dynamic_proxy(iface):
        return _FakeJavaModule._ProxyBase

    @staticmethod
    def jclass(name):
        return {
            "org.meshchatx.locallink.LocalLink": _FakeJavaModule._LinkCls,
            "org.meshchatx.locallink.PythonLocalLink": object,
            "org.meshchatx.locallink.AwareSession": _FakeJavaModule._AwareCls,
            "org.meshchatx.locallink.PythonAware": object,
            "org.meshchatx.locallink.NfcShare": _FakeJavaModule._NfcCls,
            "org.meshchatx.locallink.PythonNfc": object,
        }[name]


def _install_fake_java(monkeypatch):
    import sys
    import types

    module = types.ModuleType("java")
    module.dynamic_proxy = _FakeJavaModule.dynamic_proxy
    module.jclass = _FakeJavaModule.jclass
    monkeypatch.setitem(sys.modules, "java", module)


def test_install_resets_stale_bridges(monkeypatch):
    """Reinstall drops nfc and aware bridges bound to the dead Activity."""
    _install_fake_java(monkeypatch)
    android_locallink._nfc = object()
    android_locallink._aware = object()
    assert android_locallink.install_android_locallink(object()) is True
    assert android_locallink._nfc is None
    assert android_locallink._aware is None


def test_aware_session_lost_reaches_listeners(monkeypatch):
    """on_aware_event("session_lost") reaches listeners as session_lost."""
    _install_fake_java(monkeypatch)
    android_locallink.install_android_locallink(object())
    events = []
    android_locallink.register_aware_listener(
        lambda event, peer_id, data: events.append((event, peer_id, data))
    )
    aware = android_locallink._aware_bridge()
    assert aware is not None
    aware.proxy.on_aware_event("session_lost")
    assert ("session_lost", 0, None) in events


def test_aware_event_names_dispatch_verbatim(monkeypatch):
    """Lifecycle names pass to listeners verbatim, not wrapped as event."""
    _install_fake_java(monkeypatch)
    android_locallink.install_android_locallink(object())
    events = []
    android_locallink.register_aware_listener(
        lambda event, peer_id, data: events.append(event)
    )
    aware = android_locallink._aware_bridge()
    for what in ("attached", "publish_started", "stopped"):
        aware.proxy.on_aware_event(what)
    assert events == ["attached", "publish_started", "stopped"]


def test_aware_peer_session_lost_detaches(monkeypatch):
    """AwareInterface detaches when the session_lost event arrives."""
    import types

    locallink = types.ModuleType("fake_locallink")
    locallink.is_available = lambda: True
    locallink.aware_start = lambda role: {"ok": True, "role": role}
    listener_box = []
    locallink.register_aware_listener = listener_box.append
    locallink.unregister_aware_listener = lambda fn: None
    locallink.aware_stop = lambda: {"ok": True}
    locallink.aware_close_peer = lambda pid: None

    import meshchatx.src.backend as backend_pkg

    monkeypatch.setattr(backend_pkg, "android_locallink", locallink)
    monkeypatch.setattr(
        "RNS.Reticulum.get_instance", lambda: MagicMock(), raising=False
    )

    from meshchatx.src.backend.data.interfaces import AwareInterface

    config = {"name": "aware", "mode": "subscribe"}
    iface = AwareInterface.AwareInterface(
        owner=MagicMock(),
        configuration={"WiFi Aware": config, "name": "WiFi Aware"},
    )
    listener = listener_box[0]
    listener("session_lost", 0, None)
    assert iface.detached is True
    assert iface.online is False


def test_aware_spawn_peer_is_atomic(monkeypatch):
    """Concurrent link_up for one peer_id spawns exactly one interface."""
    import threading

    module = AwareModule = __import__(
        "meshchatx.src.backend.data.interfaces.AwareInterface",
        fromlist=["AwareInterface", "AwarePeerInterface"],
    )

    spawned = []
    barrier = threading.Event()

    class _SlowPeer:
        def __init__(self, owner, locallink, peer_id):
            self.owner = owner
            self.peer_id = peer_id
            self.online = False
            spawned.append(self)

        def optimise_mtu(self):
            # The window between construction and the peers-dict append is
            # where a second link_up for the same peer can slip in.
            barrier.wait(5)

        def teardown(self):
            pass

    monkeypatch.setattr(module, "AwarePeerInterface", _SlowPeer)
    monkeypatch.setattr(
        "RNS.Transport.add_interface", lambda iface: None, raising=False
    )

    iface = AwareModule.AwareInterface.__new__(AwareModule.AwareInterface)
    iface.owner = MagicMock()
    iface._locallink = MagicMock()
    iface.spawned_interfaces = []
    iface.peers = {}
    iface._lock = threading.Lock()
    iface._spawning = set()
    iface.detached = False
    iface.max_peers = 4
    iface.ingress_control = False
    iface.ic_max_held_announces = 0
    iface.ic_burst_hold = 0
    iface.ic_burst_freq = 0
    iface.ic_burst_freq_new = 0
    iface.ic_new_time = 0
    iface.ic_burst_penalty = 0
    iface.ic_held_release_interval = 0
    iface.egress_control = False
    iface.ec_pr_freq = 0
    iface.ic_pr_burst_freq_new = 0
    iface.ic_pr_burst_freq = 0
    iface.mode = 0
    iface.gravity = 0
    iface.bitrate = 0
    iface.HW_MTU = 500
    iface.ifac_size = None
    iface.ifac_netname = None
    iface.ifac_netkey = None

    threads = [threading.Thread(target=iface._spawn_peer, args=(7,)) for _ in range(4)]
    for t in threads:
        t.start()
    barrier.set()
    for t in threads:
        t.join()

    assert len(spawned) == 1
    assert len(iface.spawned_interfaces) == 1
    assert list(iface.peers) == [7]


def test_validate_join_ssid_byte_length():
    """SSID length is a byte limit (IEEE), not a character count."""
    from meshchatx.src.backend.http.routes.locallink import _validate_join_params

    # 17 chars of a 2-byte UTF-8 char = 34 bytes > 32
    _, _, err = _validate_join_params({"ssid": "é" * 17})
    assert err is not None
    # 16 chars = 32 bytes: at the limit, must pass
    ssid, _, err = _validate_join_params({"ssid": "é" * 16})
    assert err is None and ssid == "é" * 16
