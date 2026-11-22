# SPDX-License-Identifier: 0BSD

"""Android USB serial enumeration for GET /api/v1/comports.

On Android there is no /dev/tty* view of USB serial adapters; devices are
UsbManager entries addressed by /dev/bus/usb/... names, enumerated through
the bundled usb4a bridge.
"""

from __future__ import annotations

import json
import sys
import types

import pytest
from aiohttp import web

from meshchatx.src.backend import serial_comports as sc
from meshchatx.src.backend.http.routes import interfaces as interfaces_routes


class FakeUsbInterface:
    def __init__(self, interface_class):
        self._interface_class = interface_class

    def getInterfaceClass(self):
        return self._interface_class


class FakeUsbDevice:
    def __init__(
        self,
        name,
        vendor_id,
        product_id,
        product_name=None,
        serial_number=None,
        device_class=0,
        interfaces=(),
    ):
        self._name = name
        self._vendor_id = vendor_id
        self._product_id = product_id
        self._product_name = product_name
        self._serial_number = serial_number
        self._device_class = device_class
        self._interfaces = list(interfaces)

    def getDeviceName(self):
        return self._name

    def getVendorId(self):
        return self._vendor_id

    def getProductId(self):
        return self._product_id

    def getProductName(self):
        return self._product_name

    def getSerialNumber(self):
        if self._serial_number is None:
            raise RuntimeError("no permission")
        return self._serial_number

    def getDeviceClass(self):
        return self._device_class

    def getInterfaceCount(self):
        return len(self._interfaces)

    def getInterface(self, index):
        return self._interfaces[index]


def install_fake_usb4a(monkeypatch, devices, permissions=None):
    """Register fake usb4a.usb module backed by *devices*."""
    permissions = permissions or {}
    requested = []

    usb4a_mod = types.ModuleType("usb4a")
    usb4a_usb = types.ModuleType("usb4a.usb")
    usb4a_usb.get_usb_device_list = lambda: list(devices)
    usb4a_usb.get_usb_device = lambda name: next(
        (d for d in devices if d.getDeviceName() == name),
        None,
    )
    usb4a_usb.has_usb_permission = lambda device: permissions.get(
        device.getDeviceName(),
        False,
    )

    def _request(device):
        requested.append(device.getDeviceName())

    usb4a_usb.request_usb_permission = _request
    usb4a_usb.requested = requested
    usb4a_mod.usb = usb4a_usb

    monkeypatch.setitem(sys.modules, "usb4a", usb4a_mod)
    monkeypatch.setitem(sys.modules, "usb4a.usb", usb4a_usb)
    return usb4a_usb


def install_fake_vidpid4a(monkeypatch, groups):
    """Register a fake usbserial4a.vidpid4a data module."""
    pkg = types.ModuleType("usbserial4a")
    vidpid4a = types.ModuleType("usbserial4a.vidpid4a")
    for name, pairs in groups.items():
        setattr(vidpid4a, name, pairs)
    pkg.vidpid4a = vidpid4a
    monkeypatch.setitem(sys.modules, "usbserial4a", pkg)
    monkeypatch.setitem(sys.modules, "usbserial4a.vidpid4a", vidpid4a)


@pytest.fixture
def android_env(monkeypatch):
    monkeypatch.setattr(sc, "_is_android", lambda: True)


