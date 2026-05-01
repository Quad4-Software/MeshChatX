# SPDX-License-Identifier: 0BSD

import os
import tempfile

import pytest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


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
        "SELECT value FROM config WHERE key = 'database_version'",
    )
    assert int(version_row["value"]) == DatabaseSchema.LATEST_VERSION

    provider.close()


def test_database_health_snapshot_free_space(temp_db):
    db = Database(temp_db)
    db.initialize()
    health = db.get_database_health_snapshot()
    assert "estimated_free_bytes" in health
    assert health["estimated_free_bytes"] >= 0
    assert health["journal_mode"] == "wal"
    assert health["freelist_pages"] == 0
    assert health["estimated_free_bytes"] > 0
