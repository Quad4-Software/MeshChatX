# SPDX-License-Identifier: 0BSD

"""Thread-safe scheduling helpers for the MeshChatX asyncio event loop."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from collections.abc import Coroutine
from typing import Any, ClassVar

_logger = logging.getLogger("meshchatx.async")


class AsyncUtils:
    """Bridge between sync threads and a shared asyncio loop."""

    main_loop: asyncio.AbstractEventLoop | None = None
    _pending_futures: ClassVar[list[Any]] = []
    _pending_coroutines: ClassVar[list[Any]] = []
    _futures_lock = threading.Lock()
    _FUTURES_SWEEP_THRESHOLD = 32
    _COROUTINES_MAX = 256
    _background_loop: asyncio.AbstractEventLoop | None = None
    _background_thread: threading.Thread | None = None
    _background_ready = threading.Event()

    @staticmethod
    def ensure_background_loop() -> None:
        """Start a daemon loop when the web-server loop is not running yet."""
        if AsyncUtils.main_loop and AsyncUtils.main_loop.is_running():
            return
        if AsyncUtils._background_thread and AsyncUtils._background_thread.is_alive():
            return

        loop = asyncio.new_event_loop()
        AsyncUtils._background_ready.clear()

        def runner() -> None:
            AsyncUtils.set_main_loop(loop)
            AsyncUtils._background_ready.set()
            loop.run_forever()

        AsyncUtils._background_loop = loop
        AsyncUtils._background_thread = threading.Thread(
            target=runner,
            name="meshchatx-async",
            daemon=True,
        )
        AsyncUtils._background_thread.start()
        if not AsyncUtils._background_ready.wait(timeout=5):
            _logger.warning("Background asyncio loop did not become ready within 5s")

    @staticmethod
    def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
        """Install the process main loop and drain any buffered coroutines."""
        # Swap the buffer under the lock so a run_async caller racing the
        # loop install lands either in the drained list (scheduled below)
        # or takes the live-loop path, never into a list nobody reads.
        with AsyncUtils._futures_lock:
            AsyncUtils.main_loop = loop
            pending = AsyncUtils._pending_coroutines
            AsyncUtils._pending_coroutines = []
        # Schedule directly on the loop: it may not be running yet (the
        # installer calls this before run_forever), but run_coroutine_
        # threadsafe queues the coroutine for when the loop starts.
        for coro in pending:
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            with AsyncUtils._futures_lock:
                AsyncUtils._pending_futures.append(future)

    @staticmethod
    def run_async(coroutine: Coroutine) -> Any:
        """Schedule a coroutine on the main loop from any thread.

        Finished futures are pruned so closures can be collected promptly.
        When no loop is running, coroutines are buffered up to a fixed cap.
        """
        with AsyncUtils._futures_lock:
            loop = AsyncUtils.main_loop
            if loop is not None and loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    coroutine,
                    loop,
                )
                AsyncUtils._pending_futures.append(future)
                if (
                    len(AsyncUtils._pending_futures)
                    >= AsyncUtils._FUTURES_SWEEP_THRESHOLD
                ):
                    AsyncUtils._pending_futures = [
                        item for item in AsyncUtils._pending_futures if not item.done()
                    ]
                return future

            # If the loop isn't available yet (or has stopped), buffer the
            # coroutine but cap the backlog so we don't leak memory forever.
            AsyncUtils._pending_coroutines.append(coroutine)
            if len(AsyncUtils._pending_coroutines) > AsyncUtils._COROUTINES_MAX:
                overflow = AsyncUtils._pending_coroutines[
                    : len(AsyncUtils._pending_coroutines) - AsyncUtils._COROUTINES_MAX
                ]
                AsyncUtils._pending_coroutines = AsyncUtils._pending_coroutines[
                    -AsyncUtils._COROUTINES_MAX :
                ]
                # Close dropped coroutines so their destruction does not emit
                # RuntimeWarning: coroutine was never awaited.
                for stale in overflow:
                    with contextlib.suppress(Exception):
                        stale.close()
                _logger.warning(
                    "Dropped %d buffered coroutine(s) because the event loop is not running",
                    len(overflow),
                )
            return None
