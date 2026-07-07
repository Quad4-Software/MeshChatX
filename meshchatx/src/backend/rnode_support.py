# SPDX-License-Identifier: 0BSD

"""RNode USB serial / Bluetooth / BLE support checks for desktop and Android.

RNode over TCP ("RNode over IP") needs no native Android modules and works
unconditionally, since RNS's Android RNodeInterface is patched (see
scripts/build-android-wheels-local.sh) to stop hard-crashing the process when
usbserial4a/jnius are missing. Serial and classic-Bluetooth ports need
usbserial4a + jnius. BLE (ble://) ports need able. This module lets the rest
of the app tell which RNode config entries can actually be brought up on the
current build, so only the genuinely unsupported ones get disabled.
"""

from __future__ import annotations

import importlib.util
import logging

logger = logging.getLogger(__name__)

_TRUE_STRINGS = ("true", "yes", "1", "on")


def _optional_module_available(module_name: str) -> bool:
    """Return True when *module_name* can be resolved without importing it."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _is_chaquopy_android() -> bool:
    try:
        from meshchatx.android_push_bridge import _is_chaquopy_android as _check

        return _check()
    except ImportError:
        return False


def android_usbserial4a_available() -> bool:
    """True when usbserial4a can be imported (RNode serial/Bluetooth-classic on Android)."""
    return _optional_module_available("usbserial4a")


def android_jnius_available() -> bool:
    """True when jnius (pyjnius) can be imported.

    RNS's Android-specific RNodeInterface needs jnius for USB serial and
    classic Bluetooth (RFCOMM) access. Chaquopy does not ship pyjnius under
    the importable name "jnius" unless bundled explicitly (e.g. via a
    compatibility shim), so this is normally unavailable.
    """
    return _optional_module_available("jnius")


def android_able_available() -> bool:
    """True when able can be imported (BLE GATT support for RNode ble:// on Android)."""
    return _optional_module_available("able")


def desktop_serial_stack_available() -> bool:
    return _optional_module_available("serial.tools.list_ports")


def desktop_ble_stack_available() -> bool:
    return _optional_module_available("bleak")


def _is_rnode_tcp_config_type(iface_type: object) -> bool:
    return iface_type in ("RNodeInterface", "RNodeIPInterface")


def rnode_serial_supported() -> bool:
    """Whether RNode USB serial / classic-Bluetooth ports can be opened here.

    This does not cover RNode over TCP (always supported) or ble:// (covered
    by android_able_available() on Android).
    """
    if _is_chaquopy_android():
        return android_usbserial4a_available() and android_jnius_available()
    return desktop_serial_stack_available()


def _is_enabled(iface: dict) -> bool:
    for key in ("interface_enabled", "enabled"):
        if key in iface and str(iface.get(key, "")).lower() in _TRUE_STRINGS:
            return True
    return False


def rnode_port_is_tcp(port: object) -> bool:
    return str(port or "").strip().lower().startswith("tcp://")


def rnode_port_is_ble(port: object) -> bool:
    return str(port or "").strip().lower().startswith("ble://")


def _tcp_host_from_port(port: object) -> str | None:
    if not rnode_port_is_tcp(port):
        return None
    host_part = str(port).strip()[len("tcp://") :].strip().strip(":")
    if not host_part or set(host_part) <= {"/"}:
        return None
    return host_part


def _port_is_blank(port: object) -> bool:
    return not str(port or "").strip()


def _rnode_iface_transport(iface: dict) -> str:
    """Classify an RNodeInterface config entry's transport.

    Returns one of "tcp", "ble", "bluetooth_classic", or "serial".
    """
    port = iface.get("port")
    if rnode_port_is_tcp(port):
        return "tcp"
    if rnode_port_is_ble(port):
        return "ble"
    allow_bluetooth = str(iface.get("allow_bluetooth", "")).lower() in _TRUE_STRINGS
    if _port_is_blank(port) and allow_bluetooth:
        return "bluetooth_classic"
    return "serial"


def rnode_transport_supported(iface: dict, *, is_android: bool | None = None) -> bool:
    """Whether a specific RNodeInterface config entry can be brought up here.

    RNode over TCP always works. Serial and classic-Bluetooth need
    usbserial4a + jnius on Android. BLE needs able on Android. On desktop,
    serial and classic-Bluetooth rely on pyserial; BLE relies on bleak.

    ``is_android`` lets a caller that already determined the platform pass
    that result through explicitly, instead of re-detecting it here.
    """
    if is_android is None:
        is_android = _is_chaquopy_android()

    transport = _rnode_iface_transport(iface)
    if transport == "tcp":
        return True
    if is_android:
        if transport == "ble":
            return android_able_available()
        return android_usbserial4a_available() and android_jnius_available()
    if transport == "ble":
        return desktop_ble_stack_available()
    return desktop_serial_stack_available()


def normalize_rnode_tcp_host_in_config(config_path: str) -> bool:
    """Backfill tcp_host for RNodeInterface entries configured with a tcp:// port.

    RNS's desktop RNodeInterface derives tcp_host from a tcp:// port itself,
    but the Android-specific implementation reads tcp_host as its own,
    separate config key and never looks at port for that. Configs written or
    hand-edited with only ``port = tcp://host:port`` therefore silently try
    (and fail) to open the RNode as a serial device on Android. This keeps
    both keys in sync regardless of how the entry was created, so RNode over
    TCP works the same way on both platforms.

    Returns True if any interfaces were modified.
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
        if not _is_rnode_tcp_config_type(iface.get("type")):
            continue
        port = iface.get("port")
        if not rnode_port_is_tcp(port):
            continue
        host_part = _tcp_host_from_port(port)
        if host_part is None:
            continue
        if str(iface.get("tcp_host", "")).strip() != host_part:
            iface["tcp_host"] = host_part
            modified = True
    if modified:
        try:
            cfg.write()
        except Exception:
            pass
    return modified


def disable_rnode_interfaces_in_config(
    config_path: str,
    *,
    is_android: bool | None = None,
) -> bool:
    """Disable RNode* interfaces in a Reticulum config file that can't run here.

    RNode over TCP is left enabled since it needs no native Android modules.
    RNodeMultiInterface has no Android-specific implementation upstream and is
    always disabled on Android. Serial, classic-Bluetooth, and BLE entries are
    disabled only when their required native module isn't available.

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

    if is_android is None:
        is_android = _is_chaquopy_android()

    modified = False
    interfaces = cfg.get("interfaces")
    if not isinstance(interfaces, dict):
        return False
    for _iface_name, iface in interfaces.items():
        if not isinstance(iface, dict):
            continue
        iface_type = iface.get("type", "")
        if not isinstance(iface_type, str) or not iface_type.startswith("RNode"):
            continue
        if not _is_enabled(iface):
            continue

        if iface_type == "RNodeMultiInterface":
            should_disable = is_android
        else:
            should_disable = not rnode_transport_supported(iface, is_android=is_android)

        if should_disable:
            iface["interface_enabled"] = "false"
            modified = True
    if modified:
        try:
            cfg.write()
        except Exception:
            pass
    return modified


def _find_invalid_rnode_txpower(
    iface_name: str,
    iface: dict,
    interfaces: dict,
) -> object | None:
    from meshchatx.src.backend.interface_editor import validate_rnode_txpower

    iface_type = iface.get("type", "")
    if not isinstance(iface_type, str):
        return None
    if iface_type in ("RNodeInterface", "RNodeIPInterface"):
        txpower = iface.get("txpower")
        if validate_rnode_txpower(txpower) is not None:
            return txpower
        return None
    if iface_type != "RNodeMultiInterface":
        return None

    for value in iface.values():
        if isinstance(value, dict) and "txpower" in value:
            txpower = value.get("txpower")
            if validate_rnode_txpower(txpower) is not None:
                return txpower
    prefix = f"{iface_name}."
    for sub_name, sub_iface in interfaces.items():
        if not sub_name.startswith(prefix):
            continue
        if not isinstance(sub_iface, dict):
            continue
        txpower = sub_iface.get("txpower")
        if validate_rnode_txpower(txpower) is not None:
            return txpower
    return None


def _rnode_interface_has_invalid_txpower(
    iface_name: str,
    iface: dict,
    interfaces: dict,
) -> bool:
    return _find_invalid_rnode_txpower(iface_name, iface, interfaces) is not None


def guard_invalid_rnode_txpower_in_config(config_path: str) -> bool:
    """Disable RNode interfaces whose TX power would crash Reticulum on startup."""
    import os

    if not os.path.isfile(config_path):
        return False
    try:
        from RNS.vendor.configobj import ConfigObj

        from meshchatx.src.backend.interface_editor import validate_rnode_txpower

        cfg = ConfigObj(config_path)
    except Exception:
        return False

    modified = False
    interfaces = cfg.get("interfaces")
    if not isinstance(interfaces, dict):
        return False
    for iface_name, iface in interfaces.items():
        if not isinstance(iface, dict):
            continue
        if not _rnode_interface_has_invalid_txpower(iface_name, iface, interfaces):
            continue
        if not _is_enabled(iface):
            continue
        iface["interface_enabled"] = "false"
        modified = True
        txpower = _find_invalid_rnode_txpower(iface_name, iface, interfaces)
        detail = validate_rnode_txpower(txpower) or "invalid TX power"
        logger.warning(
            'Disabled RNode interface "%s" before startup: %s',
            iface_name,
            detail,
        )
    if modified:
        try:
            cfg.write()
        except Exception:
            pass
    return modified


def guard_rnode_interfaces_on_android(config_path: str) -> bool:
    """On Android, disable RNode interfaces that can't be brought up on this build.

    RNode over TCP is unaffected. Serial, classic-Bluetooth, and BLE entries
    are disabled only when their required native module isn't bundled, and
    RNodeMultiInterface is always disabled since RNS has no Android-specific
    implementation of it.
    """
    if not _is_chaquopy_android():
        return False
    disabled = disable_rnode_interfaces_in_config(config_path, is_android=True)
    if disabled:
        logger.warning(
            "One or more RNode interfaces were disabled because their transport "
            "is not supported on this Android build. RNode over TCP is unaffected.",
        )
    return disabled
