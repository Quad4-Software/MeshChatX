# SPDX-License-Identifier: 0BSD

"""Adversarial repro tests for backup/restore bugs found in the audit.

Each test pins an invariant:
- a legit restore must not leave the next integrity check blocked
- a restore interrupted at the worst moment must not lose the database
- staging/aside leftovers must not leak into backups or integrity scans
- two backups in one second must not overwrite each other
"""

import json
import os
import shutil
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import pytest

from meshchatx.src.backend.database import Database, DatabaseRestoreError
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.integrity_manager import IntegrityManager


@pytest.fixture(autouse=True)
def reset_database_provider():
    DatabaseProvider._instance = None
    yield
    if DatabaseProvider._instance is not None:
        DatabaseProvider._instance.close_all()
    DatabaseProvider._instance = None


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


def _make_identity_db(identity_dir, marker=None):
    os.makedirs(identity_dir, exist_ok=True)
    db_path = os.path.join(identity_dir, "database.db")
    db = Database(db_path)
    db.initialize()
    if marker:
        db.execute_sql(
            "INSERT INTO config (key, value) VALUES (?, ?)",
            ("marker", marker),
        )
    return db


class TestRestoreStaleIntegrityManifest:
    """H1: restored integrity-manifest.json must not dominate the next boot."""

    def test_backup_does_not_contain_integrity_manifest(self, temp_dir):
        """Backups must not ship the signed integrity manifest."""
        identity_dir = os.path.join(temp_dir, "identities", "abc")
        db = _make_identity_db(identity_dir)
        manager = IntegrityManager(
            identity_dir,
            os.path.join(identity_dir, "database.db"),
            identity_hash="abc",
        )
        manager.save_manifest()
        assert os.path.isfile(manager.manifest_path)

        result = db.backup_database(identity_dir)
        db.close_all()

        with zipfile.ZipFile(result["path"]) as zf:
            names = set(zf.namelist())
        assert "integrity-manifest.json" not in names, names

    def test_restore_drops_staged_integrity_manifest(self, temp_dir):
        """A smuggled integrity-manifest.json member must not be restored."""
        identity_dir = os.path.join(temp_dir, "identities", "abc")
        db = _make_identity_db(identity_dir)

        evil_zip = os.path.join(temp_dir, "evil.zip")
        with zipfile.ZipFile(evil_zip, "w") as zf:
            # copy the real db into the zip
            db_path = os.path.join(identity_dir, "database.db")
            db._checkpoint_wal()
            with open(db_path, "rb") as handle:
                zf.writestr("database.db", handle.read())
            zf.writestr(
                "integrity-manifest.json",
                json.dumps({"version": 3, "files": {}, "identity": "forged"}),
            )
        db.restore_database(evil_zip)
        db.close_all()
        assert not os.path.isfile(os.path.join(identity_dir, "integrity-manifest.json"))

    def test_restore_then_integrity_check_is_clean(self, temp_dir):
        """Oracle: backup -> mutate -> restore -> integrity check must pass.

        A stale manifest carried inside the zip would flag the restored
        database hash and resurface dead pending issues.
        """
        identity_dir = os.path.join(temp_dir, "identities", "abc")
        db = _make_identity_db(identity_dir, marker="original")
        manager = IntegrityManager(
            identity_dir,
            os.path.join(identity_dir, "database.db"),
            identity_hash="abc",
        )
        manager.save_manifest()
        backup = db.backup_database(identity_dir)

        db.execute_sql(
            "UPDATE config SET value = ? WHERE key = ?",
            ("changed", "marker"),
        )
        db.close_all()
        DatabaseProvider._instance = None

        restored = Database(os.path.join(identity_dir, "database.db"))
        restored.restore_database(backup["path"])
        restored.close_all()
        DatabaseProvider._instance = None

        fresh = IntegrityManager(
            identity_dir,
            os.path.join(identity_dir, "database.db"),
            identity_hash="abc",
        )
        is_ok, issues = fresh.check_integrity()
        assert is_ok, f"clean restore flagged: {issues}"


class TestInterruptedRestoreRecovery:
    """H2: a kill between aside-move and staged-move must not lose the db."""

    def test_missing_main_db_repaired_from_aside(self, temp_dir):
        """Repair a live database.db lost to an interrupted restore."""
        identity_dir = os.path.join(temp_dir, "identities", "abc")
        db = _make_identity_db(identity_dir, marker="precious")
        db.close_all()
        DatabaseProvider._instance = None

        db_path = os.path.join(identity_dir, "database.db")
        aside_dir = os.path.join(identity_dir, ".meshchatx-aside-deadbeef")
        os.makedirs(aside_dir)
        shutil.move(db_path, os.path.join(aside_dir, "database.db"))

        db2 = Database(db_path)
        db2.initialize()
        row = db2.provider.fetchone(
            "SELECT value FROM config WHERE key = ?",
            ("marker",),
        )
        db2.close_all()
        assert row is not None, "interrupted restore destroyed the database"
        assert row["value"] == "precious"

    def test_aside_repair_keeps_live_db_when_both_exist(self, temp_dir):
        """A live database must win over an orphaned aside copy."""
        identity_dir = os.path.join(temp_dir, "identities", "abc")
        db = _make_identity_db(identity_dir, marker="live")
        db.close_all()
        DatabaseProvider._instance = None

        aside_dir = os.path.join(identity_dir, ".meshchatx-aside-cafe")
        os.makedirs(aside_dir)
        old_db = Database(os.path.join(aside_dir, "database.db"))
        old_db.initialize()
        old_db.execute_sql(
            "INSERT INTO config (key, value) VALUES (?, ?)",
            ("marker", "aside"),
        )
        old_db.close_all()
        DatabaseProvider._instance = None

        db2 = Database(os.path.join(identity_dir, "database.db"))
        db2.initialize()
        row = db2.provider.fetchone(
            "SELECT value FROM config WHERE key = ?",
            ("marker",),
        )
        db2.close_all()
        assert row["value"] == "live"


