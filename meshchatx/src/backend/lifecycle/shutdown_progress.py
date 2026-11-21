# SPDX-License-Identifier: 0BSD

"""Structured shutdown progress reporting plus a hard exit watchdog.

The desktop shell polls the status file while it waits for the backend to
exit, and stdout lines let packagers and tests follow the same steps. A
daemon watchdog force-exits the process past a bounded deadline so a stuck
RNS thread can never leave the app looking frozen. Databases are always
flushed before the watchdog can matter, so the kill is safe.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import tempfile
import threading
import time
from collections.abc import Awaitable, Callable
from typing import Any

from meshchatx.src.env_utils import env_str

logger_name = "meshchatx.shutdown"

DEFAULT_DEADLINE_S = 10.0
_STATUS_ENV = "MESHCHATX_SHUTDOWN_STATUS"

_progress: ShutdownProgress | None = None
_watchdog_started = False


def default_status_path(storage_dir: str) -> str:
    return os.path.join(storage_dir, "logs", "shutdown-status.json")


class ShutdownProgress:
    """Writes each shutdown step to a JSON file and stdout."""

    def __init__(
        self,
        path: str | None,
        *,
        clock: Callable[[], float] = time.monotonic,
        printer: Callable[[str], None] | None = None,
        deadline_s: float = DEFAULT_DEADLINE_S,
    ) -> None:
        self.path = path
        self.clock = clock
        self.printer = printer or self._default_print
        self.deadline_s = deadline_s
        self.seq = 0
        self.started = clock()

    @staticmethod
    def _default_print(line: str) -> None:
        print(line, flush=True)

    def report(self, step: str, detail: str = "") -> None:
        self.seq += 1
        elapsed_ms = int((self.clock() - self.started) * 1000)
        line = f"[shutdown] {step}" + (f": {detail}" if detail else "")
        with contextlib.suppress(Exception):
            self.printer(line)
        if not self.path:
            return
        payload = {
            "seq": self.seq,
            "step": step,
            "detail": detail,
            "elapsed_ms": elapsed_ms,
            "deadline_s": self.deadline_s,
        }
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                dir=os.path.dirname(self.path), prefix=".shutdown-", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as fh:
                    fh.write(json.dumps(payload))
                os.replace(tmp, self.path)
            except BaseException:
                with contextlib.suppress(Exception):
                    os.unlink(tmp)
                raise
        except Exception:
            pass


def init_progress(
    storage_dir: str | None, *, deadline_s: float = DEFAULT_DEADLINE_S
) -> ShutdownProgress:
    """Create the process-wide reporter. The env var overrides the path."""
    global _progress
    path = env_str(_STATUS_ENV) or (
        default_status_path(storage_dir) if storage_dir else None
    )
    _progress = ShutdownProgress(path, deadline_s=deadline_s)
    if path:
        with contextlib.suppress(Exception):
            os.unlink(path)
    return _progress


def get_progress() -> ShutdownProgress:
    global _progress
    if _progress is None:
        _progress = init_progress(None)
    return _progress


def reset_for_tests() -> None:
    global _progress, _watchdog_started
    _progress = None
    _watchdog_started = False


def arm_watchdog(
    seconds: float = DEFAULT_DEADLINE_S,
    *,
    exit_fn: Callable[[int], Any] | None = None,
    on_fire: Callable[[], None] | None = None,
) -> Callable[[], None]:
    """Force-exit the process if shutdown is still running past `seconds`.

    The default path uses faulthandler's C-level timer, which fires even
    when the main thread is blocked in native code holding the GIL. A
    Python thread cannot promise that. exit_fn and on_fire exist for
    tests, which swap in a daemon thread instead. Returns a disarm
    callable.
    """
    global _watchdog_started
    if _watchdog_started:
        return lambda: None
    _watchdog_started = True

    if exit_fn is None and on_fire is None:
        import faulthandler

        faulthandler.dump_traceback_later(seconds, exit=True)

        def disarm() -> None:
            global _watchdog_started
            _watchdog_started = False
            with contextlib.suppress(Exception):
                faulthandler.cancel_dump_traceback_later()

        return disarm

    fired = threading.Event()
    real_exit = exit_fn if exit_fn is not None else os._exit

    def _watch() -> None:
        if fired.wait(seconds):
            return
        if on_fire is not None:
            with contextlib.suppress(Exception):
                on_fire()
        else:
            with contextlib.suppress(Exception):
                print(
                    f"[shutdown] hard deadline {seconds}s reached, forcing exit",
                    flush=True,
                )
        real_exit(124)

    threading.Thread(target=_watch, name="mcx-shutdown-watchdog", daemon=True).start()

    def disarm() -> None:
        global _watchdog_started
        _watchdog_started = False
        fired.set()

    return disarm


async def run_step(
    progress: ShutdownProgress,
    name: str,
    fn: Callable[[], Any],
    *,
    timeout: float,
    detail: str = "",
) -> None:
    """Run a blocking teardown step in a thread with a bounded wait.

    A timed-out step logs and moves on. The thread may linger but the
    watchdog bounds total exit time.
    """
    progress.report(name, detail)
    try:
        await asyncio.wait_for(asyncio.to_thread(fn), timeout=timeout)
    except TimeoutError:
        progress.report(name, f"timed out after {timeout}s, continuing")
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        progress.report(name, f"failed: {exc}")


async def run_step_async(
    progress: ShutdownProgress,
    name: str,
    awaitable_fn: Callable[[], Awaitable[Any]],
    *,
    timeout: float,
    detail: str = "",
) -> None:
    """Async variant of run_step for coroutine teardown steps."""
    progress.report(name, detail)
    try:
        await asyncio.wait_for(awaitable_fn(), timeout=timeout)
    except TimeoutError:
        progress.report(name, f"timed out after {timeout}s, continuing")
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        progress.report(name, f"failed: {exc}")
