"""Path safety: backup/snapshot delete must not escape storage directories."""

import os

import pytest

from meshchatx.src.backend.database import Database


def test_delete_database_backup_rejects_path_outside_storage(tmp_path):
    db_path = tmp_path / "t.db"
    db = Database(str(db_path))
    db.initialize()
    storage = str(tmp_path)
    os.makedirs(os.path.join(storage, "database-backups"), exist_ok=True)
    with pytest.raises(ValueError, match="Invalid path"):
        db.delete_snapshot_or_backup(
            storage,
            "../../../etc/passwd",
            is_backup=True,
        )
    db.close_all()
