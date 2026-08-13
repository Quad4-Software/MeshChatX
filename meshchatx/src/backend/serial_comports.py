# SPDX-License-Identifier: 0BSD

"""List host serial ports for the interface editor without 500ing the API."""

from __future__ import annotations

import glob
import logging

from serial.tools import list_ports

logger = logging.getLogger(__name__)

# Same USB/CDC/ARM/Bluetooth globs as pyserial list_ports_linux, minus ttyS*.
# ttyS* is omitted on purpose: unused 8250 nodes survive pyserial's platform
# filter on modern kernels (subsystem serial-base) and are not RNodes.
_FALLBACK_GLOBS = (
    "/dev/ttyUSB*",
    "/dev/ttyXRUSB*",
    "/dev/ttyACM*",
    "/dev/ttyAMA*",
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


def list_serial_comports() -> list[dict]:
    """Return serial ports for GET /api/v1/comports.

    pyserial's Linux SysFS helper stats /sys/class/tty/<name>/device (allowed
    under Landlock without a /sys read rule) then open()s idVendor (denied).
    read_line returns None and int(None, 16) raises TypeError, which used to
    500 the whole endpoint whenever a USB serial device was present.
    """
    try:
        return [
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
        return _glob_usb_like_comports()
