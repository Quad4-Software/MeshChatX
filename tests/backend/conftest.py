import asyncio
import os
import tempfile
from unittest.mock import patch

import pytest

# Set log dir to a temporary directory for tests to avoid permission issues
# in restricted environments like sandboxes.
os.environ["MESHCHAT_LOG_DIR"] = tempfile.mkdtemp()


@pytest.fixture(autouse=True)
def global_mocks():
    with (
        patch("meshchatx.meshchat.AsyncUtils") as mock_async_utils,
        patch(
            "meshchatx.src.backend.identity_context.IdentityContext.start_background_threads",
            return_value=None,
        ),
        patch("meshchatx.meshchat.generate_ssl_certificate", return_value=None),
        patch("asyncio.sleep", side_effect=lambda *args, **kwargs: asyncio.sleep(0)),
    ):
        # Mock run_async to properly close coroutines
        def mock_run_async(coro):
            if asyncio.iscoroutine(coro):
                try:
                    # If it's a coroutine, we should close it if it's not being awaited
                    coro.close()
                except RuntimeError:
                    pass
            elif hasattr(coro, "__await__"):
                # Handle other awaitables
                pass

        mock_async_utils.run_async.side_effect = mock_run_async

        yield {
            "async_utils": mock_async_utils,
        }


@pytest.fixture(autouse=True)
def cleanup_sqlite_connections():
    yield
    # After each test, try to close any lingering sqlite connections if possible
    # This is a bit hard globally without tracking them, but we can at least
    # trigger GC which often helps with ResourceWarnings.
    import gc

    gc.collect()
