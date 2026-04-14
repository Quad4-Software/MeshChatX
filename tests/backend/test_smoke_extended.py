import os
import sqlite3
import subprocess
import sys
import tempfile

import pytest


def test_cli_help():
    """Smoke test for --help flag."""
    result = subprocess.run(
        [sys.executable, "-m", "meshchatx.meshchat", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower() or "options:" in result.stdout.lower()


def test_import_all_backend_modules():
    """Smoke test to ensure all backend modules can be imported without error."""
    import importlib

    backend_path = "meshchatx.src.backend"
    root_dir = os.path.join("meshchatx", "src", "backend")

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                rel_path = os.path.relpath(os.path.join(root, file), root_dir)
                module_name = rel_path.replace(os.sep, ".").replace(".py", "")
                full_module_name = f"{backend_path}.{module_name}"
                try:
                    importlib.import_module(full_module_name)
                except Exception as e:
                    # Skip some modules that might need special environment
                    if "bot_process" in full_module_name:
                        continue
                    pytest.fail(f"Failed to import {full_module_name}: {e}")


def test_database_migration_smoke():
    """Smoke test for database migrations from version 0 to latest."""
    from meshchatx.src.backend.database.provider import DatabaseProvider
    from meshchatx.src.backend.database.schema import DatabaseSchema

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_migration.db")
        provider = DatabaseProvider(db_path)
        schema = DatabaseSchema(provider)

        # Initialize (runs all migrations)
        schema.initialize()

        # Verify it reached the latest version
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = 'database_version'")
        row = cursor.fetchone()
        assert row is not None
        assert int(row["value"]) == DatabaseSchema.LATEST_VERSION
        conn.close()


def test_markdown_renderer_smoke():
    """Smoke test for MarkdownRenderer with basic markdown."""
    from meshchatx.src.backend.markdown_renderer import MarkdownRenderer

    basic_md = "# Hello\nThis is **bold** and *italic*."
    result = MarkdownRenderer.render(basic_md)
    assert "Hello" in result
    assert "<h1" in result
    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result

    list_md = "* item 1\n* item 2"
    result = MarkdownRenderer.render(list_md)
    assert "<ul" in result
    assert "item 1" in result


def test_config_manager_smoke():
    """Smoke test for ConfigManager basic operations."""
    from meshchatx.src.backend.config_manager import ConfigManager
    from meshchatx.src.backend.database import Database

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_config.db")
        # Use the high-level Database class which has the expected structure
        db = Database(db_path)
        db.initialize()

        config = ConfigManager(db)

        # Test default value
        assert config.display_name.get() == "Anonymous Peer"

        # Test set and get
        config.display_name.set("New Name")
        assert config.display_name.get() == "New Name"

        # Test boolean
        assert config.auto_announce_enabled.get() is False
        config.auto_announce_enabled.set(True)
        assert config.auto_announce_enabled.get() is True

        assert config.announce_max_stored_lxmf_delivery.get() == 1000
        assert config.announce_fetch_limit_lxmf_delivery.get() == 500
        assert config.discovered_interfaces_max_return.get() == 500


def test_telephone_manager_smoke():
    """Smoke test for TelephoneManager initialization."""
    import RNS

    from meshchatx.src.backend.telephone_manager import TelephoneManager

    # Mock identity
    identity = RNS.Identity()
    manager = TelephoneManager(identity)
    assert manager.identity == identity
    assert manager.telephone is None  # Should be None until init_telephone


def test_voicemail_manager_smoke():
    """Smoke test for VoicemailManager initialization."""
    from unittest.mock import MagicMock

    from meshchatx.src.backend.voicemail_manager import VoicemailManager

    mock_db = MagicMock()
    mock_config = MagicMock()
    mock_tm = MagicMock()
    tmp_dir = tempfile.mkdtemp()

    try:
        manager = VoicemailManager(mock_db, mock_config, mock_tm, tmp_dir)
        assert manager.db == mock_db
        assert os.path.exists(os.path.join(tmp_dir, "voicemails", "recordings"))
    finally:
        import shutil

        shutil.rmtree(tmp_dir)


def test_lxst_smoke():
    """Smoke test for LXST import and basic structure."""
    import LXST

    assert hasattr(LXST, "Telephone") or hasattr(LXST, "Pipeline")


def test_identity_context_smoke():
    """Smoke test for IdentityContext creation."""
    from unittest.mock import MagicMock

    import RNS

    from meshchatx.src.backend.identity_context import IdentityContext

    identity = RNS.Identity()
    mock_app = MagicMock()
    mock_app.storage_dir = tempfile.mkdtemp()

    try:
        ctx = IdentityContext(identity, mock_app)
        assert ctx.identity == identity
        assert ctx.identity_hash == identity.hash.hex()
    finally:
        import shutil

        shutil.rmtree(mock_app.storage_dir)


def test_announce_manager_smoke():
    """Smoke test for AnnounceManager."""
    from unittest.mock import MagicMock

    from meshchatx.src.backend.announce_manager import AnnounceManager

    mock_db = MagicMock()
    manager = AnnounceManager(mock_db)
    assert manager.db == mock_db


def test_rnstatus_handler_smoke():
    """Smoke test for RNStatusHandler."""
    from unittest.mock import MagicMock

    from meshchatx.src.backend.rnstatus_handler import RNStatusHandler

    mock_rns = MagicMock()
    handler = RNStatusHandler(mock_rns)
    assert handler.reticulum == mock_rns


def test_lxmf_router_creation_smoke():
    """Smoke test for create_lxmf_router utility."""
    from unittest.mock import patch

    import RNS

    from meshchatx.src.backend.meshchat_utils import create_lxmf_router

    identity = RNS.Identity()
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("LXMF.LXMRouter") as mock_router:
            create_lxmf_router(identity, tmpdir)
            mock_router.assert_called()
