# SPDX-License-Identifier: 0BSD

"""Hot-apply Reticulum interface-discovery settings without a stack reload.

RNS reads most discovery options through class-level getters on every use,
so updating the underlying ``Reticulum`` class variables takes effect
immediately. ``discover_interfaces`` itself is represented by the
``Transport.discovery_handler`` (an ``InterfaceDiscovery``) which RNS only
creates at startup; this module starts or pauses it in place instead of
restarting the whole Reticulum stack.

``network_identity`` is deliberately not handled here: swapping the
announcement identity needs the same teardown a reload performs, so the
caller falls back to ``reload_reticulum`` when that value changes.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

import RNS

logger = logging.getLogger(__name__)

_RET = "_Reticulum__"

_DISCOVERY_THRESHOLD_KEYS = (
    ("interface_discovery_unknown_after_days", "THRESHOLD_UNKNOWN", 24 * 60 * 60),
    ("interface_discovery_stale_after_days", "THRESHOLD_STALE", 3 * 24 * 60 * 60),
    ("interface_discovery_remove_after_days", "THRESHOLD_REMOVE", 7 * 24 * 60 * 60),
)

_MODE_MAP = {
    "full": "MODE_FULL",
    "access_point": "MODE_ACCESS_POINT",
    "accesspoint": "MODE_ACCESS_POINT",
    "ap": "MODE_ACCESS_POINT",
    "pointtopoint": "MODE_POINT_TO_POINT",
    "ptp": "MODE_POINT_TO_POINT",
    "roaming": "MODE_ROAMING",
    "boundary": "MODE_BOUNDARY",
    "gateway": "MODE_GATEWAY",
    "gw": "MODE_GATEWAY",
    "internal": "MODE_INTERNAL",
}


def _reticulum_cls() -> type | None:
    cls = getattr(RNS, "Reticulum", None)
    return cls if isinstance(cls, type) else None


def _set_class_var(name: str, value: Any) -> None:
    cls = _reticulum_cls()
    if cls is None:
        return
    setattr(cls, _RET + name, value)


def _class_var(name: str, default: Any = None) -> Any:
    cls = _reticulum_cls()
    if cls is None:
        return default
    return getattr(cls, _RET + name, default)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "yes", "1", "on")


def _as_int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _yes_no_to_bool(value: Any) -> bool | None:
    """Map RNS yes/no config values to a bool; None when unset."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered in ("yes", "true", "1", "on"):
        return True
    if lowered in ("no", "false", "0", "off"):
        return False
    return None


def _parse_discovery_sources(value: Any) -> list[bytes]:
    """Parse interface_discovery_sources into identity-hash bytes.

    Mirrors RNS's config parsing (hex strings of TRUNCATED_HASHLENGTH/4
    hex chars). Invalid entries are skipped rather than raising so a bad
    value cannot wedge the live apply; RNS would reject the whole option
    at next startup, which the config write already allows today.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        raw_items = value
    else:
        raw_items = str(value).replace("\n", ",").split(",")
    try:
        hash_hex_len = (RNS.Reticulum.TRUNCATED_HASHLENGTH // 8) * 2
    except Exception:
        hash_hex_len = 16
    sources: list[bytes] = []
    for item in raw_items:
        hexhash = str(item).strip()
        if not hexhash:
            continue
        if len(hexhash) != hash_hex_len:
            continue
        try:
            digest = bytes.fromhex(hexhash)
        except ValueError:
            continue
        if digest not in sources:
            sources.append(digest)
    return sources


def _apply_autoconnect_mode(value: Any) -> None:
    """Map the config mode string to RNS Interface.MODE_* like Reticulum does."""
    if value is None or value == "":
        _set_class_var("autoconnect_interface_mode", None)
        return
    try:
        from RNS.Interfaces import Interface
    except Exception:
        return
    mode_name = _MODE_MAP.get(str(value).strip().lower())
    if mode_name is None:
        return
    _set_class_var(
        "autoconnect_interface_mode", getattr(Interface.Interface, mode_name)
    )


def _apply_discovery_thresholds(reticulum_config: dict) -> None:
    try:
        from RNS.Discovery import InterfaceDiscovery
    except Exception:
        return
    for key, attr, default_seconds in _DISCOVERY_THRESHOLD_KEYS:
        seconds = default_seconds
        raw = reticulum_config.get(key)
        if raw is not None and str(raw).strip() != "":
            try:
                days = float(str(raw).strip())
                if days > 0:
                    seconds = days * 86400.0
            except (TypeError, ValueError):
                pass
        try:
            setattr(InterfaceDiscovery, attr, seconds)
        except Exception:
            pass


def _discovery_handler():
    return getattr(RNS.Transport, "discovery_handler", None)


def _start_discovery() -> bool:
    """Create the InterfaceDiscovery listener if it does not exist."""
    try:
        if _discovery_handler() is not None:
            return True
        RNS.Transport.discover_interfaces()
        return _discovery_handler() is not None
    except Exception as exc:
        logger.warning("Could not start interface discovery live: %s", exc)
        return False


def _ensure_monitor_job(discovery: Any) -> None:
    """Restart InterfaceDiscovery's monitor thread after a pause/resume."""
    try:
        if getattr(discovery, "monitoring_autoconnects", True):
            return
        monitored = getattr(discovery, "monitored_interfaces", None) or []
        if not monitored:
            return
        job = getattr(discovery, "_InterfaceDiscovery__monitor_job", None)
        if job is None:
            return
        discovery.monitoring_autoconnects = True
        threading.Thread(target=job, daemon=True).start()
    except Exception as exc:
        logger.debug("Could not restart discovery monitor job: %s", exc)


