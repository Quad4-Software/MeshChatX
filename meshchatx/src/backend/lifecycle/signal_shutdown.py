# SPDX-License-Identifier: 0BSD

"""SIGINT/SIGTERM handlers that flush SQLite before stopping the process.

Reticulum installs SIGINT/SIGTERM handlers that call RNS.exit(). With panic
containment that no longer os._exit, but the handlers still replace aiohttp's
GracefulExit path. Repeated Ctrl+C from task/dev scripts then escalates to
SIGKILL while WAL may be uncheckpointed, which can leave a malformed DB.

These handlers always durable-flush identity databases first, detach RNS
interfaces, then raise aiohttp GracefulExit so on_shutdown can finish.
"""

from __future__ import annotations

import contextlib
import logging
import signal
import threading
from collections.abc import Callable
from types import FrameType
from typing import Any

logger = logging.getLogger(__name__)

_APP_REF: Any | None = None
_FLUSH_LOCK = threading.Lock()
_FLUSHED = False
_HANDLERS_INSTALLED = False


def register_shutdown_app(app: Any | None) -> None:
    """Remember the MeshChat app so signal handlers can close its databases."""
    global _APP_REF, _FLUSHED
    _APP_REF = app
    _FLUSHED = False


def reset_shutdown_state_for_tests() -> None:
    global _APP_REF, _FLUSHED, _HANDLERS_INSTALLED
    _APP_REF = None
    _FLUSHED = False
    _HANDLERS_INSTALLED = False


def durable_flush_all_databases(app: Any | None = None) -> int:
    """Checkpoint and close every identity database. Idempotent.

    Returns the number of databases flushed.
    """
    global _FLUSHED
    target = app if app is not None else _APP_REF
    with _FLUSH_LOCK:
        if target is None:
            return 0
        flushed = 0
        contexts = getattr(target, "contexts", None) or {}
        for ctx in list(contexts.values()):
            database = getattr(ctx, "database", None)
            if database is None:
                continue
            try:
                durable = getattr(database, "durable_shutdown", None)
                if callable(durable):
                    durable()
                else:
                    database._checkpoint_and_close()
                flushed += 1
            except Exception as exc:
                logger.warning("durable DB flush failed: %s", exc)
        current = getattr(target, "current_context", None)
        if current is not None:
            database = getattr(current, "database", None)
            if database is not None and current not in list(contexts.values()):
                try:
                    durable = getattr(database, "durable_shutdown", None)
                    if callable(durable):
                        durable()
                    else:
                        database._checkpoint_and_close()
                    flushed += 1
                except Exception as exc:
                    logger.warning("durable DB flush (current) failed: %s", exc)
        _FLUSHED = True
        return flushed


def _detach_reticulum() -> None:
    try:
        import RNS

        with contextlib.suppress(Exception):
            RNS.Transport.detach_interfaces()
        with contextlib.suppress(Exception):
            if hasattr(RNS, "Reticulum") and hasattr(RNS.Reticulum, "exit_handler"):
                RNS.Reticulum.exit_handler()
    except Exception:
        pass


def _raise_graceful_exit() -> None:
    try:
        from aiohttp.web_runner import GracefulExit
    except Exception:
        raise KeyboardInterrupt from None
    raise GracefulExit()


def meshchat_signal_handler(signum: int, frame: FrameType | None) -> None:
    """Flush SQLite, detach RNS, then stop aiohttp cleanly."""
    try:
        print(
            f"Received signal {signum}: flushing databases before shutdown...",
            flush=True,
        )
    except Exception:
        pass
    with contextlib.suppress(Exception):
        durable_flush_all_databases()
    _detach_reticulum()
    _raise_graceful_exit()


def install_meshchat_signal_handlers(
    *,
    force: bool = False,
    signal_fn: Callable[..., Any] | None = None,
) -> bool:
    """Install MeshChat SIGINT/SIGTERM handlers on the main thread."""
    global _HANDLERS_INSTALLED
    if _HANDLERS_INSTALLED and not force:
        return True
    install = signal_fn or signal.signal
    try:
        install(signal.SIGINT, meshchat_signal_handler)
        install(signal.SIGTERM, meshchat_signal_handler)
    except ValueError:
        # signal.signal only works on the main thread
        return False
    except Exception as exc:
        logger.warning("Failed to install MeshChat signal handlers: %s", exc)
        return False
    _HANDLERS_INSTALLED = True
    return True