def test_android_enumerates_serial_usb_devices(android_env, monkeypatch):
    rnode = FakeUsbDevice(
        "/dev/bus/usb/001/002",
        0x1915,
        0x520A,
        product_name="RNode LoRa Radio",
        serial_number="RND-0001",
        interfaces=[FakeUsbInterface(0x02), FakeUsbInterface(0x0A)],
    )
    cdc_only = FakeUsbDevice(
        "/dev/bus/usb/001/003",
        0x2E8A,
        0x000A,
        product_name="Serial adapter",
        device_class=0,
        interfaces=[FakeUsbInterface(0x02), FakeUsbInterface(0x0A)],
    )
    keyboard = FakeUsbDevice(
        "/dev/bus/usb/001/004",
        0x046D,
        0xC52B,
        product_name="Keyboard",
        device_class=0,
        interfaces=[FakeUsbInterface(0x03)],
    )
    install_fake_usb4a(
        monkeypatch,
        [rnode, cdc_only, keyboard],
        permissions={"/dev/bus/usb/001/002": True},
    )

    ports = sc.list_serial_comports()
    devices = {port["device"]: port for port in ports}

    assert set(devices) == {"/dev/bus/usb/001/002", "/dev/bus/usb/001/003"}
    assert devices["/dev/bus/usb/001/002"]["product"] == "RNode LoRa Radio"
    assert devices["/dev/bus/usb/001/002"]["serial_number"] == "RND-0001"
    assert devices["/dev/bus/usb/001/002"]["has_permission"] is True
    assert devices["/dev/bus/usb/001/002"]["vendor_id"] == 0x1915
    assert devices["/dev/bus/usb/001/003"]["has_permission"] is False
    assert devices["/dev/bus/usb/001/003"]["serial_number"] is None


def test_android_known_serial_vendor_without_cdc_class(android_env, monkeypatch):
    cp210x = FakeUsbDevice(
        "/dev/bus/usb/001/005",
        0x10C4,
        0xEA60,
        product_name="CP2102 USB to UART Bridge",
        device_class=0,
        interfaces=[FakeUsbInterface(0xFF)],
    )
    install_fake_usb4a(monkeypatch, [cp210x])

    ports = sc.list_serial_comports()
    assert [port["device"] for port in ports] == ["/dev/bus/usb/001/005"]


def test_android_device_class_two_counts_as_serial(android_env, monkeypatch):
    composite = FakeUsbDevice(
        "/dev/bus/usb/001/006",
        0x1234,
        0x5678,
        product_name="Composite",
        device_class=2,
    )
    install_fake_usb4a(monkeypatch, [composite])
    assert [p["device"] for p in sc.list_serial_comports()] == [
        "/dev/bus/usb/001/006",
    ]


def test_android_vid_pid_group_matches_dedicated_driver(android_env, monkeypatch):
    """usbserial4a's cross-vendor (vid, pid) pairs get a dedicated driver."""
    rebranded_ftdi = FakeUsbDevice(
        "/dev/bus/usb/001/007",
        0x03EB,
        0x2109,
        product_name="Rebranded FTDI",
        device_class=0,
        interfaces=[FakeUsbInterface(0xFF)],
    )
    install_fake_usb4a(monkeypatch, [rebranded_ftdi])
    install_fake_vidpid4a(
        monkeypatch,
        {"FTDI_VID_PID_GROUP": [(0x03EB, 0x2109)]},
    )
    assert [p["device"] for p in sc.list_serial_comports()] == [
        "/dev/bus/usb/001/007",
    ]


def test_android_vid_pid_group_miss_falls_back_to_cdc(android_env, monkeypatch):
    install_fake_vidpid4a(monkeypatch, {"FTDI_VID_PID_GROUP": [(0x03EB, 0x2109)]})
    cdc = FakeUsbDevice(
        "/dev/bus/usb/001/008",
        0x03EB,
        0x9999,
        product_name="Other",
        device_class=0,
        interfaces=[FakeUsbInterface(0x02)],
    )
    hid = FakeUsbDevice(
        "/dev/bus/usb/001/009",
        0x03EB,
        0x8888,
        product_name="HID",
        device_class=0,
        interfaces=[FakeUsbInterface(0x03)],
    )
    install_fake_usb4a(monkeypatch, [cdc, hid])
    assert [p["device"] for p in sc.list_serial_comports()] == [
        "/dev/bus/usb/001/008",
    ]


def test_android_empty_device_list_returns_empty(android_env, monkeypatch):
    install_fake_usb4a(monkeypatch, [])
    assert sc.list_serial_comports() == []