class TestStagingLeftovers:
    """H3/H7: temp dirs must not leak into backups, restores or scans."""

    def test_backup_excludes_staging_leftovers_and_sqlite_tmp(self, temp_dir):
        identity_dir = os.path.join(temp_dir, "identities", "abc")
        db = _make_identity_db(identity_dir)
        for junk in (
            ".meshchatx-restore-aa",
            ".meshchatx-aside-bb",
            ".meshchatx-extras-aside-cc",
            "sqlite-tmp",
        ):
            junk_dir = os.path.join(identity_dir, junk)
            os.makedirs(junk_dir)
            with open(os.path.join(junk_dir, "junk.bin"), "wb") as handle:
                handle.write(b"junk")

        result = db.backup_database(identity_dir)
        db.close_all()

        with zipfile.ZipFile(result["path"]) as zf:
            names = set(zf.namelist())
        leaked = [n for n in names if ".meshchatx-" in n or "sqlite-tmp" in n]
        assert not leaked, f"temp dirs leaked into backup: {leaked}"

    def test_restore_ignores_staged_temp_dirs(self, temp_dir):
        """Tainted backup members must not recreate temp dirs."""
        identity_dir = os.path.join(temp_dir, "identities", "abc")
        db = _make_identity_db(identity_dir)
        db_path = os.path.join(identity_dir, "database.db")
        db._checkpoint_wal()

        zip_path = os.path.join(temp_dir, "tainted.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            with open(db_path, "rb") as handle:
                zf.writestr("database.db", handle.read())
            zf.writestr(".meshchatx-aside-zz/old.bin", b"stale")

        db.restore_database(zip_path)
        db.close_all()
        assert not os.path.exists(os.path.join(identity_dir, ".meshchatx-aside-zz"))

    def test_staging_leftover_not_flagged_by_integrity(self, temp_dir):
        """Post-crash restore leftovers are app artifacts, not tamper."""
        identity_dir = os.path.join(temp_dir, "identities", "abc")
        db = _make_identity_db(identity_dir)
        db.close_all()
        DatabaseProvider._instance = None

        manager = IntegrityManager(
            identity_dir, os.path.join(identity_dir, "database.db")
        )
        manager.save_manifest()

        leftover = os.path.join(identity_dir, ".meshchatx-aside-11")
        os.makedirs(leftover)
        with open(os.path.join(leftover, "database.db"), "wb") as handle:
            handle.write(b"aside")

        is_ok, issues = manager.check_integrity()
        assert is_ok, f"restore leftover flagged: {issues}"


class TestBackupNameCollision:
    """H4: backups taken inside one second must both survive."""

    def test_same_second_backups_do_not_clobber(self, temp_dir):
        identity_dir = os.path.join(temp_dir, "identities", "abc")
        db = _make_identity_db(identity_dir)
        r1 = db.backup_database(identity_dir)
        r2 = db.backup_database(identity_dir)
        db.close_all()
        assert r1["path"] != r2["path"], "same-second backup overwrote the first"
        assert os.path.isfile(r1["path"])
        assert os.path.isfile(r2["path"])


class TestRestoreDiskGuard:
    """H5: restore must refuse a zip that cannot fit on the target disk."""

    def test_zip_bigger_than_free_space_rejected_before_moves(self, temp_dir):
        identity_dir = os.path.join(temp_dir, "identities", "abc")
        db = _make_identity_db(identity_dir, marker="alive")
        db_path = os.path.join(identity_dir, "database.db")
        db._checkpoint_wal()

        zip_path = os.path.join(temp_dir, "huge.zip")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
            with open(db_path, "rb") as handle:
                zf.writestr("database.db", handle.read())
            zf.writestr("payload.bin", b"x" * 1024)

        fake_usage = shutil._ntuple_diskusage(10**12, 10**12 - 1024, 1024)
        with patch("shutil.disk_usage", return_value=fake_usage):
            with pytest.raises(DatabaseRestoreError):
                db.restore_database(zip_path)

        # original database must still be live and readable
        row = db.provider.fetchone(
            "SELECT value FROM config WHERE key = ?",
            ("marker",),
        )
        db.close_all()
        assert row["value"] == "alive"
        assert os.path.isfile(db_path)


class TestCrossIdentityRestore:
    """A zip carrying a different identity must land in that identity's slot.

    Identity storage is keyed by hash: identities/<hash>/. Without relocation
    the restored tree sits under the old hash while the app boots the new key
    and finds an empty dir, so the restore looks like data loss.
    """

    def test_restore_of_foreign_identity_relocates_tree(self, temp_dir):
        import threading

        import RNS

        from meshchatx.meshchat import ReticulumMeshChat

        id_a = RNS.Identity(create_keys=True)
        id_b = RNS.Identity(create_keys=True)
        hash_a, hash_b = id_a.hash.hex(), id_b.hash.hex()

        dir_a = os.path.join(temp_dir, "identities", hash_a)
        _make_identity_db(dir_a, marker="A")
        db_path_a = os.path.join(dir_a, "database.db")

        src_b = os.path.join(temp_dir, "src_b")
        db_b = _make_identity_db(src_b, marker="B")
        id_b.to_file(os.path.join(src_b, "identity"))
        backup = db_b.backup_database(
            src_b,
            backup_path=os.path.join(temp_dir, "b.zip"),
        )
        db_b.close_all()
        DatabaseProvider._instance = None

        app = object.__new__(ReticulumMeshChat)
        app.contexts = {}
        app.current_context = None
        app.storage_dir = temp_dir
        app.identity = id_a
        app.identity_file_path = os.path.join(temp_dir, "identity")
        app._restore_lock = threading.Lock()
        app._teardown_all_contexts_for_reload = unittest.mock.Mock()

        with patch.object(
            ReticulumMeshChat,
            "prepare_for_database_restore",
            return_value=db_path_a,
        ):
            result = ReticulumMeshChat.restore_database(
                app,
                backup["path"],
                relaunch=False,
            )

        dir_b = os.path.join(temp_dir, "identities", hash_b)
        assert result["restored_from"] == backup["path"]
        assert os.path.isfile(os.path.join(dir_b, "database.db"))
        assert os.path.isfile(os.path.join(dir_b, "identity"))
        assert not os.path.exists(dir_a), "restored tree stranded under old hash"

        reopened = RNS.Identity.from_file(app.identity_file_path)
        assert reopened.hash == id_b.hash

        db2 = Database(os.path.join(dir_b, "database.db"))
        db2.initialize()
        row = db2.provider.fetchone(
            "SELECT value FROM config WHERE key = ?",
            ("marker",),
        )
        db2.close_all()
        assert row["value"] == "B"

    def test_restore_same_identity_stays_in_slot(self, temp_dir):
        import threading

        import RNS

        from meshchatx.meshchat import ReticulumMeshChat

        id_a = RNS.Identity(create_keys=True)
        hash_a = id_a.hash.hex()
        dir_a = os.path.join(temp_dir, "identities", hash_a)
        db = _make_identity_db(dir_a, marker="A")
        db_path_a = os.path.join(dir_a, "database.db")
        id_a.to_file(os.path.join(dir_a, "identity"))
        backup = db.backup_database(dir_a)
        db.execute_sql(
            "UPDATE config SET value = ? WHERE key = ?",
            ("changed", "marker"),
        )
        db.close_all()
        DatabaseProvider._instance = None

        app = object.__new__(ReticulumMeshChat)
        app.contexts = {}
        app.current_context = None
        app.storage_dir = temp_dir
        app.identity = id_a
        app.identity_file_path = os.path.join(temp_dir, "identity")
        app._restore_lock = threading.Lock()
        app._teardown_all_contexts_for_reload = unittest.mock.Mock()

        with patch.object(
            ReticulumMeshChat,
            "prepare_for_database_restore",
            return_value=db_path_a,
        ):
            ReticulumMeshChat.restore_database(app, backup["path"], relaunch=False)

        assert os.path.isfile(db_path_a)
        assert not os.path.exists(os.path.join(temp_dir, "identities", "prerestore"))
        db2 = Database(db_path_a)
        db2.initialize()
        row = db2.provider.fetchone(
            "SELECT value FROM config WHERE key = ?",
            ("marker",),
        )
        db2.close_all()
        assert row["value"] == "A"


class TestAsideRollbackBound:
    """Only the newest aside holding a db is kept as a rollback artifact."""

    def test_older_asides_with_db_are_pruned(self, temp_dir):
        identity_dir = os.path.join(temp_dir, "identities", "abc")
        db = _make_identity_db(identity_dir, marker="live")
        db.close_all()
        DatabaseProvider._instance = None

        asides = []
        for idx in range(3):
            aside = os.path.join(identity_dir, f".meshchatx-aside-{idx}")
            os.makedirs(aside)
            with open(os.path.join(aside, "database.db"), "wb") as handle:
                handle.write(b"old-db-%d" % idx)
            # spread mtimes so ordering is deterministic
            os.utime(aside, (1_000_000 + idx, 1_000_000 + idx))
            asides.append(aside)

        Database(os.path.join(identity_dir, "database.db"))

        assert os.path.exists(asides[2]), "newest rollback artifact removed"
        assert not os.path.exists(asides[0])
        assert not os.path.exists(asides[1])


if __name__ == "__main__":
    unittest.main()
