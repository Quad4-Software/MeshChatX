# SPDX-License-Identifier: 0BSD

"""RNode USB serial / BLE UART support checks for desktop and Android."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _is_chaquopy_android() -> bool:
    try:
        from meshchatx.android_push_bridge import _is_chaquopy_android as _check

        return _check()
    except ImportError:
        return False


def android_usbserial4a_available() -> bool:
    """True when Chaquopy can import usbserial4a (RNS RNode on Android)."""
    if not _is_chaquopy_android():
        return False
    try:
        import usbserial4a  # noqa: F401
    except ImportError:
        return False
    return True


def desktop_serial_stack_available() -> bool:
    try:
        from serial.tools import list_ports  # noqa: F401
    except ImportError:
        return False
    return True


def rnode_serial_supported() -> bool:
    """Whether RNode serial and ble:// UART ports can be opened on this platform."""
    if _is_chaquopy_android():
        return android_usbserial4a_available()
    return desktop_serial_stack_available()


def disable_rnode_interfaces_in_config(config_path: str) -> bool:
    """Disable enabled RNode* interfaces in a Reticulum config file.

    Returns True if any interfaces were disabled.
    """
    import os

    if not os.path.isfile(config_path):
        return False
    try:
        from RNS.vendor.configobj import ConfigObj

        cfg = ConfigObj(config_path)
    except Exception:
        return False

    modified = False
    interfaces = cfg.get("interfaces")
    if not isinstance(interfaces, dict):
        return False
    for _iface_name, iface in interfaces.items():
        if not isinstance(iface, dict):
            continue
        iface_type = iface.get("type", "")
        if isinstance(iface_type, str) and iface_type.startswith("RNode"):
            if str(iface.get("interface_enabled", "")).lower() in (
                "true",
                "yes",
                "1",
                "on",
            ):
                iface["interface_enabled"] = "false"
                modified = True
    if modified:
        try:
            cfg.write()
        except Exception:
            pass
    return modified


def guard_rnode_interfaces_on_android(config_path: str) -> bool:
    """On Android without usbserial4a, disable RNode interfaces to avoid startup crashes."""
    if not _is_chaquopy_android():
        return False
    if rnode_serial_supported():
        return False
    disabled = disable_rnode_interfaces_in_config(config_path)
    if disabled:
        logger.warning(
            "RNode interfaces were disabled because usbserial4a is not installed. "
            "Rebuild the Android app with usbserial4a or remove RNode entries from config.",
        )
    return disabled
