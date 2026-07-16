# SPDX-License-Identifier: 0BSD

"""Contain RNS process-killing exits and recover from bad interface configs.

Reticulum's ``RNS.panic()`` calls ``os._exit(255)``, which kills the whole
MeshChatX process (fatal on Android where Python runs in-process). Interface
init failures can also leave the app unable to start until the user wipes
storage. This module:

1. Replaces ``RNS.panic`` / ``RNS.exit`` with catchable exceptions
2. Forces ``panic_on_interface_error = No`` in the Reticulum config
3. Progressively disables risky interfaces and retries RNS construction
"""

from __future__ import annotations

import logging
import os
import re
import contextlib
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_TRUE_STRINGS = ("true", "yes", "1", "on", "y")
_PANIC_PATCHED = False
_ORIGINAL_PANIC = None
_ORIGINAL_EXIT = None
_EXIT_IN_PROGRESS = False

# Prefer disabling these types first when init fails without a named culprit.
_HIGH_RISK_TYPES = (
    "I2PInterface",
    "RNodeMultiInterface",
    "RNodeInterface",
    "RNodeIPInterface",
    "AutoInterface",
    "SerialInterface",
    "KISSInterface",
    "AX25KISSInterface",
    "PipeInterface",
)


class RnsPanicError(RuntimeError):
    """Raised instead of ``os._exit`` when RNS would panic or hard-exit."""


def install_rns_panic_containment(*, force: bool = False) -> bool:
    """Replace RNS panic/exit with exceptions so the HTTP process can survive.

    Safe to call multiple times. Returns True when the patch was applied (or
    was already applied).
    """
    global _PANIC_PATCHED, _ORIGINAL_PANIC, _ORIGINAL_EXIT, _EXIT_IN_PROGRESS
    if _PANIC_PATCHED and not force:
        return True
    try:
        import RNS
    except Exception as exc:
        logger.warning("Could not import RNS for panic containment: %s", exc)
        return False

    if force:
        _EXIT_IN_PROGRESS = False

    if _ORIGINAL_PANIC is None:
        _ORIGINAL_PANIC = getattr(RNS, "panic", None)
    if _ORIGINAL_EXIT is None:
        _ORIGINAL_EXIT = getattr(RNS, "exit", None)

    def _contained_panic(*_args, **_kwargs):
        message = "RNS.panic() was called"
        if _args:
            message = f"RNS.panic(): {_args[0]}"
        # Avoid logging handlers here. Panic can run under signal context.
        raise RnsPanicError(message)

    def _contained_exit(code: int = 0):
        global _EXIT_IN_PROGRESS
        # SIGINT/SIGTERM can reenter while logging or SQLite is in flight.
        # A second RNS.exit must be a no-op or FileHandlers blow up with
        # "reentrant call inside BufferedWriter".
        if _EXIT_IN_PROGRESS:
            return
        _EXIT_IN_PROGRESS = True
        try:
            if hasattr(RNS, "Reticulum") and hasattr(RNS.Reticulum, "exit_handler"):
                with contextlib.suppress(Exception):
                    RNS.Reticulum.exit_handler()
        finally:
            if code != 0:
                _EXIT_IN_PROGRESS = False
                raise RnsPanicError(f"RNS.exit({code}) was called")

    RNS.panic = _contained_panic
    RNS.exit = _contained_exit
    _PANIC_PATCHED = True
    logger.info("Installed RNS panic/exit containment (os._exit disabled for RNS)")
    return True


def ensure_panic_on_interface_error_disabled(config_path: str) -> bool:
    """Force ``panic_on_interface_error = No`` so interface faults cannot kill RNS."""
    if not os.path.isfile(config_path):
        return False
    try:
        from RNS.vendor.configobj import ConfigObj

        cfg = ConfigObj(config_path)
    except Exception:
        return False

    reticulum = cfg.get("reticulum")
    if not isinstance(reticulum, dict):
        reticulum = {}
        cfg["reticulum"] = reticulum

    current = str(reticulum.get("panic_on_interface_error", "No")).strip().lower()
    if current in ("no", "false", "0", "off", ""):
        if "panic_on_interface_error" not in reticulum:
            reticulum["panic_on_interface_error"] = "No"
            try:
                cfg.write()
            except Exception:
                return False
            return True
        return False

    reticulum["panic_on_interface_error"] = "No"
    try:
        cfg.write()
    except Exception as exc:
        logger.warning(
            "Failed to disable panic_on_interface_error in %s: %s",
            config_path,
            exc,
        )
        return False
    logger.warning(
        "Disabled panic_on_interface_error in %s so interface errors cannot "
        "kill the MeshChatX process",
        config_path,
    )
    return True


def _is_enabled(iface: dict) -> bool:
    for key in ("interface_enabled", "enabled"):
        if key in iface and str(iface.get(key, "")).strip().lower() in _TRUE_STRINGS:
            return True
    return False


def _disable_iface(iface: dict) -> None:
    iface["interface_enabled"] = "false"
    if "enabled" in iface:
        iface["enabled"] = "false"


def list_enabled_interface_names(config_path: str) -> list[str]:
    if not os.path.isfile(config_path):
        return []
    try:
        from RNS.vendor.configobj import ConfigObj

        cfg = ConfigObj(config_path)
    except Exception:
        return []
    interfaces = cfg.get("interfaces")
    if not isinstance(interfaces, dict):
        return []
    return [
        name
        for name, iface in interfaces.items()
        if isinstance(iface, dict) and _is_enabled(iface)
    ]


