# SPDX-License-Identifier: 0BSD

"""Tests for automatic database recovery backup selection."""

from __future__ import annotations

import os

from meshchatx.src.backend.database import PRE_MIGRATE_BACKUP_PREFIX, Database
from meshchatx.src.backend.database.auto_recover import (
    infer_version_hint_from_backup_name,
    pick_compatible_backup,
    probe_backup_zip,
    run_auto_database_recover,
    schema_version_restorable,
)
from meshchatx.src.backend.database.schema import DatabaseSchema


def test_schema_version_restorable_bounds():
    latest = DatabaseSchema.LATEST_VERSION
    assert schema_version_restorable(latest, latest)
    assert schema_version_restorable(0, latest)
    assert not schema_version_restorable(latest + 1, latest)
    assert not schema_version_restorable(None, latest)


def test_infer_version_hint_from_pre_migrate_name():
    name = f"{PRE_MIGRATE_BACKUP_PREFIX}v52-to-v53-20260101-120000.zip"
    assert infer_version_hint_from_backup_name(name) == 52
    assert infer_version_hint_from_backup_name("backup-2026.zip") is None


def test_pick_compatible_backup_skips_unprobed_pre_migrate_name(tmp_path):
    temp_dir = str(tmp_path)
    backup_dir = os.path.join(temp_dir, "database-backups")
    os.makedirs(backup_dir)
    bogus = os.path.join(
        backup_dir,
        f"{PRE_MIGRATE_BACKUP_PREFIX}v52-to-v53-20260101-120000.zip",
    )
    with open(bogus, "wb") as handle:
        handle.write(b"not-a-zip")

    picked = pick_compatible_backup(temp_dir, DatabaseSchema.LATEST_VERSION)
    assert picked is None


def test_pick_compatible_backup_skips_too_new_and_suspicious(tmp_path):
    temp_dir = str(tmp_path)
    db_path = os.path.join(temp_dir, "database.db")
    db = Database(db_path)
    db.initialize()
    db.provider.execute(
        "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("marker", "pick-test"),
    )
    db.close_all()

    backup_dir = os.path.join(temp_dir, "database-backups")
    os.makedirs(backup_dir)
    good = db.backup_database(temp_dir)
    assert good["path"]

    too_new_path = os.path.join(backup_dir, "backup-too-new.zip")
    db2 = Database(db_path)
    db2.initialize()
    db2.provider.execute(
        "UPDATE config SET value = ? WHERE key = ?",
        (str(DatabaseSchema.LATEST_VERSION + 1), "database_version"),
    )
    db2.close_all()
    too_new = Database(db_path)
    too_new.backup_database(temp_dir, backup_path=too_new_path)
    too_new.close_all()

    suspicious_path = os.path.join(backup_dir, "backup-SUSPICIOUS-test.zip")
    with open(suspicious_path, "wb") as handle:
        handle.write(b"not-a-real-zip")

    picked = pick_compatible_backup(temp_dir, DatabaseSchema.LATEST_VERSION)
    assert picked is not None
    assert picked["name"] == os.path.basename(good["path"])
    assert picked["database_version"] == DatabaseSchema.LATEST_VERSION

    probe = probe_backup_zip(good["path"])
    assert probe["quick_check"] == "ok"
    assert probe["version"] == DatabaseSchema.LATEST_VERSION


def test_pick_compatible_backup_prefers_healthy_over_suspicious(tmp_path):
    temp_dir = str(tmp_path)
    db_path = os.path.join(temp_dir, "database.db")
    db = Database(db_path)
    db.initialize()
    good = db.backup_database(temp_dir)
    db.close_all()

    backup_dir = os.path.join(temp_dir, "database-backups")
    suspicious_path = os.path.join(backup_dir, "backup-SUSPICIOUS-only.zip")
    with open(suspicious_path, "wb") as handle:
        handle.write(b"PK\x03\x04")
    # corrupt zip still listed but should not win over good backup

    picked = pick_compatible_backup(temp_dir, DatabaseSchema.LATEST_VERSION)
    assert picked is not None
    assert picked["name"] == os.path.basename(good["path"])


def test_run_auto_database_recover_restores_when_backup_exists(tmp_path):
    temp_dir = str(tmp_path)
    db_path = os.path.join(temp_dir, "database.db")
    db = Database(db_path)
    db.initialize()
    backup_info = db.backup_database(temp_dir)
    db.close_all()

    restored_paths: list[str] = []

    def restore_fn(path: str) -> dict:
        restored_paths.append(path)
        return {"path": path, "restored": True}

    result = run_auto_database_recover(
        temp_dir,
        db_path,
        DatabaseSchema.LATEST_VERSION,
        restore_fn,
        sqlite_recover_fn=lambda: {"actions": []},
    )
    assert result["strategy"] == "restore_backup"
    assert restored_paths == [backup_info["path"]]
    assert result["requires_relaunch"] is True


def test_run_auto_database_recover_falls_back_to_sqlite(tmp_path):
    temp_dir = str(tmp_path)
    db_path = os.path.join(temp_dir, "database.db")
    db = Database(db_path)
    db.initialize()
    db.close_all()

    sqlite_called = False

    def restore_fn(_path: str) -> dict:
        raise AssertionError("restore should not run without backups")

    def sqlite_fn() -> dict:
        nonlocal sqlite_called
        sqlite_called = True
        return {"actions": [{"step": "wal_checkpoint"}]}

    result = run_auto_database_recover(
        temp_dir,
        db_path,
        DatabaseSchema.LATEST_VERSION,
        restore_fn,
        sqlite_recover_fn=sqlite_fn,
    )
    assert sqlite_called
    assert result["strategy"] == "sqlite_recovery"
    assert result["requires_relaunch"] is False


def test_run_auto_database_recover_none_without_backups_or_db(tmp_path):
    temp_dir = str(tmp_path)
    result = run_auto_database_recover(
        temp_dir,
        None,
        DatabaseSchema.LATEST_VERSION,
        lambda _p: {},
        sqlite_recover_fn=None,
    )
    assert result["strategy"] == "none"
