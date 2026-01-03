import os
import sqlite3
import tempfile
import pytest
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema
from meshchatx.src.backend.database.legacy_migrator import LegacyMigrator


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_database_initialization(temp_db):
    provider = DatabaseProvider(temp_db)
    schema = DatabaseSchema(provider)
    schema.initialize()

    # Check if tables were created
    tables = provider.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [row["name"] for row in tables]

    assert "config" in table_names
    assert "lxmf_messages" in table_names
    assert "announces" in table_names

    # Check version
    version_row = provider.fetchone(
        "SELECT value FROM config WHERE key = 'database_version'"
    )
    assert int(version_row["value"]) == DatabaseSchema.LATEST_VERSION

    provider.close()


def test_legacy_migrator_detection(temp_db):
    # Setup current DB
    provider = DatabaseProvider(temp_db)
    schema = DatabaseSchema(provider)
    schema.initialize()

    # Setup a "legacy" DB in a temp directory
    with tempfile.TemporaryDirectory() as legacy_dir:
        identity_hash = "deadbeef"
        legacy_identity_dir = os.path.join(legacy_dir, "identities", identity_hash)
        os.makedirs(legacy_identity_dir)
        legacy_db_path = os.path.join(legacy_identity_dir, "database.db")

        legacy_conn = sqlite3.connect(legacy_db_path)
        legacy_conn.execute("CREATE TABLE config (key TEXT, value TEXT)")
        legacy_conn.execute(
            "INSERT INTO config (key, value) VALUES ('display_name', 'Legacy User')"
        )
        legacy_conn.commit()
        legacy_conn.close()

        migrator = LegacyMigrator(provider, legacy_dir, identity_hash)
        assert migrator.get_legacy_db_path() == legacy_db_path
        assert migrator.should_migrate() is True

    provider.close()


def test_legacy_migration_data(temp_db):
    provider = DatabaseProvider(temp_db)
    schema = DatabaseSchema(provider)
    schema.initialize()

    with tempfile.TemporaryDirectory() as legacy_dir:
        identity_hash = "deadbeef"
        legacy_identity_dir = os.path.join(legacy_dir, "identities", identity_hash)
        os.makedirs(legacy_identity_dir)
        legacy_db_path = os.path.join(legacy_identity_dir, "database.db")

        # Create legacy DB with some data
        legacy_conn = sqlite3.connect(legacy_db_path)
        legacy_conn.execute(
            "CREATE TABLE lxmf_messages (hash TEXT UNIQUE, content TEXT)"
        )
        legacy_conn.execute(
            "INSERT INTO lxmf_messages (hash, content) VALUES ('msg1', 'Hello Legacy')"
        )
        legacy_conn.execute("CREATE TABLE config (key TEXT UNIQUE, value TEXT)")
        legacy_conn.execute(
            "INSERT INTO config (key, value) VALUES ('test_key', 'test_val')"
        )
        legacy_conn.commit()
        legacy_conn.close()

        migrator = LegacyMigrator(provider, legacy_dir, identity_hash)
        assert migrator.migrate() is True

        # Verify data moved
        msg_row = provider.fetchone(
            "SELECT content FROM lxmf_messages WHERE hash = 'msg1'"
        )
        assert msg_row["content"] == "Hello Legacy"

        config_row = provider.fetchone(
            "SELECT value FROM config WHERE key = 'test_key'"
        )
        assert config_row["value"] == "test_val"

    provider.close()
