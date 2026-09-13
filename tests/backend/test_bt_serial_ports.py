# SPDX-License-Identifier: 0BSD

"""Unit tests for bt:// target resolution against fake port lists."""

import pytest

from meshchatx.src.backend.bt_serial_ports import (
    BtSerialPort,
    _hwid_mac,
    _looks_like_port,
    _normalize_mac,
    resolve_bt_target,
)


def _ports():
    return [
        BtSerialPort(
            device="COM5",
            name="Standard Serial over Bluetooth link (RNode A123)",
            address="aabbccddeeff",
        ),
        BtSerialPort(
            device="COM9",
            name="Standard Serial over Bluetooth link (RNode B456)",
            address="112233445566",
        ),
    ]


def test_normalize_mac_accepts_common_forms():
    assert _normalize_mac("aa:bb:cc:dd:ee:ff") == "aabbccddeeff"
    assert _normalize_mac("AA-BB-CC-DD-EE-FF") == "aabbccddeeff"
    assert _normalize_mac("AABBCCDDEEFF") == "aabbccddeeff"
    assert _normalize_mac("not-a-mac") is None
    assert _normalize_mac("") is None


def test_looks_like_port():
    assert _looks_like_port("COM7")
    assert _looks_like_port("/dev/rfcomm0")
    assert _looks_like_port("/dev/cu.RNode-SPPDev")
    assert not _looks_like_port("MyRNode")


def test_hwid_mac_extracts_from_windows_hwid():
    hwid = (
        r"BTHENUM\{00001101-0000-1000-8000-00805f9b34fb}_VID&00010075"
        r"_PID&0100\7&1234ABCD&0&AABBCCDDEEFF_C00000000"
    )
    assert _hwid_mac(hwid) == "aabbccddeeff"
    assert _hwid_mac("USB\\VID_1234") is None


def test_resolve_empty_auto_picks_single_port():
    ports = [BtSerialPort(device="COM5", name="RNode A123")]
    assert resolve_bt_target("", ports=ports) == "COM5"
    assert resolve_bt_target(None, ports=ports) == "COM5"


def test_resolve_empty_errors_without_ports():
    with pytest.raises(IOError, match="No Bluetooth serial ports"):
        resolve_bt_target("", ports=[])


def test_resolve_empty_errors_when_ambiguous():
    with pytest.raises(IOError, match="Multiple Bluetooth serial ports"):
        resolve_bt_target("", ports=_ports())


def test_resolve_explicit_port_passthrough():
    assert resolve_bt_target("COM7", ports=[]) == "COM7"
    assert resolve_bt_target("/dev/rfcomm0", ports=[]) == "/dev/rfcomm0"


def test_resolve_by_mac():
    assert resolve_bt_target("aa:bb:cc:dd:ee:ff", ports=_ports()) == "COM5"
    assert resolve_bt_target("AABBCCDDEEFF", ports=_ports()) == "COM5"


def test_resolve_by_mac_missing_device():
    with pytest.raises(IOError, match="No Bluetooth serial port found"):
        resolve_bt_target("00:11:22:33:44:55", ports=_ports())


def test_resolve_by_name_exact_and_partial():
    assert resolve_bt_target("RNode A123", ports=_ports()) == "COM5"
    # partial match
    assert resolve_bt_target("b456", ports=_ports()) == "COM9"


def test_resolve_by_name_unknown():
    with pytest.raises(IOError, match='No Bluetooth serial port matches "nope"'):
        resolve_bt_target("nope", ports=_ports())
