# SPDX-License-Identifier: 0BSD

"""List host serial ports for the interface editor without 500ing the API."""

from __future__ import annotations

import glob
import logging
import sys

from serial.tools import list_ports

logger = logging.getLogger(__name__)

# USB/CDC/ARM/Bluetooth globs covering pyserial list_ports_linux plus ttyWCH*
# (CH340/CH341 adapters, which pyserial never lists). ttyS* is omitted on
# purpose: unused 8250 nodes survive pyserial's platform filter on modern
# kernels (subsystem serial-base) and are not RNodes.
_FALLBACK_GLOBS = (
    "/dev/ttyUSB*",
    "/dev/ttyXRUSB*",
    "/dev/ttyACM*",
    "/dev/ttyAMA*",
    "/dev/ttyWCH*",
    "/dev/rfcomm*",
)


def _port_payload(device, product=None, serial_number=None) -> dict:
    return {
        "device": device,
        "product": product,
        "serial_number": serial_number,
    }


def _glob_usb_like_comports() -> list[dict]:
    seen: set[str] = set()
    ports: list[dict] = []
    for pattern in _FALLBACK_GLOBS:
        for device in glob.glob(pattern):
            if device in seen:
                continue
            seen.add(device)
            ports.append(_port_payload(device))
    return ports


# Vendor IDs usbserial4a's get_serial_port maps to a dedicated driver. Any
# other device is attempted as CDC-ACM, so class 0x02/0x0A interfaces are the
# remaining signal that a device can plausibly carry a serial port.
_ANDROID_SERIAL_VENDOR_IDS = frozenset({0x0403, 0x10C4, 0x1A86, 0x067B})
_CDC_USB_CLASSES = frozenset({2, 10})


def _is_android() -> bool:
    return hasattr(sys, "getandroidapilevel")


def _android_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _android_str(value):
    if value is None:
        return None
    return str(value)


def _android_serial_vid_pids() -> frozenset | None:
    """(vid, pid) pairs usbserial4a has a dedicated driver for.

    get_serial_port also honours these cross-vendor pairs on top of the four
    bare vendor IDs. Returns None when usbserial4a is not importable so the
    caller falls back to the vendor-ID check alone.
    """
    try:
        from usbserial4a import vidpid4a
    except Exception:
        return None
    pairs = set()
    for name in (
        "FTDI_VID_PID_GROUP",
        "SILABS_VID_PID_GROUP",
        "QINHENG_VID_PID_GROUP",
        "PROLIFIC_VID_PID_GROUP",
    ):
        pairs.update(getattr(vidpid4a, name, None) or ())
    return frozenset(pairs)


def _usb_device_has_cdc_class(device) -> bool:
    try:
        if _android_int(device.getDeviceClass()) == 2:
            return True
    except Exception:
        pass
    try:
        interface_count = int(device.getInterfaceCount())
    except Exception:
        return False
    for index in range(interface_count):
        try:
            interface = device.getInterface(index)
            if _android_int(interface.getInterfaceClass()) in _CDC_USB_CLASSES:
                return True
        except Exception:
            continue
    return False


def _usb_device_is_serial(device, serial_vid_pids=None) -> bool:
    try:
        vendor_id = _android_int(device.getVendorId())
        product_id = _android_int(device.getProductId())
    except Exception:
        vendor_id = product_id = None
    if vendor_id in _ANDROID_SERIAL_VENDOR_IDS:
        return True
    if serial_vid_pids and (vendor_id, product_id) in serial_vid_pids:
        return True
    return _usb_device_has_cdc_class(device)


def _android_port_payload(device, usb4a_usb) -> dict | None:
    try:
        device_name = _android_str(device.getDeviceName())
    except Exception:
        return None
    if not device_name:
        return None
    try:
        product = _android_str(device.getProductName())
    except Exception:
        product = None
    payload = _port_payload(device_name, product=product)
    try:
        vendor_id = _android_int(device.getVendorId())
        product_id = _android_int(device.getProductId())
    except Exception:
        vendor_id = product_id = None
    if vendor_id is not None:
        payload["vendor_id"] = vendor_id
    if product_id is not None:
        payload["product_id"] = product_id
    try:
        payload["has_permission"] = bool(usb4a_usb.has_usb_permission(device))
    except Exception:
        payload["has_permission"] = False
    if payload["has_permission"]:
        try:
            serial_number = _android_str(device.getSerialNumber())
        except Exception:
            serial_number = None
        if serial_number:
            payload["serial_number"] = serial_number
    return payload


def _android_usb_serial_comports() -> list[dict] | None:
    """USB serial devices visible to UsbManager on Android.

    Returns None when the usb4a bridge cannot be imported so the caller can
    fall back to the desktop enumeration path.
    """
    try:
        from usb4a import usb as usb4a_usb
    except Exception:
        return None
    try:
        devices = usb4a_usb.get_usb_device_list()
    except Exception as exc:
        logger.warning("usb4a USB device enumeration failed: %s", exc)
        return []
    serial_vid_pids = _android_serial_vid_pids()
    ports = []
    for device in devices or []:
        if device is None or not _usb_device_is_serial(device, serial_vid_pids):
            continue
        payload = _android_port_payload(device, usb4a_usb)
        if payload is not None:
            ports.append(payload)
    return ports


def request_android_usb_permission(device_name: str) -> dict:
    """Ask Android for USB permission on a device name like /dev/bus/usb/001/002.

    Returns a status dict for the HTTP layer and never raises for expected
    failure modes.
    """
    if not _is_android():
        return {"ok": False, "error": "not_android"}
    try:
        from usb4a import usb as usb4a_usb
    except Exception:
        return {"ok": False, "error": "usb_unavailable"}
    try:
        device = usb4a_usb.get_usb_device(str(device_name))
    except Exception:
        device = None
    if device is None:
        return {"ok": False, "error": "device_not_found"}
    try:
        if usb4a_usb.has_usb_permission(device):
            return {"ok": True, "granted": True, "requested": False}
    except Exception:
        pass
    try:
        usb4a_usb.request_usb_permission(device)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "granted": False, "requested": True}


def list_serial_comports() -> list[dict]:
    """Return serial ports for GET /api/v1/comports.

    pyserial's Linux SysFS helper stats /sys/class/tty/<name>/device (allowed
    under Landlock without a /sys read rule) then open()s idVendor (denied).
    read_line returns None and int(None, 16) raises TypeError, which used to
    500 the whole endpoint whenever a USB serial device was present.

    On Android there is no /sys/class/tty or /dev/tty* view of USB devices;
    serial ports are UsbManager devices addressed by /dev/bus/usb/... names,
    so enumeration goes through the usb4a bridge instead.
    """
    if _is_android():
        android_ports = _android_usb_serial_comports()
        if android_ports is not None:
            return android_ports
    try:
        ports = [
            _port_payload(
                comport.device,
                product=comport.product,
                serial_number=comport.serial_number,
            )
            for comport in list_ports.comports()
        ]
    except (TypeError, ValueError, OSError) as exc:
        logger.warning(
            "list_ports.comports failed (%s), falling back to USB-like device glob",
            exc,
        )
        ports = []
    seen = {port["device"] for port in ports}
    for port in _glob_usb_like_comports():
        if port["device"] not in seen:
            ports.append(port)
    return ports
