# SPDX-License-Identifier: 0BSD AND MIT

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any, ClassVar


class AsyncUtils:
    main_loop: asyncio.AbstractEventLoop | None = None
    _pending_futures: ClassVar[list[Any]] = []
    _pending_coroutines: ClassVar[list[Any]] = []
    _futures_lock = threading.Lock()
    _FUTURES_SWEEP_THRESHOLD = 32
    _COROUTINES_MAX = 256

    @staticmethod
    def set_main_loop(loop: asyncio.AbstractEventLoop):
        AsyncUtils.main_loop = loop
        for coro in AsyncUtils._pending_coroutines:
            AsyncUtils.run_async(coro)
        AsyncUtils._pending_coroutines.clear()

    @staticmethod
    def run_async(coroutine: Coroutine):
        """Schedule *coroutine* on the main event loop from any thread.

        Returned futures are tracked so they (and the closures they reference)
        can be garbage-collected promptly once finished.
        """
        if AsyncUtils.main_loop and AsyncUtils.main_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                coroutine,
                AsyncUtils.main_loop,
            )
            with AsyncUtils._futures_lock:
                AsyncUtils._pending_futures.append(future)
                if (
                    len(AsyncUtils._pending_futures)
                    >= AsyncUtils._FUTURES_SWEEP_THRESHOLD
                ):
                    AsyncUtils._pending_futures = [
                        f for f in AsyncUtils._pending_futures if not f.done()
                    ]
            return

        # If the loop isn't available yet (or has stopped), buffer the coroutine
        # but cap the backlog so we don't leak memory indefinitely.
        AsyncUtils._pending_coroutines.append(coroutine)
        if len(AsyncUtils._pending_coroutines) > AsyncUtils._COROUTINES_MAX:
            dropped = len(AsyncUtils._pending_coroutines) - AsyncUtils._COROUTINES_MAX
            AsyncUtils._pending_coroutines = AsyncUtils._pending_coroutines[
                -AsyncUtils._COROUTINES_MAX :
            ]
            import logging

            logging.getLogger("meshchatx.async").warning(
                "Dropped %d buffered coroutine(s) because the event loop is not running",
                dropped,
            )
