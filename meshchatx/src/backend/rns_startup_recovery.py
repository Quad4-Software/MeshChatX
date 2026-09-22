# SPDX-License-Identifier: 0BSD

"""Contain RNS process-killing exits and recover from bad interface configs.

Reticulum's RNS.panic() calls os._exit(255), which kills the whole
MeshChatX process (fatal on Android where Python runs in-process). Interface
init failures can also leave the app unable to start until the user wipes
storage. This module:

1. Replaces RNS.panic / RNS.exit with catchable exceptions
2. Forces panic_on_interface_error = No in the Reticulum config
3. Progressively disables risky interfaces and retries RNS construction
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_TRUE_STRINGS = ("true", "yes", "1", "on", "y")
_PANIC_PATCHED = False
_ORIGINAL_PANIC = None
_ORIGINAL_EXIT = None
_EXIT_IN_PROGRESS = False

_HIGH_RISK_TYPES = (
    "RNodeMultiInterface",
    "RNodeInterface",
    "RNodeIPInterface",
    "AutoInterface",
    "SerialInterface",
    "KISSInterface",
    "AX25KISSInterface",
    "PipeInterface",
    "I2PInterface",
)

_CAPTURED_ERROR_LOG_LINES: list[str] = []
_ORIGINAL_RNS_LOG = None

RECOVERY_REPORT_FILENAME = "startup_recovery.json"


def _write_recovery_report(config_dir: str, disabled: list[str]) -> None:
    """Persist which interfaces startup recovery turned off.

    The app reads this once when building user guidance so the owner can
    see that an interface was disabled automatically, instead of silently
    losing an interface they configured.
    """
    import json
    import time

    if not disabled:
        return
    path = os.path.join(config_dir, RECOVERY_REPORT_FILENAME)
    try:
        payload = {"disabled": list(dict.fromkeys(disabled)), "time": time.time()}
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        os.replace(tmp_path, path)
    except Exception as exc:
        logger.warning("Failed to write startup recovery report: %s", exc)


def consume_recovery_report(config_dir: str) -> list[str]:
    """Read and clear the startup recovery report. Returns disabled names."""
    import json

    path = os.path.join(config_dir, RECOVERY_REPORT_FILENAME)
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return []
    except Exception:
        payload = None
    with contextlib.suppress(Exception):
        os.remove(path)
    if not isinstance(payload, dict):
        return []
    disabled = payload.get("disabled")
    if not isinstance(disabled, list):
        return []
    return [str(name) for name in disabled if name]


def _capturing_log(msg, level=3, *args, **kwargs):
    try:
        import RNS

        if level <= RNS.LOG_ERROR:
            _CAPTURED_ERROR_LOG_LINES.append(str(msg))
            del _CAPTURED_ERROR_LOG_LINES[:-20]
    except Exception:
        pass
    original = _ORIGINAL_RNS_LOG
    if original is None:
        return None
    return original(msg, level, *args, **kwargs)


@contextlib.contextmanager
def _capture_rns_error_logs():
    global _ORIGINAL_RNS_LOG
    try:
        import RNS
    except Exception:
        yield
        return

    _CAPTURED_ERROR_LOG_LINES.clear()
    _ORIGINAL_RNS_LOG = RNS.log
    RNS.log = _capturing_log
    try:
        yield
    finally:
        RNS.log = _ORIGINAL_RNS_LOG


def _mentions_i2p(text: str) -> bool:
    return "i2p" in str(text).lower()


class RnsPanicError(RuntimeError):
    """Raised instead of os._exit when RNS would panic or hard-exit."""


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
        if _CAPTURED_ERROR_LOG_LINES:
            message = message + " | " + " | ".join(_CAPTURED_ERROR_LOG_LINES[-5:])
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
    """Force panic_on_interface_error = No so interface faults cannot kill RNS."""
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
    0. Named interfaces from the error (if any), else I2P when error mentions I2P
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
        if _mentions_i2p(str(error)) and i2p_support.disable_all_i2p_in_config(
            config_path,
        ):
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


def _close_quietly(resource) -> None:
    """Close a socket, socketserver, or serial-style object."""
    import socket
    import socketserver
    import threading

    if isinstance(resource, socketserver.BaseServer):
        # The port stays bound until serve_forever exits because the
        # selector holds a reference to the socket's file description.
        # shutdown() is what makes serve_forever exit, but it blocks
        # forever on a server that never served, so it runs on a daemon
        # thread joined with a timeout before server_close() drops the
        # socket.
        done = threading.Event()

        def _shutdown():
            with contextlib.suppress(Exception):
                resource.shutdown()
            done.set()

        threading.Thread(target=_shutdown, daemon=True).start()
        done.wait(timeout=3)
        with contextlib.suppress(Exception):
            resource.server_close()
        return
    if isinstance(resource, socket.socket):
        with contextlib.suppress(Exception):
            resource.shutdown(socket.SHUT_RDWR)
        with contextlib.suppress(Exception):
            resource.close()
        return
    close = getattr(resource, "close", None)
    if callable(close) and (
        hasattr(resource, "fileno")
        or hasattr(resource, "is_open")
        or hasattr(resource, "isOpen")
    ):
        with contextlib.suppress(Exception):
            close()


def _release_interface_resources(interface) -> None:
    """Close every socket-like resource reachable from a dead interface.

    Interface.detach() releases sockets on most interface types, but
    AutoInterface.detach() only flips a flag: its per-ifname UDPServers
    stay bound and keep the data port held, so the recovery retry fails
    with EADDRINUSE all over again. Walk the interface attributes for
    sockets, servers, and serial handles and close them directly.

    AutoInterface also binds discovery sockets inside __init__ and keeps
    them only in thread closures, so attribute walking cannot reach
    them. Scan live threads for closures that reference this interface
    and close any sockets held there. Scoped to closures that mention
    the dead interface so unrelated sockets are never touched.
    """
    seen: set[int] = set()
    for value in list(vars(interface).values()):
        if isinstance(value, dict):
            candidates = list(value.values())
        elif isinstance(value, (list, tuple, set)):
            candidates = list(value)
        else:
            candidates = [value]
        for resource in candidates:
            if id(resource) in seen:
                continue
            seen.add(id(resource))
            _close_quietly(resource)

    import socket
    import threading

    for thread in threading.enumerate():
        target = getattr(thread, "_target", None)
        cells = getattr(target, "__closure__", None) or ()
        cell_values = []
        for cell in cells:
            with contextlib.suppress(Exception):
                cell_values.append(cell.cell_contents)
        if not any(v is interface for v in cell_values):
            continue
        for value in cell_values:
            if isinstance(value, socket.socket):
                _close_quietly(value)


def reset_rns_runtime_state() -> None:
    """Best-effort teardown of a partially constructed RNS.

    RNS.Reticulum.__init__ assigns Reticulum.__instance at the top and
    starts Transport workers before interfaces are synthesised. When an
    interface then fails to come up, the interpreter is left holding the
    singleton, bound sockets, and running workers, so every later
    Reticulum() attempt fails instantly with "Attempt to reinitialise".
    Android makes this fatal: the Java shell retries start_server inside
    the same interpreter, each retry dies on the singleton, and the app
    ends on a permanent startup-error screen.

    Detaching interfaces releases the ports the surviving interfaces
    bound, clearing the singleton lets Reticulum() run again, and
    toggling _should_run retires any worker threads the failed init
    spawned before the next start() re-arms them.
    """
    try:
        import RNS
    except Exception:
        return

    transport = getattr(RNS, "Transport", None)
    if transport is not None:
        with contextlib.suppress(Exception):
            transport._should_run = False
        interfaces = list(getattr(transport, "interfaces", []) or [])
        for interface in interfaces:
            with contextlib.suppress(Exception):
                _release_interface_resources(interface)
        with contextlib.suppress(Exception):
            transport.detach_interfaces()
        for attr in (
            "interfaces",
            "destinations",
            "pending_links",
            "active_links",
            "control_destinations",
            "control_hashes",
            "mgmt_destinations",
            "mgmt_hashes",
            "remote_management_allowed",
            "local_client_interfaces",
            "local_client_rssi_cache",
            "local_client_snr_cache",
            "local_client_q_cache",
        ):
            with contextlib.suppress(Exception):
                setattr(transport, attr, [])
        for attr in ("destinations_map", "pending_links_map"):
            with contextlib.suppress(Exception):
                setattr(transport, attr, {})
        for attr in (
            "identity",
            "network_identity",
            "_identity",
            "interface_announcer",
            "discovery_handler",
            "blackhole_updater",
            "start_time",
        ):
            with contextlib.suppress(Exception):
                setattr(transport, attr, None)
        with contextlib.suppress(Exception):
            transport.ready = False
        with contextlib.suppress(Exception):
            transport._should_run = True

    reticulum_cls = getattr(RNS, "Reticulum", None)
    if reticulum_cls is not None:
        with contextlib.suppress(Exception):
            reticulum_cls._Reticulum__instance = None
        with contextlib.suppress(Exception):
            reticulum_cls._Reticulum__interface_detach_ran = False


def sweep_orphaned_ratchet_files(config_dir: str) -> int:
    """Remove ratchet storage entries whose names are not 32-hex destinations.

    Older RNS builds staged ratchet writes under temp names like
    <hash>.out. A crash between write and rename leaves the orphan behind,
    and upstream _clean_ratchets cannot remove it: it calls
    bytes.fromhex on the full filename, the suffix breaks parsing, and the
    unlink is skipped, so the corrupted-file error path re-runs on every
    startup. Sweeping before Reticulum init removes the recurring error
    and the wasted per-boot processing.
    """
    ratchets_dir = os.path.join(config_dir, "storage", "ratchets")
    if not os.path.isdir(ratchets_dir):
        return 0
    removed = 0
    try:
        for name in os.listdir(ratchets_dir):
            if len(name) == 32:
                try:
                    bytes.fromhex(name)
                    continue
                except ValueError:
                    pass
            path = os.path.join(ratchets_dir, name)
            if not os.path.isfile(path):
                continue
            try:
                os.unlink(path)
                removed += 1
                logger.warning("Removed orphaned ratchet storage file %s", name)
            except OSError as exc:
                logger.warning(
                    "Could not remove orphaned ratchet file %s: %s", name, exc
                )
    except OSError as exc:
        logger.warning("Could not sweep ratchet storage: %s", exc)
    return removed


def create_reticulum_with_recovery(
    config_dir: str,
    *,
    construct: Callable[[], Any],
    max_attempts: int = 5,
) -> Any:
    """Construct RNS, progressively disabling bad interfaces on failure."""
    install_rns_panic_containment()
    sweep_orphaned_ratchet_files(config_dir)
    try:
        from meshchatx.src.backend.rns_rnode_patch import (
            install_rns_rnode_patches,
        )

        install_rns_rnode_patches()
    except Exception:
        logger.debug("RNS RNode patch install skipped", exc_info=True)
    try:
        from meshchatx.src.backend.rns_backbone_patch import (
            install_rns_backbone_patches,
        )

        install_rns_backbone_patches()
    except Exception:
        logger.debug("RNS backbone patch install skipped", exc_info=True)
    config_path = os.path.join(config_dir, "config")
    ensure_panic_on_interface_error_disabled(config_path)

    try:
        import RNS

        stale = getattr(RNS.Reticulum, "_Reticulum__instance", None)
        if stale is not None and getattr(stale, "jobs_thread", None) is None:
            # A previous failed init left a zombie singleton behind.
            # Android retries start_server inside the same interpreter,
            # so without this the retry dies instantly on "Attempt to
            # reinitialise Reticulum". jobs_thread is only assigned once
            # __init__ completes, so a healthy instance is never touched.
            reset_rns_runtime_state()
    except Exception:
        pass

    last_exc: Exception | None = None
    all_disabled: list[str] = []
    for attempt in range(max_attempts):
        try:
            with _capture_rns_error_logs():
                instance = construct()
            _write_recovery_report(config_dir, all_disabled)
            return instance
        except Exception as exc:
            last_exc = exc
            # A failed init leaves the Reticulum singleton, Transport
            # workers, and bound sockets behind. Clear them or the retry
            # dies instantly on "Attempt to reinitialise Reticulum".
            reset_rns_runtime_state()
            disabled = apply_startup_recovery_step(
                config_path,
                exc,
                attempt=attempt,
            )
            if not disabled:
                break
            all_disabled.extend(disabled)
            print(
                "Reticulum init failed; disabled "
                f"{', '.join(disabled)} and retrying "
                f"(attempt {attempt + 1}/{max_attempts}). "
                f"Error: {exc}",
                flush=True,
            )
    if last_exc is None:
        raise RuntimeError("Reticulum init failed")
    raise last_exc