def disable_named_interfaces_in_config(
    config_path: str,
    names: list[str] | set[str],
) -> list[str]:
    """Disable the named interfaces. Returns names that were actually disabled."""
    if not names or not os.path.isfile(config_path):
        return []
    try:
        from RNS.vendor.configobj import ConfigObj

        cfg = ConfigObj(config_path)
    except Exception:
        return []
    interfaces = cfg.get("interfaces")
    if not isinstance(interfaces, dict):
        return []
    disabled: list[str] = []
    wanted = {str(n) for n in names}
    for name, iface in interfaces.items():
        if name not in wanted or not isinstance(iface, dict):
            continue
        if not _is_enabled(iface):
            continue
        _disable_iface(iface)
        disabled.append(name)
        logger.warning('Disabled interface "%s" during RNS startup recovery', name)
    if not disabled:
        return []
    try:
        cfg.write()
    except Exception as exc:
        logger.warning("Failed to write interface recovery config: %s", exc)
        return []
    return disabled


def disable_interfaces_by_type(
    config_path: str,
    iface_types: tuple[str, ...] | list[str],
    *,
    limit: int | None = None,
) -> list[str]:
    if not os.path.isfile(config_path):
        return []
    try:
        from RNS.vendor.configobj import ConfigObj

        cfg = ConfigObj(config_path)
    except Exception:
        return []
    interfaces = cfg.get("interfaces")
    if not isinstance(interfaces, dict):
        return []
    type_set = {str(t) for t in iface_types}
    disabled: list[str] = []
    for name, iface in interfaces.items():
        if not isinstance(iface, dict) or not _is_enabled(iface):
            continue
        if str(iface.get("type") or "").strip() not in type_set:
            continue
        _disable_iface(iface)
        disabled.append(name)
        logger.warning(
            'Disabled %s interface "%s" during RNS startup recovery',
            iface.get("type"),
            name,
        )
        if limit is not None and len(disabled) >= limit:
            break
    if not disabled:
        return []
    try:
        cfg.write()
    except Exception as exc:
        logger.warning("Failed to write typed interface recovery config: %s", exc)
        return []
    return disabled


def extract_interface_names_from_error(error: BaseException | str) -> list[str]:
    """Best-effort parse of interface section names from an RNS error string."""
    text = str(error)
    found: list[str] = []
    patterns = (
        r'interface\s+"([^"]+)"',
        r"interface\s+'([^']+)'",
        r"Interface\[([^\]]+)\]",
        r"I2PInterface\[([^\]]+)\]",
        r"AutoInterface\[([^\]]+)\]",
        r"TCPClientInterface\[([^\]]+)\]",
        r"TCPServerInterface\[([^\]]+)\]",
        r"RNodeInterface\[([^\]]+)\]",
        r"The interface name \"([^\"]+)\" was already used",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            name = match.group(1).strip()
            if name and name not in found:
                found.append(name)
    return found


def apply_startup_recovery_step(
    config_path: str,
    error: BaseException | str,
    *,
    attempt: int,
) -> list[str]:
    """Disable something that might be blocking RNS init. Returns disabled names.

    Steps escalate with *attempt*:
    0. Named interfaces from the error (if any), else I2P
    1. RNode / serial / kiss family
    2. AutoInterface
    3. Any remaining enabled high-risk interface (one at a time)
    """
    from meshchatx.src.backend import i2p_support
    from meshchatx.src.backend.rnode_support import (
        _is_chaquopy_android,
        disable_rnode_interfaces_in_config,
    )

    disabled: list[str] = []
    named = extract_interface_names_from_error(error)
    if named:
        disabled.extend(disable_named_interfaces_in_config(config_path, named))
        if disabled:
            return disabled

    if attempt <= 0:
        if i2p_support.disable_all_i2p_in_config(config_path):
            # Names unknown here, so report a synthetic marker for logs/tests.
            disabled.append("__i2p__")
        return disabled

    if attempt == 1:
        if disable_rnode_interfaces_in_config(
            config_path,
            is_android=_is_chaquopy_android(),
        ):
            disabled.append("__rnode__")
        more = disable_interfaces_by_type(
            config_path,
            ("SerialInterface", "KISSInterface", "AX25KISSInterface", "PipeInterface"),
        )
        disabled.extend(more)
        return disabled

    if attempt == 2:
        more = disable_interfaces_by_type(config_path, ("AutoInterface",))
        disabled.extend(more)
        return disabled

    # Final attempts: peel off one high-risk enabled interface at a time.
    for iface_type in _HIGH_RISK_TYPES:
        more = disable_interfaces_by_type(config_path, (iface_type,), limit=1)
        if more:
            disabled.extend(more)
            break
    return disabled


def create_reticulum_with_recovery(
    config_dir: str,
    *,
    construct: Callable[[], Any],
    max_attempts: int = 5,
) -> Any:
    """Construct RNS, progressively disabling bad interfaces on failure."""
    install_rns_panic_containment()
    config_path = os.path.join(config_dir, "config")
    ensure_panic_on_interface_error_disabled(config_path)

    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return construct()
        except Exception as exc:
            last_exc = exc
            disabled = apply_startup_recovery_step(
                config_path,
                exc,
                attempt=attempt,
            )
            if not disabled:
                break
            print(
                "Reticulum init failed; disabled "
                f"{', '.join(disabled)} and retrying "
                f"(attempt {attempt + 1}/{max_attempts}). "
                f"Error: {exc}",
                flush=True,
            )
    assert last_exc is not None
    raise last_exc
