# SPDX-License-Identifier: 0BSD

"""Resolve bt:// RNode targets to platform serial ports.

RNS's desktop RNodeInterface has no native classic-Bluetooth transport. A
paired RNode reaches it as a serial port instead: a Windows outgoing SPP COM
port ("Standard Serial over Bluetooth link"), a macOS /dev/cu.*-SPPDev or
/dev/cu.<name>-SerialPort device, or a Linux /dev/rfcomm* node. This module
enumerates those ports and translates a bt:// target (device name, MAC
address, or empty for auto-pick) into the serial port RNS can open.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_BT_MAC_RE = re.compile(r"^(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}$")
_BT_MAC_BARE_RE = re.compile(r"^[0-9a-fA-F]{12}$")
# Windows pyserial hwids for SPP ports look like
# BTHENUM\{00001101-...\}_...\8&XXXX&0&AABBCCDDEEFF_C00000000
# where the 12-hex token is the remote device MAC.
_HWID_MAC_RE = re.compile(r"[&\\]([0-9a-fA-F]{12})[_&]")
_COM_PORT_RE = re.compile(r"^COM\d{1,3}$", re.IGNORECASE)


@dataclass
class BtSerialPort:
    """A Bluetooth SPP serial port candidate."""

    device: str
    name: str = ""
    address: str | None = None


def _normalize_mac(value: str) -> str | None:
    stripped = value.strip()
    if _BT_MAC_RE.match(stripped):
        return stripped.replace(":", "").replace("-", "").lower()
    if _BT_MAC_BARE_RE.match(stripped):
        return stripped.lower()
    return None


def _looks_like_port(target: str) -> bool:
    if _COM_PORT_RE.match(target):
        return True
    return target.startswith("/dev/")


def _windows_bt_device_names() -> dict[str, str]:
    """Map paired BT device MAC -> friendly name from the Windows registry."""
    if sys.platform != "win32":
        return {}
    try:
        import winreg
    except ImportError:
        return {}
    names: dict[str, str] = {}
    try:
        key_path = r"SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as devices:
            for i in range(winreg.QueryInfoKey(devices)[0]):
                subkey_name = winreg.EnumKey(devices, i)
                mac = _normalize_mac(subkey_name)
                if mac is None:
                    continue
                try:
                    with winreg.OpenKey(devices, subkey_name) as dev:
                        raw, _kind = winreg.QueryValueEx(dev, "Name")
                except OSError:
                    continue
                if isinstance(raw, bytes):
                    name = raw.decode("utf-8", errors="replace").rstrip("\x00")
                else:
                    name = str(raw)
                if name:
                    names[mac] = name
    except OSError:
        return names
    return names


def _hwid_mac(hwid: str) -> str | None:
    matches = _HWID_MAC_RE.findall(hwid or "")
    if not matches:
        return None
    return matches[-1].lower()


def _is_windows_bt_port(port) -> bool:
    return "BTHENUM" in str(getattr(port, "hwid", "") or "").upper()


def _is_macos_bt_port(port) -> bool:
    device = str(getattr(port, "device", "") or "")
    description = str(getattr(port, "description", "") or "")
    hwid = str(getattr(port, "hwid", "") or "")
    if not device.startswith("/dev/cu."):
        return False
    haystack = f"{device} {description} {hwid}".lower()
    if "bluetooth-incoming-port" in haystack:
        return False
    return "bluetooth" in haystack or "-spp" in haystack or "-serialport" in haystack


def _is_linux_bt_port(port) -> bool:
    device = str(getattr(port, "device", "") or "")
    return os.path.basename(device).startswith("rfcomm")


def list_bluetooth_serial_ports(comports=None) -> list[BtSerialPort]:
    """Enumerate Bluetooth SPP serial ports visible on this host.

    Returns BtSerialPort entries with a best-effort friendly name and remote
    device MAC where the platform exposes them. *comports* is injectable for
    tests; when None, serial.tools.list_ports is used.
    """
    if comports is None:
        try:
            from serial.tools import list_ports
        except ImportError:
            return []
        try:
            comports = list(list_ports.comports())
        except Exception as e:
            logger.warning("Could not enumerate serial ports: %s", e)
            return []

    if sys.platform == "win32":
        classifier = _is_windows_bt_port
    elif sys.platform == "darwin":
        classifier = _is_macos_bt_port
    else:
        classifier = _is_linux_bt_port

    name_map = _windows_bt_device_names()
    results: list[BtSerialPort] = []
    for port in comports:
        try:
            if not classifier(port):
                continue
        except Exception:
            continue
        device = str(getattr(port, "device", "") or "")
        description = str(getattr(port, "description", "") or "")
        address = _hwid_mac(str(getattr(port, "hwid", "") or ""))
        name = name_map.get(address) if address else None
        if not name:
            name = description or device
        results.append(BtSerialPort(device=device, name=name, address=address))
    return results


def _describe_candidates(ports: list[BtSerialPort]) -> str:
    parts = []
    for p in ports:
        label = p.name or "unknown device"
        if p.address:
            label = f"{label} ({p.address})"
        parts.append(f"{p.device}: {label}")
    return "; ".join(parts)


def resolve_bt_target(target: str | None, ports=None) -> str:
    """Resolve a bt:// target to a serial port device path.

    *target* may be empty (auto-pick when exactly one BT serial port exists),
    an explicit port (COM7, /dev/rfcomm0, /dev/cu.*), a Bluetooth MAC
    address, or a paired device name. *ports* is injectable for tests.

    Raises IOError with actionable text when the target cannot be resolved.
    """
    if ports is None:
        ports = list_bluetooth_serial_ports()

    value = (target or "").strip()
    if not value:
        if len(ports) == 1:
            return ports[0].device
        if not ports:
            raise OSError(
                "No Bluetooth serial ports found. Pair the RNode first so the "
                "OS exposes a serial port for it: an outgoing COM port on "
                "Windows, a /dev/cu.* port on macOS, or /dev/rfcomm* on Linux."
            )
        raise OSError(
            "Multiple Bluetooth serial ports found, specify which one to use. "
            f"Available: {_describe_candidates(ports)}"
        )

    if _looks_like_port(value):
        return value

    mac = _normalize_mac(value)
    if mac is not None:
        for p in ports:
            if p.address and p.address.lower() == mac:
                return p.device
        raise OSError(
            f"No Bluetooth serial port found for device address {value}. "
            "Pair the device and make sure an outgoing serial port exists. "
            f"Available: {_describe_candidates(ports) or 'none'}"
        )

    lowered = value.lower()
    exact = [p for p in ports if (p.name or "").lower() == lowered]
    if len(exact) == 1:
        return exact[0].device
    partial = [
        p
        for p in ports
        if lowered in (p.name or "").lower() or lowered in p.device.lower()
    ]
    if len(partial) == 1:
        return partial[0].device
    candidates = exact + [p for p in partial if p not in exact]
    if not candidates:
        raise OSError(
            f'No Bluetooth serial port matches "{value}". '
            f"Available: {_describe_candidates(ports) or 'none'}"
        )
    raise OSError(
        f'Multiple Bluetooth serial ports match "{value}": '
        f"{_describe_candidates(candidates)}. Specify a MAC address instead."
    )
