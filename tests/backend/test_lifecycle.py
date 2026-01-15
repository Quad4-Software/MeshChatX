import gc
import os
import shutil
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.identity_context import IdentityContext
from meshchatx.src.backend.web_audio_bridge import WebAudioBridge


def test_database_provider_disposal():
    """Test that DatabaseProvider correctly closes connections."""
    db_path = os.path.join(tempfile.gettempdir(), "test_disposal.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    # Ensure any existing singleton is cleared
    DatabaseProvider._instance = None

    try:
        provider = DatabaseProvider.get_instance(db_path)
        conn = provider.connection
        assert isinstance(conn, sqlite3.Connection)

        # Test close()
        provider.close()
        with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
            conn.execute("SELECT 1")

        # Re-open
        conn2 = provider.connection
        assert conn2 is not conn

        # Test close_all()
        provider.close_all()
        with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
            conn2.execute("SELECT 1")

    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
        DatabaseProvider._instance = None


def test_web_audio_bridge_disposal():
    """Test that WebAudioBridge correctly manages clients and cleanup."""
    mock_tele_mgr = MagicMock()
    mock_config_mgr = MagicMock()
    bridge = WebAudioBridge(mock_tele_mgr, mock_config_mgr)

    mock_client = MagicMock()
    mock_tele = MagicMock()
    mock_tele.active_call = True
    mock_tele_mgr.telephone = mock_tele

    with (
        patch("meshchatx.src.backend.web_audio_bridge.WebAudioSource"),
        patch("meshchatx.src.backend.web_audio_bridge.WebAudioSink"),
        patch("meshchatx.src.backend.web_audio_bridge.Tee"),
        patch("meshchatx.src.backend.web_audio_bridge.Pipeline"),
    ):
        bridge.attach_client(mock_client)
        assert mock_client in bridge.clients

        bridge.on_call_ended()
        assert bridge.tx_source is None
        assert bridge.rx_sink is None
        assert len(bridge.clients) == 0


def test_identity_context_teardown_completeness():
    """Verify that teardown cleans up all major components."""
    mock_identity = MagicMock(spec=RNS.Identity)
    mock_identity.hash = b"test_hash_32_bytes_long_01234567"
    mock_identity.get_private_key.return_value = b"mock_pk"

    mock_app = MagicMock()
    mock_app.storage_dir = tempfile.mkdtemp()

    with (
        patch("meshchatx.src.backend.identity_context.Database"),
        patch("meshchatx.src.backend.identity_context.ConfigManager"),
        patch("meshchatx.src.backend.identity_context.create_lxmf_router"),
        patch("meshchatx.src.backend.identity_context.IntegrityManager"),
        patch(
            "meshchatx.src.backend.identity_context.AutoPropagationManager",
        ),
    ):
        context = IdentityContext(mock_identity, mock_app)
        context.start_background_threads = MagicMock()
        context.register_announce_handlers = MagicMock()

        context.setup()

        # Capture instances
        db_instance = context.database
        auto_prop_instance = context.auto_propagation_manager

        context.teardown()

        # Verify component cleanup
        db_instance._checkpoint_and_close.assert_called()
        auto_prop_instance.stop.assert_called()
        assert context.running is False


def test_identity_context_memory_leak():
    """Verify that IdentityContext can be garbage collected after teardown."""
    mock_identity = MagicMock(spec=RNS.Identity)
    mock_identity.hash = b"leak_test_hash_32_bytes_long_012"
    mock_identity.get_private_key.return_value = b"mock_pk"
    mock_app = MagicMock()
    mock_app.storage_dir = tempfile.mkdtemp()

    import weakref

    # We use a list to store the ref so we can access it after the function scope
    leak_ref = []

    def run_lifecycle():
        with (
            patch("meshchatx.src.backend.identity_context.Database"),
            patch("meshchatx.src.backend.identity_context.ConfigManager"),
            patch("meshchatx.src.backend.identity_context.create_lxmf_router"),
            patch("meshchatx.src.backend.identity_context.IntegrityManager"),
            patch("RNS.Transport"),
        ):
            context = IdentityContext(mock_identity, mock_app)
            context.start_background_threads = MagicMock()
            context.register_announce_handlers = MagicMock()
            context.setup()
            context.teardown()

            leak_ref.append(weakref.ref(context))
            # End of with block and function scope should clear 'context'

    run_lifecycle()

    # Break any potential cycles in the app mock which might have captured the context
    mock_app.reset_mock()

    # Multiple collection rounds
    for _ in range(5):
        gc.collect()

    # Check if it was collected
    assert leak_ref[0]() is None, "IdentityContext was not garbage collected"


@settings(deadline=None)
@given(st.integers(min_value=1, max_value=3))
def test_identity_context_repeated_lifecycle(n):
    """Fuzz the lifecycle by repeating setup/teardown multiple times with new instances."""
    mock_identity = MagicMock(spec=RNS.Identity)
    mock_identity.hash = b"fuzz_hash_32_bytes_long_01234567"
    mock_identity.get_private_key.return_value = b"mock_pk"

    mock_app = MagicMock()
    mock_app.storage_dir = tempfile.mkdtemp()

    with (
        patch("meshchatx.src.backend.identity_context.Database"),
        patch("meshchatx.src.backend.identity_context.ConfigManager"),
        patch("meshchatx.src.backend.identity_context.create_lxmf_router"),
        patch("meshchatx.src.backend.identity_context.IntegrityManager"),
        patch("RNS.Transport"),
    ):
        for _ in range(n):
            context = IdentityContext(mock_identity, mock_app)
            context.start_background_threads = MagicMock()
            context.register_announce_handlers = MagicMock()
            context.setup()
            assert context.running is True
            context.teardown()
            assert context.running is False

    if os.path.exists(mock_app.storage_dir):
        shutil.rmtree(mock_app.storage_dir)