def _set_discovery_enabled(enabled: bool) -> bool:
    """Start or pause interface discovery without touching the stack."""
    discovery = _discovery_handler()
    if enabled:
        if discovery is None:
            return _start_discovery()
        announce_handler = getattr(discovery, "handler", None)
        if announce_handler is not None:
            announce_handler.paused = False
        _ensure_monitor_job(discovery)
        return True

    if discovery is None:
        return True
    announce_handler = getattr(discovery, "handler", None)
    if announce_handler is not None:
        announce_handler.paused = True
    try:
        discovery.monitoring_autoconnects = False
    except Exception:
        pass
    return True


def apply_discovery_settings_live(app: Any) -> tuple[bool, str | None]:
    """Apply the current reticulum discovery config to the running RNS.

    Returns ``(applied, needs_reload_reason)``. ``applied`` is True when the
    live path ran to completion; ``needs_reload_reason`` is a short string
    when the change still requires ``reload_reticulum`` (shared instance or
    an unsupported RNS layout), or None when live apply covered everything.
    """
    reticulum = getattr(app, "reticulum", None)
    if reticulum is None:
        return False, "reticulum-unavailable"
    if getattr(reticulum, "is_connected_to_shared_instance", False):
        return False, "shared-instance"

    try:
        reticulum_config = app._get_reticulum_section() or {}
    except Exception:
        return False, "config-unavailable"

    try:
        discover_enabled = _as_bool(reticulum_config.get("discover_interfaces"))
        _set_class_var("discover_interfaces", discover_enabled)
        _set_class_var(
            "interface_sources",
            _parse_discovery_sources(
                reticulum_config.get("interface_discovery_sources")
            ),
        )

        required_value = _as_float_or_none(
            reticulum_config.get("required_discovery_value")
        )
        if required_value is not None and required_value <= 0:
            required_value = None
        _set_class_var("required_discovery_value", required_value)

        autoconnect_count = _as_int_or_none(
            reticulum_config.get("autoconnect_discovered_interfaces")
        )
        _set_class_var(
            "autoconnect_discovered_interfaces",
            autoconnect_count if autoconnect_count and autoconnect_count > 0 else False,
        )
        _set_class_var(
            "autoconnect_unverified",
            _as_bool(reticulum_config.get("autoconnect_unverified_implementations")),
        )
        _apply_autoconnect_mode(reticulum_config.get("autoconnect_interface_mode"))
        _set_class_var(
            "autoconnect_interface_gravity",
            _as_int_or_none(reticulum_config.get("autoconnect_interface_gravity")),
        )
        announces_internal = _yes_no_to_bool(
            reticulum_config.get("autoconnect_announces_to_internal")
        )
        _set_class_var(
            "autoconnect_announces_to_internal",
            announces_internal if announces_internal else None,
        )
        _set_class_var(
            "default_gravity",
            _as_int_or_none(reticulum_config.get("default_gravity")),
        )

        _apply_discovery_thresholds(reticulum_config)

        # Keep the live announce handler's stamp requirement in sync; RNS
        # captures required_value when InterfaceDiscovery is constructed.
        discovery = _discovery_handler()
        announce_handler = getattr(discovery, "handler", None) if discovery else None
        if announce_handler is not None:
            try:
                if required_value is not None:
                    announce_handler.required_value = required_value
                elif hasattr(announce_handler, "required_value"):
                    from RNS.Discovery import InterfaceAnnouncer

                    announce_handler.required_value = (
                        InterfaceAnnouncer.DEFAULT_STAMP_VALUE
                    )
            except Exception:
                pass

        if not _set_discovery_enabled(discover_enabled):
            return False, "discovery-toggle-failed"
        return True, None
    except Exception as exc:
        logger.warning("Live discovery apply failed, falling back to reload: %s", exc)
        return False, "live-apply-error"
