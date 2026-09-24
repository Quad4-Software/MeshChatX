# SPDX-License-Identifier: 0BSD

"""Unit tests for the patched BLE transport and bt:// translation.

The BLE tests drive MeshChatBLEConnection with fake bleak devices/clients
so no real Bluetooth adapter is needed. They pin the regressions fixed
relative to stock RNS 1.5.4: macOS bond detection, transient scan errors,
connected-flag timing, and deliberate-vs-unexpected disconnect handling.
"""

import asyncio
import threading
import time

import pytest

from meshchatx.src.backend import rns_rnode_patch
from meshchatx.src.backend.rns_rnode_patch import (
    MeshChatBLEConnection,
    _resolve_bt_port_value,
)


class _FakeDevice:
    def __init__(self, name=None, address=None, details=None):
        self.name = name
        self.address = address
        self.details = details


def _ble_connection(**attrs):
    """A MeshChatBLEConnection without running __init__/threads."""
    conn = MeshChatBLEConnection.__new__(MeshChatBLEConnection)
    conn.owner = attrs.get("owner")
    conn.target_name = attrs.get("target_name")
    conn.target_bt_addr = attrs.get("target_bt_addr")
    conn.scan_timeout = 0.01
    conn.ble_device = None
    conn.last_client = None
    conn.connected = False
    conn.running = False
    conn.should_run = True
    conn.must_disconnect = False
    conn.connect_job_running = False
    conn.device_disappeared = False
    conn.loop = asyncio.new_event_loop()
    conn._windows_paired_addrs = attrs.get("windows_paired_addrs")
    return conn


def test_device_bonded_bluez_dict():
    conn = _ble_connection()
    try:
        bonded = _FakeDevice(details={"props": {"Bonded": True}})
        unbonded = _FakeDevice(details={"props": {"Bonded": False}})
        no_props = _FakeDevice(details={})
        assert conn.device_bonded(bonded) is True
        assert conn.device_bonded(unbonded) is False
        assert conn.device_bonded(no_props) is True
    finally:
        conn.loop.close()


def test_device_bonded_corebluetooth_tuple():
    """MacOS devices must count as bonded.

    CoreBluetooth exposes details as a tuple, not BlueZ props. Upstream
    returned False and BLE could never connect there.
    """
    conn = _ble_connection()
    try:
        device = _FakeDevice(details=("cb-tuple", object()))
        assert conn.device_bonded(device) is True
        assert conn.device_bonded(_FakeDevice(details=None)) is True
    finally:
        conn.loop.close()


def test_device_bonded_windows_paired_set():
    conn = _ble_connection(windows_paired_addrs={"aa:bb:cc:dd:ee:ff"})
    try:
        paired = _FakeDevice(address="AA:BB:CC:DD:EE:FF")
        unpaired = _FakeDevice(address="00:11:22:33:44:55")
        assert conn.device_bonded(paired) is True
        assert conn.device_bonded(unpaired) is False
    finally:
        conn.loop.close()


def test_find_target_device_transient_scan_error_does_not_kill():
    """A scan failure must not kill the connection job.

    Upstream set should_run=False on any scan error, permanently stopping
    the retry loop.
    """

    class FailingScanner:
        @staticmethod
        async def find_device_by_filter(*a, **k):
            raise RuntimeError("adapter busy")

    class FakeBleak:
        BleakScanner = FailingScanner

        class backends:
            class device:
                BLEDevice = _FakeDevice

            class scanner:
                AdvertisementData = object

    conn = _ble_connection()
    conn.bleak = FakeBleak
    conn.asyncio = asyncio
    try:
        result = conn.find_target_device()
        assert result is None
        assert conn.should_run is True
    finally:
        conn.loop.close()


def test_device_disconnected_marks_disappeared_only_when_unexpected():
    conn = _ble_connection()
    try:
        conn.device_disconnected(_FakeDevice())
        assert conn.device_disappeared is True

        conn = _ble_connection()
        conn.connected = True
        conn.must_disconnect = True
        conn.device_disconnected(_FakeDevice())
        assert conn.device_disappeared is False
        assert conn.connected is False
    finally:
        conn.loop.close()


