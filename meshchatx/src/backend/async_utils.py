import asyncio
import sys
import threading
from collections.abc import Coroutine


class AsyncUtils:
    main_loop: asyncio.AbstractEventLoop | None = None
    _pending_futures: list = []
    _pending_coroutines: list = []
    _futures_lock = threading.Lock()
    _FUTURES_SWEEP_THRESHOLD = 64

    @staticmethod
    def apply_asyncio_313_patch():
        """Apply a patch for asyncio on Python 3.13 to avoid a bug in sendfile with SSL.
        See: https://github.com/python/cpython/issues/124448
        And: https://github.com/aio-libs/aiohttp/issues/8863
        """
        if sys.version_info >= (3, 13):
            import asyncio.base_events

            original_sendfile = asyncio.base_events.BaseEventLoop.sendfile

            async def patched_sendfile(
                self,
                transport,
                file,
                offset=0,
                count=None,
                *,
                fallback=True,
            ):
                if transport.get_extra_info("sslcontext"):
                    raise NotImplementedError(
                        "sendfile is broken on SSL transports in Python 3.13",
                    )
                return await original_sendfile(
                    self,
                    transport,
                    file,
                    offset,
                    count,
                    fallback=fallback,
                )

            asyncio.base_events.BaseEventLoop.sendfile = patched_sendfile

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
                coroutine, AsyncUtils.main_loop,
            )
            with AsyncUtils._futures_lock:
                AsyncUtils._pending_futures.append(future)
                if len(AsyncUtils._pending_futures) >= AsyncUtils._FUTURES_SWEEP_THRESHOLD:
                    AsyncUtils._pending_futures = [
                        f for f in AsyncUtils._pending_futures if not f.done()
                    ]
            return

        AsyncUtils._pending_coroutines.append(coroutine)
