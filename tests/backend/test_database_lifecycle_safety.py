# SPDX-License-Identifier: 0BSD

import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import pytest

from meshchatx.src.backend.database import Database, DatabaseRestoreError
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseMigrationError, DatabaseSchema
from meshchatx.src.backend.integrity_manager import IntegrityManager
from meshchatx.src.backend.storage_lock import StorageLock, StorageLockError


@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_provider():
    DatabaseProvider._instance = None
    yield
    if DatabaseProvider._instance is not None:
        DatabaseProvider._instance.close_all()
    DatabaseProvider._instance = None


def test_provider_path_switch_does_not_deadlock(temp_dir):
    db_path_a = os.path.join(temp_dir, "a.db")
    db_path_b = os.path.join(temp_dir, "b.db")
    DatabaseProvider.get_instance(db_path_a)
    provider_b = DatabaseProvider.get_instance(db_path_b)
    assert provider_b.db_path == db_path_b
    DatabaseProvider._instance.close_all()


def test_provider_path_switch_calls_close_all(temp_dir):
    db_path_a = os.path.join(temp_dir, "a.db")
    db_path_b = os.path.join(temp_dir, "b.db")
    provider_a = DatabaseProvider.get_instance(db_path_a)
    with patch.object(provider_a, "close_all") as mock_close:
        DatabaseProvider.get_instance(db_path_b)
        mock_close.assert_called_once()
    DatabaseProvider._instance.close_all()


def test_restore_invokes_close_all_before_replace(temp_dir):
    db_path = os.path.join(temp_dir, "live.db")
    db = Database(db_path)
    db.initialize()
    db.execute_sql("INSERT INTO config (key, value) VALUES (?, ?)", ("k", "v1"))
    backup_path = os.path.join(temp_dir, "backup.zip")
    db.backup_database(temp_dir, backup_path=backup_path)
    with patch.object(
        db.provider, "close_all", wraps=db.provider.close_all
    ) as mock_close:
        db.restore_database(backup_path)
        assert mock_close.call_count >= 1
    row = db.provider.fetchone("SELECT value FROM config WHERE key = ?", ("k",))
    assert row["value"] == "v1"
    db.close_all()


def test_migration_failure_does_not_bump_version(temp_dir):
    db_path = os.path.join(temp_dir, "broken_migrate.db")
    provider = DatabaseProvider.get_instance(db_path)
    schema = DatabaseSchema(provider)
    provider.execute(
        """
        CREATE TABLE config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT
        )
        """,
    )
    provider.execute(
        "INSERT INTO config (key, value) VALUES (?, ?)",
        ("database_version", "47"),
    )

    def fail_run(_current_version):
        schema._migration_errors.append("simulated migration failure")

    schema._run_migrations = fail_run
    with pytest.raises(DatabaseMigrationError):
        schema.migrate(47)

    row = provider.fetchone(
        "SELECT value FROM config WHERE key = 'database_version'",
    )
    assert int(row["value"]) == 47
    provider.close_all()


def test_integrity_allows_hash_change_when_sqlite_ok(temp_dir):
    db_path = os.path.join(temp_dir, "database.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE data (id INTEGER PRIMARY KEY, val TEXT)")
    conn.execute("INSERT INTO data (val) VALUES ('x')")
    conn.commit()
    conn.close()

    manager = IntegrityManager(temp_dir, db_path)
    manager.save_manifest()

    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO data (val) VALUES ('y')")
    conn.commit()
    conn.close()

    is_ok, issues = manager.check_integrity()
    assert is_ok, issues


def test_integrity_flags_structural_damage(temp_dir):
    db_path = os.path.join(temp_dir, "database.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE data (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    manager = IntegrityManager(temp_dir, db_path)
    manager.save_manifest()

    with open(db_path, "r+b") as handle:
        handle.seek(0)
        handle.write(b"NOTASQLITEFILE")

    is_ok, issues = manager.check_integrity()
    assert not is_ok
    assert any("Database structural issue" in i for i in issues)


def test_storage_lock_rejects_second_instance(temp_dir):
    lock_a = StorageLock(temp_dir)
    lock_a.acquire()
    lock_b = StorageLock(temp_dir)
    with pytest.raises(StorageLockError):
        lock_b.acquire()
    lock_a.release()


def test_restore_rejects_non_sqlite_backup(temp_dir):
    db_path = os.path.join(temp_dir, "main.db")
    db = Database(db_path)
    db.initialize()

    bad_backup = os.path.join(temp_dir, "bad.db")
    with open(bad_backup, "wb") as handle:
        handle.write(b"not a sqlite database")

    with pytest.raises(DatabaseRestoreError, match="not a valid SQLite"):
        db.restore_database(bad_backup)
    db.close_all()


def test_looks_like_sqlite_header():
    path = tempfile.NamedTemporaryFile(delete=False).name
    try:
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.close()
        assert Database._looks_like_sqlite(path)
        with open(path, "r+b") as handle:
            handle.seek(0)
            handle.write(b"garbage")
        assert not Database._looks_like_sqlite(path)
    finally:
        os.remove(path)


class TestRestoreDatabaseMethod(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")

    def tearDown(self):
        if DatabaseProvider._instance is not None:
            DatabaseProvider._instance.close_all()
        DatabaseProvider._instance = None
        shutil.rmtree(self.test_dir)

    def test_checkpoint_and_close_uses_close_all(self):
        db = Database(self.db_path)
        db.initialize()
        with patch.object(db.provider, "close_all") as mock_close:
            db._checkpoint_and_close()
            mock_close.assert_called_once()


class TestMeshchatRestoreFlow(unittest.TestCase):
    @patch("meshchatx.meshchat.ReticulumMeshChat._schedule_process_restart")
    def test_restore_database_prepares_and_schedules_restart(self, mock_restart):
        from meshchatx.meshchat import ReticulumMeshChat

        temp = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp, "identities", "abc", "database.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            app = object.__new__(ReticulumMeshChat)
            app.contexts = {}
            app.current_context = None
            app.storage_dir = temp
            app.identity_file_path = None
            app._teardown_all_contexts_for_reload = unittest.mock.Mock()

            db = Database(db_path)
            db.initialize()
            backup_path = os.path.join(temp, "b.zip")
            db.backup_database(temp, backup_path=backup_path)
            db.close_all()

            with patch.object(
                ReticulumMeshChat,
                "prepare_for_database_restore",
                return_value=db_path,
            ):
                result = ReticulumMeshChat.restore_database(
                    app,
                    backup_path,
                    relaunch=True,
                )
            assert result["restored_from"] == backup_path
            mock_restart.assert_called_once()
        finally:
            shutil.rmtree(temp)
