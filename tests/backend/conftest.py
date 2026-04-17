# SPDX-License-Identifier: 0BSD

import asyncio
import os
import socket
import tempfile
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.config_manager import ConfigManager
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema

# Set log dir to a temporary directory for tests to avoid permission issues
# in restricted environments like sandboxes.
os.environ["MESHCHAT_LOG_DIR"] = tempfile.mkdtemp()


@pytest.fixture(scope="session")
def loopback_available():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    accepted = None
    try:
        server.settimeout(0.5)
        client.settimeout(0.5)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        client.connect(("127.0.0.1", port))
        accepted, _ = server.accept()
        return True
    except OSError:
        return False
    finally:
        if accepted is not None:
            accepted.close()
        client.close()
        server.close()


@pytest.fixture
def require_loopback_tcp(loopback_available):
    if not loopback_available:
        pytest.skip("Loopback TCP is blocked by local firewall/policy; skipping localhost integration test.")


@pytest.fixture(autouse=True)
def global_mocks():
    with (
        patch("meshchatx.meshchat.AsyncUtils") as mock_async_utils,
        patch(
            "meshchatx.src.backend.identity_context.IdentityContext.start_background_threads",
            return_value=None,
        ),
        patch("meshchatx.meshchat.generate_ssl_certificate", return_value=None),
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
    import gc

    gc.collect()


@pytest.fixture
def temp_db(tmp_path):
    db_path = os.path.join(tmp_path, "test_meshchat.db")
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def db(temp_db):
    provider = DatabaseProvider(temp_db)
    schema = DatabaseSchema(provider)
    schema.initialize()
    database = Database(temp_db)
    yield database
    database.close_all()
    provider.close_all()


@pytest.fixture
def mock_app(db, tmp_path, temp_db):
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"test_hash_32_bytes_long_01234567"
            self.hexhash = self.hash.hex()

    with ExitStack() as stack:
        stack.enter_context(patch("RNS.Identity", MockIdentityClass))
        stack.enter_context(patch("RNS.Reticulum"))
        stack.enter_context(patch("RNS.Transport"))
        stack.enter_context(patch("LXMF.LXMRouter"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.TelephoneManager"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.VoicemailManager"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RingtoneManager"),
        )
        stack.enter_context(patch("meshchatx.src.backend.identity_context.RNCPHandler"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RNStatusHandler"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RNProbeHandler"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.TranslatorHandler"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.ArchiverManager"),
        )
        stack.enter_context(patch("meshchatx.src.backend.identity_context.MapManager"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.MessageHandler"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.AnnounceManager"),
        )
        stack.enter_context(patch("threading.Thread"))

        mock_id = MockIdentityClass()
        mock_id.get_private_key = MagicMock(return_value=b"test_private_key")

        stack.enter_context(
            patch.object(MockIdentityClass, "from_file", return_value=mock_id),
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "recall", return_value=mock_id),
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "from_bytes", return_value=mock_id),
        )

        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "announce_loop",
                new=MagicMock(return_value=None),
            ),
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "announce_sync_propagation_nodes",
                new=MagicMock(return_value=None),
            ),
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "crawler_loop",
                new=MagicMock(return_value=None),
            ),
        )

        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "auto_backup_loop",
                new=MagicMock(return_value=None),
            ),
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "send_config_to_websocket_clients",
                return_value=None,
            ),
        )

        app = ReticulumMeshChat(
            identity=mock_id,
            storage_dir=str(tmp_path),
            reticulum_config_dir=str(tmp_path),
        )

        # DatabaseProvider is a singleton; IdentityContext.setup() opens the identity DB
        # and replaces the singleton. Recreate the test DB handle so config and DAOs use
        # a live provider for the same path as the db fixture.
        app.database = Database(temp_db)
        app.current_context.config = ConfigManager(app.database)
        app.websocket_broadcast = MagicMock(side_effect=lambda data: None)

        yield app
        app.teardown_identity()
