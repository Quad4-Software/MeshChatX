# SPDX-License-Identifier: 0BSD

"""Reference: /api/v1/comports must not 500 when pyserial SysFS hits Landlock."""

from __future__ import annotations

import pytest

from meshchatx.src.backend import serial_comports as sc

PYSERIAL_SYSFS_TYPEERROR = TypeError(
    "int() can't convert non-string with explicit base",
)


def test_fallback_globs_omit_ttys():
    assert not any("ttyS" in pattern for pattern in sc._FALLBACK_GLOBS)


def test_comports_typeerror_falls_back_to_usb_like_globs(monkeypatch):
    """Pyserial SysFS does int(None, 16) when idVendor open() is EACCES."""

    def boom():
        raise PYSERIAL_SYSFS_TYPEERROR

    monkeypatch.setattr(sc.list_ports, "comports", boom)

    def fake_glob(pattern):
        mapping = {
            "/dev/ttyUSB*": ["/dev/ttyUSB0"],
            "/dev/ttyACM*": ["/dev/ttyACM0"],
            "/dev/ttyS*": ["/dev/ttyS0", "/dev/ttyS1"],
        }
        return mapping.get(pattern, [])

    monkeypatch.setattr(sc.glob, "glob", fake_glob)
    ports = sc.list_serial_comports()
    devices = [port["device"] for port in ports]
    assert "/dev/ttyACM0" in devices
    assert "/dev/ttyUSB0" in devices
    assert "/dev/ttyS0" not in devices
    assert all("device" in port and "product" in port for port in ports)


def test_comports_oserror_falls_back_to_empty_when_no_usb_nodes(monkeypatch):
    def boom():
        raise OSError(13, "Permission denied")

    monkeypatch.setattr(sc.list_ports, "comports", boom)
    monkeypatch.setattr(sc.glob, "glob", lambda _pattern: [])
    assert sc.list_serial_comports() == []


def test_comports_success_keeps_pyserial_metadata(monkeypatch):
    class FakePort:
        def __init__(self):
            self.device = "/dev/ttyACM0"
            self.product = "RNode"
            self.serial_number = "ABC123"

    monkeypatch.setattr(sc.list_ports, "comports", lambda: [FakePort()])
    monkeypatch.setattr(sc.glob, "glob", lambda _pattern: [])
    assert sc.list_serial_comports() == [
        {
            "device": "/dev/ttyACM0",
            "product": "RNode",
            "serial_number": "ABC123",
        },
    ]


def test_comports_empty_pyserial_result_still_globs_usb_nodes(monkeypatch):
    """A successful-but-empty pyserial result must still glob USB nodes."""
    monkeypatch.setattr(sc.list_ports, "comports", lambda: [])

    def fake_glob(pattern):
        return {
            "/dev/ttyUSB*": ["/dev/ttyUSB0"],
            "/dev/ttyACM*": ["/dev/ttyACM0"],
        }.get(pattern, [])

    monkeypatch.setattr(sc.glob, "glob", fake_glob)
    devices = [port["device"] for port in sc.list_serial_comports()]
    assert devices == ["/dev/ttyUSB0", "/dev/ttyACM0"]


def test_comports_merges_glob_only_devices_without_duplicates(monkeypatch):
    """Glob-visible nodes pyserial misses (e.g. ttyWCH*) are appended."""

    class FakePort:
        device = "/dev/ttyACM0"
        product = "RNode"
        serial_number = "ABC123"

    monkeypatch.setattr(sc.list_ports, "comports", lambda: [FakePort()])

    def fake_glob(pattern):
        return {
            "/dev/ttyACM*": ["/dev/ttyACM0"],
            "/dev/ttyWCH*": ["/dev/ttyWCH0"],
        }.get(pattern, [])

    monkeypatch.setattr(sc.glob, "glob", fake_glob)
    ports = sc.list_serial_comports()
    assert ports == [
        {
            "device": "/dev/ttyACM0",
            "product": "RNode",
            "serial_number": "ABC123",
        },
        {"device": "/dev/ttyWCH0", "product": None, "serial_number": None},
    ]


@pytest.mark.parametrize(
    "exc",
    [
        TypeError("int() can't convert non-string with explicit base"),
        ValueError("invalid literal for int() with base 16: 'None'"),
        OSError(13, "Permission denied"),
    ],
)
def test_comports_never_raises_from_pyserial(monkeypatch, exc):
    def boom():
        raise exc

    monkeypatch.setattr(sc.list_ports, "comports", boom)
    monkeypatch.setattr(sc.glob, "glob", lambda _pattern: [])
    assert sc.list_serial_comports() == []
