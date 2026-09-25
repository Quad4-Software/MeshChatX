# SPDX-License-Identifier: 0BSD AND MIT

import asyncio
import contextlib
import logging
import threading
from collections.abc import Coroutine
from typing import Any, ClassVar

_logger = logging.getLogger("meshchatx.async")


class AsyncUtils:
    main_loop: asyncio.AbstractEventLoop | None = None
    _pending_futures: ClassVar[list[Any]] = []
    _pending_coroutines: ClassVar[list[Any]] = []
    _futures_lock = threading.Lock()
    _FUTURES_SWEEP_THRESHOLD = 32
    _COROUTINES_MAX = 256
    _background_loop: asyncio.AbstractEventLoop | None = None
    _background_thread: threading.Thread | None = None
    _background_ready = threading.Event()
    # Optional loop exception reporter, installed by CrashRecovery so task
    # exceptions that never reach sys.excepthook still get diagnosed.
    _exception_handler = None

    @staticmethod
    def ensure_background_loop() -> None:
        """Start a daemon event loop for pre-web-server async work."""
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
    def set_exception_handler(handler) -> None:
        """Install a loop exception handler on all known loops.

        Safe to call before loops exist: set_main_loop applies the stored
        handler to each loop it registers. Passing None restores default
        handling on every registered loop.
        """
        AsyncUtils._exception_handler = handler
        for loop in (AsyncUtils.main_loop, AsyncUtils._background_loop):
            AsyncUtils._apply_exception_handler(loop)

    @staticmethod
    def _apply_exception_handler(loop) -> None:
        if not isinstance(loop, asyncio.AbstractEventLoop) or loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(
                loop.set_exception_handler,
                AsyncUtils._exception_handler,
            )
        except RuntimeError:
            pass

    @staticmethod
    def set_main_loop(loop: asyncio.AbstractEventLoop):
        # Swap the buffer under the lock so a run_async caller racing the
        # loop install lands either in the drained list (scheduled below)
        # or takes the live-loop path, never into a list nobody reads.
        with AsyncUtils._futures_lock:
            AsyncUtils.main_loop = loop
            pending = AsyncUtils._pending_coroutines
            AsyncUtils._pending_coroutines = []
        AsyncUtils._apply_exception_handler(loop)
        # Schedule directly on the loop: it may not be running yet (the
        # installer calls this before run_forever), but run_coroutine_
        # threadsafe queues the coroutine for when the loop starts.
        for coro in pending:
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            with AsyncUtils._futures_lock:
                AsyncUtils._pending_futures.append(future)

    @staticmethod
    def spawn_background(coroutine: Coroutine):
        """Schedule a long-lived coroutine on the shared background loop.

        Identity-scoped periodic loops used to each get a dedicated thread
        running asyncio.run(), where a whole event loop per timer wastes a
        thread stack and a thread-local SQLite connection per task. They now share
        the meshchatx-async loop. Blocking work inside them must use
        asyncio.to_thread so the other tasks on the loop are not stalled.
        """
        AsyncUtils.ensure_background_loop()
        loop = AsyncUtils._background_loop
        if loop is None or loop.is_closed():
            # No loop available (early teardown, tests), so keep the old
            # behaviour and run the task on a dedicated thread.
            thread = threading.Thread(
                target=asyncio.run,
                args=(coroutine,),
                daemon=True,
            )
            thread.start()
            return thread

        future = asyncio.run_coroutine_threadsafe(coroutine, loop)

        def _done(fut):
            if fut.cancelled():
                return
            exc = fut.exception()
            if exc is not None:
                _logger.error("Background task failed: %s", exc)

        future.add_done_callback(_done)
        return future

    @staticmethod
    def run_async(coroutine: Coroutine):
        """Schedule *coroutine* on the main event loop from any thread.

        Returned futures are tracked so they (and the closures they reference)
        can be garbage-collected promptly once finished.
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
                        f for f in AsyncUtils._pending_futures if not f.done()
                    ]
                return

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


def call_soon_threadsafe_or_none(
    loop: asyncio.AbstractEventLoop,
    callback,
    *args,
) -> bool:
    """Schedule callback on loop from another thread, False when closed.

    RNS transport-thread callbacks fire after the owning web or identity
    loop may have shut down. call_soon_threadsafe raises RuntimeError on a
    closed loop, which would surface as an unhandled exception in the RNS
    thread; the waiter is gone by then, so dropping the callback is correct.
    """
    try:
        loop.call_soon_threadsafe(callback, *args)
        return True
    except RuntimeError:
        return False
