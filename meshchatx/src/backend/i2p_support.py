# SPDX-License-Identifier: 0BSD

"""I2PInterface safety helpers for MeshChatX.

Reticulum's I2P interface is fragile: only one should exist, it must be the
last interface in the config, and transport mode must already be enabled.
Adding I2P via raw config/import or leaving it mid-list after later edits can
brick startup (on Android that previously meant wiping the whole app).

These helpers enforce the constraints on API writes and repair unsafe configs
before Reticulum starts so identity/storage survive.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_TRUE_STRINGS = ("true", "yes", "1", "on", "y")

I2P_TYPE = "I2PInterface"

MSG_TRANSPORT_REQUIRED = (
    "Transport mode must be enabled before adding or enabling an I2P interface. "
    "Enable it in Settings, then add I2P as the last interface."
)
MSG_ONLY_ONE = (
    "Only one I2P interface is allowed. Remove or disable the existing I2P "
    "interface before adding another."
)
MSG_IMPORT_FORBIDDEN = (
    "I2P interfaces cannot be imported from a config file. Add I2P only through "
    "the Add Interface page, with transport mode already enabled, as the last "
    "interface."
)
MSG_RAW_FORBIDDEN = (
    "I2P interfaces cannot be added or changed through the raw config editor. "
    "Use the Add Interface page (transport must already be enabled), or delete "
    "the I2P section from the file to recover."
)
MSG_MUST_BE_LAST = (
    "The I2P interface must be the last interface in the Reticulum config. "
    "Remove interfaces added after it, or delete I2P and re-add it last."
)


def is_i2p_interface(iface: object) -> bool:
    if not isinstance(iface, dict):
        return False
    return str(iface.get("type") or "").strip() == I2P_TYPE


def _parse_bool(value: object, *, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUE_STRINGS


def is_interface_enabled(iface: dict) -> bool:
    for key in ("interface_enabled", "enabled"):
        if key in iface:
            return _parse_bool(iface.get(key), default=False)
    return False


def transport_enabled_in_section(reticulum_section: object) -> bool:
    if not isinstance(reticulum_section, dict):
        return False
    return _parse_bool(reticulum_section.get("enable_transport"), default=False)


def list_i2p_names(interfaces: object) -> list[str]:
    if not isinstance(interfaces, dict):
        return []
    return [name for name, iface in interfaces.items() if is_i2p_interface(iface)]


def _i2p_block_is_suffix(interfaces: dict) -> bool:
    """True when every I2P entry is at the end (no non-I2P after the first I2P)."""
    seen_i2p = False
    for _name, iface in interfaces.items():
        if is_i2p_interface(iface):
            seen_i2p = True
        elif seen_i2p:
            return False
    return True


def i2p_is_last(interfaces: object) -> bool:
    if not isinstance(interfaces, dict) or not interfaces:
        return True
    if not list_i2p_names(interfaces):
        return True
    return _i2p_block_is_suffix(interfaces)


def validate_i2p_add_or_update(
    interfaces: object,
    reticulum_section: object,
    *,
    interface_name: str,
    interface_type: str,
    updating_existing: bool,
) -> str | None:
    """Return an error message when adding/updating I2P is unsafe, else None."""
    if str(interface_type or "").strip() != I2P_TYPE:
        return None
    if not transport_enabled_in_section(reticulum_section):
        return MSG_TRANSPORT_REQUIRED
    if not isinstance(interfaces, dict):
        interfaces = {}
    existing = list_i2p_names(interfaces)
    if updating_existing:
        others = [n for n in existing if n != interface_name]
        if others:
            return MSG_ONLY_ONE
        return None
    if existing:
        return MSG_ONLY_ONE
    return None


def validate_i2p_enable(
    interfaces: object,
    reticulum_section: object,
    *,
    interface_name: str,
) -> str | None:
    if not isinstance(interfaces, dict):
        return None
    target = interfaces.get(interface_name)
    if not is_i2p_interface(target):
        return None
    if not transport_enabled_in_section(reticulum_section):
        return MSG_TRANSPORT_REQUIRED
    others_enabled = [
        n
        for n in list_i2p_names(interfaces)
        if n != interface_name and is_interface_enabled(interfaces.get(n) or {})
    ]
    if others_enabled:
        return MSG_ONLY_ONE
    return None


def validate_no_i2p_in_import(interface_config: dict) -> str | None:
    for name, body in interface_config.items():
        if is_i2p_interface(body):
            return f'{MSG_IMPORT_FORBIDDEN} (rejected "{name}")'
    return None


def reorder_interfaces_i2p_last(interfaces: dict) -> bool:
    """Move all I2P sections to the end. Returns True when order changed."""
    if not isinstance(interfaces, dict) or not interfaces:
        return False
    if _i2p_block_is_suffix(interfaces):
        return False

    non_i2p: list[tuple[str, Any]] = []
    i2p: list[tuple[str, Any]] = []
    for name, iface in list(interfaces.items()):
        if is_i2p_interface(iface):
            i2p.append((name, iface))
        else:
            non_i2p.append((name, iface))
    if not i2p:
        return False

    for name in list(interfaces.keys()):
        del interfaces[name]
    for name, iface in non_i2p + i2p:
        interfaces[name] = iface
    return True


def enforce_single_enabled_i2p(interfaces: dict) -> bool:
    """Disable all but the first enabled I2P interface. Returns True if changed."""
    if not isinstance(interfaces, dict):
        return False
    modified = False
    kept: str | None = None
    for name, iface in interfaces.items():
        if not is_i2p_interface(iface):
            continue
        if not is_interface_enabled(iface):
            continue
        if kept is None:
            kept = name
            continue
        iface["interface_enabled"] = "false"
        if "enabled" in iface:
            iface["enabled"] = "false"
        modified = True
        logger.warning(
            'Disabled extra I2P interface "%s" (only one I2P interface is allowed; '
            'kept "%s")',
            name,
            kept,
        )
    return modified


def disable_i2p_when_transport_off(
    interfaces: dict,
    reticulum_section: object,
) -> bool:
    if transport_enabled_in_section(reticulum_section):
        return False
    if not isinstance(interfaces, dict):
        return False
    modified = False
    for name, iface in interfaces.items():
        if not is_i2p_interface(iface):
            continue
        if not is_interface_enabled(iface):
            continue
        iface["interface_enabled"] = "false"
        if "enabled" in iface:
            iface["enabled"] = "false"
        modified = True
        logger.warning(
            'Disabled I2P interface "%s" because enable_transport is off',
            name,
        )
    return modified


def repair_interfaces_dict(
    interfaces: dict,
    reticulum_section: object,
) -> bool:
    """Apply all in-memory I2P safety repairs. Returns True when anything changed."""
    if not isinstance(interfaces, dict):
        return False
    modified = False
    if enforce_single_enabled_i2p(interfaces):
        modified = True
    if disable_i2p_when_transport_off(interfaces, reticulum_section):
        modified = True
    if reorder_interfaces_i2p_last(interfaces):
        modified = True
        logger.warning(
            "Moved I2P interface(s) to the end of [interfaces] for safe startup",
        )
    return modified


def existing_i2p_names_from_config_path(config_path: str) -> set[str]:
    if not os.path.isfile(config_path):
        return set()
    try:
        from RNS.vendor.configobj import ConfigObj

        cfg = ConfigObj(config_path)
    except Exception:
        return set()
    interfaces = cfg.get("interfaces")
    return set(list_i2p_names(interfaces))


def _iface_snapshot(iface: dict) -> dict:
    out = {}
    for key, value in iface.items():
        if isinstance(value, dict):
            continue
        out[str(key)] = value
    return out


def validate_raw_config_i2p_policy(
    content: str,
    *,
    previous_interfaces: dict | None = None,
) -> str | None:
    """Reject raw edits that add or alter I2P stanzas via the file editor.

    Deleting an existing I2P section is allowed (recovery path). Adding I2P or
    changing an existing I2P stanza through raw text is not.
    """
    try:
        from RNS.vendor.configobj import ConfigObj
    except Exception:
        return None

    try:
        cfg = ConfigObj(content.splitlines())
    except Exception:
        return None

    interfaces = cfg.get("interfaces")
    if not isinstance(interfaces, dict):
        return None

    prev_ifaces = previous_interfaces if isinstance(previous_interfaces, dict) else {}
    prev_names = set(list_i2p_names(prev_ifaces))
    new_names = set(list_i2p_names(interfaces))

    if new_names - prev_names:
        return MSG_RAW_FORBIDDEN

    if len(new_names) > 1:
        return MSG_ONLY_ONE

    if new_names and not _i2p_block_is_suffix(interfaces):
        return MSG_MUST_BE_LAST

    for name in new_names & prev_names:
        prev_body = prev_ifaces.get(name) or {}
        new_body = interfaces.get(name) or {}
        if not isinstance(prev_body, dict) or not isinstance(new_body, dict):
            return MSG_RAW_FORBIDDEN
        if _iface_snapshot(prev_body) != _iface_snapshot(new_body):
            return MSG_RAW_FORBIDDEN

    return None


def disable_all_i2p_in_config(config_path: str) -> bool:
    """Disable every I2P interface in *config_path*. Returns True if changed."""
    if not os.path.isfile(config_path):
        return False
    try:
        from RNS.vendor.configobj import ConfigObj

        cfg = ConfigObj(config_path)
    except Exception:
        return False
    interfaces = cfg.get("interfaces")
    if not isinstance(interfaces, dict):
        return False
    modified = False
    for name, iface in interfaces.items():
        if not is_i2p_interface(iface):
            continue
        if not is_interface_enabled(iface):
            continue
        iface["interface_enabled"] = "false"
        if "enabled" in iface:
            iface["enabled"] = "false"
        modified = True
        logger.warning(
            'Disabled I2P interface "%s" to recover from a Reticulum startup failure',
            name,
        )
    if not modified:
        return False
    try:
        cfg.write()
    except Exception as exc:
        logger.warning("Failed to disable I2P interfaces in config: %s", exc)
        return False
    return True


def guard_i2p_interfaces_in_config(config_path: str) -> bool:
    """Repair I2P entries in a Reticulum config file before startup.

    Ensures at most one enabled I2P interface, disables I2P when transport is
    off, and moves I2P sections to the end of [interfaces].
    """
    if not os.path.isfile(config_path):
        return False
    try:
        from RNS.vendor.configobj import ConfigObj

        cfg = ConfigObj(config_path)
    except Exception as exc:
        logger.warning("Could not open Reticulum config for I2P guard: %s", exc)
        return False

    interfaces = cfg.get("interfaces")
    reticulum = cfg.get("reticulum")
    if not isinstance(interfaces, dict):
        return False

    if not repair_interfaces_dict(interfaces, reticulum):
        return False

    try:
        cfg.write()
    except Exception as exc:
        logger.warning("Failed to write I2P-guarded Reticulum config: %s", exc)
        return False
    return True