def test_android_falls_back_to_desktop_path_without_usb4a(android_env, monkeypatch):
    monkeypatch.setitem(sys.modules, "usb4a", None)
    monkeypatch.setitem(sys.modules, "usb4a.usb", None)
    monkeypatch.setattr(sc.list_ports, "comports", lambda: [])
    monkeypatch.setattr(sc.glob, "glob", lambda _pattern: [])
    assert sc.list_serial_comports() == []


def test_non_android_ignores_usb4a(monkeypatch):
    monkeypatch.setattr(sc, "_is_android", lambda: False)
    install_fake_usb4a(
        monkeypatch,
        [FakeUsbDevice("/dev/bus/usb/001/002", 0x1915, 0x520A)],
    )
    monkeypatch.setattr(sc.list_ports, "comports", lambda: [])
    monkeypatch.setattr(sc.glob, "glob", lambda _pattern: [])
    assert sc.list_serial_comports() == []


def test_request_usb_permission_not_android(monkeypatch):
    monkeypatch.setattr(sc, "_is_android", lambda: False)
    assert sc.request_android_usb_permission("/dev/bus/usb/001/002") == {
        "ok": False,
        "error": "not_android",
    }


def test_request_usb_permission_requests_when_missing(android_env, monkeypatch):
    device = FakeUsbDevice("/dev/bus/usb/001/002", 0x1915, 0x520A)
    usb4a_usb = install_fake_usb4a(
        monkeypatch,
        [device],
        permissions={},
    )
    result = sc.request_android_usb_permission("/dev/bus/usb/001/002")
    assert result == {"ok": True, "granted": False, "requested": True}
    assert usb4a_usb.requested == ["/dev/bus/usb/001/002"]


def test_request_usb_permission_reports_granted(android_env, monkeypatch):
    device = FakeUsbDevice("/dev/bus/usb/001/002", 0x1915, 0x520A)
    usb4a_usb = install_fake_usb4a(
        monkeypatch,
        [device],
        permissions={"/dev/bus/usb/001/002": True},
    )
    result = sc.request_android_usb_permission("/dev/bus/usb/001/002")
    assert result == {"ok": True, "granted": True, "requested": False}
    assert usb4a_usb.requested == []


def test_request_usb_permission_unknown_device(android_env, monkeypatch):
    install_fake_usb4a(monkeypatch, [])
    assert sc.request_android_usb_permission("/dev/bus/usb/009/009") == {
        "ok": False,
        "error": "device_not_found",
    }


def _comports_permission_handler():
    table = web.RouteTableDef()
    interfaces_routes.register_interfaces_routes(table, None)
    for route in table:
        if route.path == "/api/v1/comports/usb-permission" and route.method == "POST":
            return route.handler
    raise AssertionError("usb-permission route not registered")


class _JsonRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_usb_permission_route_returns_requested(monkeypatch):
    monkeypatch.setattr(
        interfaces_routes,
        "request_android_usb_permission",
        lambda device: {"ok": True, "granted": False, "requested": True},
    )
    handler = _comports_permission_handler()
    response = await handler(_JsonRequest({"device": "/dev/bus/usb/001/002"}))
    assert response.status == 200
    assert json.loads(response.body) == {
        "ok": True,
        "granted": False,
        "requested": True,
    }


@pytest.mark.asyncio
async def test_usb_permission_route_maps_errors(monkeypatch):
    handler = _comports_permission_handler()

    monkeypatch.setattr(
        interfaces_routes,
        "request_android_usb_permission",
        lambda device: {"ok": False, "error": "not_android"},
    )
    response = await handler(_JsonRequest({"device": "/dev/bus/usb/001/002"}))
    assert response.status == 400

    monkeypatch.setattr(
        interfaces_routes,
        "request_android_usb_permission",
        lambda device: {"ok": False, "error": "device_not_found"},
    )
    response = await handler(_JsonRequest({"device": "/dev/bus/usb/009/009"}))
    assert response.status == 404


@pytest.mark.asyncio
async def test_usb_permission_route_rejects_missing_device():
    handler = _comports_permission_handler()
    response = await handler(_JsonRequest({}))
    assert response.status == 422
