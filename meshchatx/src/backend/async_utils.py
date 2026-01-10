import asyncio
import sys
from collections.abc import Coroutine


class AsyncUtils:
    # remember main loop
    main_loop: asyncio.AbstractEventLoop | None = None

    @staticmethod
    def apply_asyncio_313_patch():
        """Apply a patch for asyncio on Python 3.13 to avoid a bug in sendfile with SSL.
        See: https://github.com/python/cpython/issues/124448
        And: https://github.com/aio-libs/aiohttp/issues/8863
        """
        if sys.version_info >= (3, 13):
            import asyncio.base_events

            # We need to patch the loop's sendfile to raise NotImplementedError for SSL transports.
            # This will force aiohttp to use its own fallback which works correctly.

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

    # this method allows running the provided async coroutine from within a sync function
    # it will run the async function on the main event loop if possible, otherwise it logs a warning
    @staticmethod
    def run_async(coroutine: Coroutine):
        # run provided coroutine on main event loop, ensuring thread safety
        if AsyncUtils.main_loop and AsyncUtils.main_loop.is_running():
            asyncio.run_coroutine_threadsafe(coroutine, AsyncUtils.main_loop)
            return

        # main event loop not running...
        print("WARNING: Main event loop not available. Could not schedule task.")
