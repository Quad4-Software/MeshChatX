import os
import shutil
import tempfile

import pytest

from meshchatx.src.backend.database import Database


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


def test_database_snapshot_creation(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()

    # Add some data
    db.execute_sql(
        "INSERT INTO config (key, value) VALUES (?, ?)",
        ("test_key", "test_value"),
    )

    # Create snapshot
    snapshot_name = "test_snapshot"
    db.create_snapshot(temp_dir, snapshot_name)

    snapshot_path = os.path.join(temp_dir, "snapshots", f"{snapshot_name}.zip")
    assert os.path.exists(snapshot_path)

    # List snapshots
    snapshots = db.list_snapshots(temp_dir)
    assert len(snapshots) == 1
    assert snapshots[0]["name"] == snapshot_name


def test_database_snapshot_restoration(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()

    # Add some data
    db.execute_sql("INSERT INTO config (key, value) VALUES (?, ?)", ("v1", "original"))

    # Create snapshot
    db.create_snapshot(temp_dir, "snap1")
    snapshot_path = os.path.join(temp_dir, "snapshots", "snap1.zip")

    # Modify data
    db.execute_sql("UPDATE config SET value = ? WHERE key = ?", ("modified", "v1"))
    row = db.provider.fetchone("SELECT value FROM config WHERE key = ?", ("v1",))
    assert row["value"] == "modified"

    # Restore snapshot
    db.restore_database(snapshot_path)

    # Verify data is back to original
    row = db.provider.fetchone("SELECT value FROM config WHERE key = ?", ("v1",))
    assert row is not None
    assert row["value"] == "original"


def test_database_auto_backup_logic(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()

    # Should create a timestamped backup
    result = db.backup_database(temp_dir)
    assert "database-backups" in result["path"]
    assert os.path.exists(result["path"])

    backup_dir = os.path.join(temp_dir, "database-backups")
    assert len(os.listdir(backup_dir)) == 1