def test_connected_flag_waits_for_services_and_notify():
    """Connected must flip only after service discovery + start_notify."""
    events = []

    class FakeCharacteristic:
        max_write_without_response_size = 20

    class FakeService:
        def get_characteristic(self, _uuid):
            return FakeCharacteristic()

    class FakeServices:
        def get_service(self, _uuid):
            return FakeService()

    class FakeBleakClient:
        def __init__(self, device, disconnected_callback=None):
            self.address = "AA:BB:CC:DD:EE:FF"
            self.services = FakeServices()
            self._disconnected_callback = disconnected_callback

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            if self._disconnected_callback:
                self._disconnected_callback(self)

        async def start_notify(self, _uuid, _cb):
            events.append(("start_notify", conn.connected))

        async def write_gatt_char(self, *a, **k):
            pass

        async def disconnect(self):
            events.append(("disconnect", None))
            # Real bleak fires the disconnected callback, which flips
            # conn.connected False and lets the write loop exit.
            if self._disconnected_callback:
                self._disconnected_callback(self)

    class FakeBleak:
        BleakClient = FakeBleakClient

        class backends:
            class device:
                BLEDevice = _FakeDevice

    class _Owner:
        port = ""
        ble_rx_queue = b""
        ble_tx_queue = b""
        ble_rx_lock = threading.Lock()
        ble_tx_lock = threading.Lock()

        def ble_waiting(self):
            return False

        def get_ble_waiting(self, _n):
            return b""

        def ble_receive(self, data):
            pass

    conn = _ble_connection(owner=_Owner())
    conn.bleak = FakeBleak
    conn.asyncio = asyncio
    conn.ble_device = _FakeDevice()
    try:
        # Flip must_disconnect shortly after connect so the write loop exits.
        def stop_soon():
            deadline = time.time() + 5
            while not conn.connected and time.time() < deadline:
                time.sleep(0.02)
            conn.must_disconnect = True

        threading.Thread(target=stop_soon, daemon=True).start()
        conn.connect_device()

        assert events[0] == ("start_notify", False), events
        assert ("disconnect", None) in events
    finally:
        conn.loop.close()


def test_missing_bleak_raises_ioerror_not_panic(monkeypatch):
    monkeypatch.setattr(MeshChatBLEConnection, "bleak", None)
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    with pytest.raises(IOError, match="bleak"):
        MeshChatBLEConnection()


def test_resolve_bt_port_value_resolves_scheme(monkeypatch):
    monkeypatch.setattr(
        "meshchatx.src.backend.bt_serial_ports.resolve_bt_target",
        lambda target, ports=None: f"RESOLVED:{target}",
    )
    assert _resolve_bt_port_value("bt://MyRNode") == "RESOLVED:MyRNode"
    assert _resolve_bt_port_value("ble://aa:bb") is None
    assert _resolve_bt_port_value("/dev/ttyUSB0") is None
    assert _resolve_bt_port_value(None) is None


def test_resolve_bt_port_value_propagates_failure(monkeypatch):
    def _fail(target, ports=None):
        raise OSError("no ports")

    monkeypatch.setattr(
        "meshchatx.src.backend.bt_serial_ports.resolve_bt_target",
        _fail,
    )
    with pytest.raises(OSError, match="no ports"):
        _resolve_bt_port_value("bt://MyRNode")


def test_install_patches_module_attrs(monkeypatch):
    monkeypatch.setattr(rns_rnode_patch, "_PATCHED", False)
    from RNS.Interfaces import RNodeInterface as rnode_module

    original = rnode_module.RNodeInterface
    assert rns_rnode_patch.install_rns_rnode_patches() is True
    assert rnode_module.BLEConnection is MeshChatBLEConnection
    assert issubclass(rnode_module.RNodeInterface, original)
