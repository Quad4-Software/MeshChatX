# SPDX-License-Identifier: 0BSD

import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.integrity_manager import IntegrityManager


class TestIntegrityManagerExtensive(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "database.db"
        self.storage_dir = self.test_dir / "storage"
        self.storage_dir.mkdir()

        # Create a valid SQLite database
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE data (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO data (val) VALUES ('initial')")
        conn.commit()
        conn.close()

        self.manager = IntegrityManager(self.test_dir, self.db_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_db_structural_tamper_detection(self):
        """Simulate actual SQLite corruption that bypasses hash-only checks."""
        self.manager.save_manifest()

        # Corrupt the database file header or internal structure
        # Overwriting the first few bytes (SQLite header) is a guaranteed fail
        with open(self.db_path, "r+b") as f:
            f.seek(0)
            f.write(b"NOTASQLITEFILE")

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok, f"Integrity should fail. Issues: {issues}")
        self.assertTrue(
            any(
                "Database structural issue" in i or "Database structural anomaly" in i
                for i in issues
            ),
            f"Expected structural issue in: {issues}",
        )

    def test_content_replacement_detection(self):
        """Replacing a monitored file's content must flag a signature mismatch."""
        data_file = self.test_dir / "user_data.bin"
        with open(data_file, "wb") as f:
            f.write(b"A" * 5000)

        self.manager.save_manifest()

        with open(data_file, "wb") as f:
            f.write(os.urandom(5000))

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok, f"Integrity should fail. Issues: {issues}")
        self.assertTrue(
            any("File signature mismatch" in i for i in issues),
            f"Expected signature mismatch in: {issues}",
        )

    def test_ignore_patterns_extensive(self):
        """Verify all volatile LXMF/RNS patterns are correctly filtered."""
        volatile_files = [
            "lxmf_router/lxmf/outbound_stamp_costs",
            "lxmf_router/storage/some_volatile_file",
            "lxmf_router/announces/ann_data",
            "lxmf_router/tmp/uploading",
            "database.db-wal",
            "database.db-shm",
            "something.tmp",
            ".DS_Store",
        ]

        for v in volatile_files:
            rel_path = Path(v)
            full_path = self.test_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.touch()
            self.assertTrue(
                self.manager._should_ignore(str(rel_path)),
                f"Failed to ignore {v}",
            )

    def test_ratchets_and_router_state_ignored(self):
        """RNS ratchets and LXMF router runtime state must not trigger warnings."""
        volatile_files = [
            "lxmf_router/lxmf/ratchets/adc0193d0a5b3726682486a1f0204b30.ratchets",
            "lxmf_router/lxmf/node_stats",
            "lxmf_router/lxmf/available_tickets",
            "lxmf_router/lxmf/local_deliveries",
            "lxmf_router/lxmf/locally_processed",
            "lxmf_router/lxmf/messagestore/abc123_1776215096.805143_19",
            "ratchets/deadbeef.ratchets",
            "node_stats",
        ]
        for v in volatile_files:
            self.assertTrue(
                self.manager._should_ignore(v),
                f"Failed to ignore volatile state: {v}",
            )

    def test_router_churn_does_not_break_integrity(self):
        """A clean manifest stays valid even as the router tree changes."""
        router_dir = self.storage_dir / "lxmf_router" / "lxmf"
        (router_dir / "ratchets").mkdir(parents=True)
        (router_dir / "messagestore").mkdir(parents=True)
        (router_dir / "ratchets" / "aa.ratchets").write_bytes(b"\x00" * 32)
        (router_dir / "node_stats").write_bytes(b"\x01" * 16)

        self.manager.save_manifest()

        (router_dir / "ratchets" / "aa.ratchets").write_bytes(b"\x02" * 64)
        (router_dir / "ratchets" / "bb.ratchets").write_bytes(b"\x03" * 64)
        (router_dir / "messagestore" / "msg_1.bin").write_bytes(b"\x04" * 100)
        (router_dir / "node_stats").write_bytes(b"\x05" * 32)

        is_ok, issues = self.manager.check_integrity()
        self.assertTrue(is_ok, f"Router churn should not flag integrity: {issues}")

    def test_critical_files_still_monitored(self):
        """Identity and config outside the router tree remain protected."""
        self.assertFalse(self.manager._should_ignore("identity"))
        self.assertFalse(self.manager._should_ignore("config"))
        self.assertFalse(
            self.manager._should_ignore("identities/abc/identity"),
        )

    def test_critical_file_protection(self):
        """Ensure identity and config changes are always treated as critical."""
        id_file = self.test_dir / "identity"
        id_file.write_text("secure_key")

        self.manager.save_manifest()

        # Minor modification (stays low entropy)
        id_file.write_text("secure_kez")

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(any("Critical security component" in i for i in issues))

    def test_missing_file_detection(self):
        """Verify missing files are detected even if not critical."""
        misc_file = self.test_dir / "misc.txt"
        misc_file.write_text("data")

        self.manager.save_manifest()
        misc_file.unlink()

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(any("File missing: misc.txt" in i for i in issues))

    def test_manifest_versioning(self):
        """Verify the manifest includes the new version and metadata fields."""
        self.manager.save_manifest()

        with open(self.manager.manifest_path) as f:
            manifest = json.load(f)

        self.assertEqual(manifest["version"], 3)
        self.assertIn("metadata", manifest)
        self.assertIn("clean_exit", manifest)
        self.assertIn("pending_issues", manifest)

        # Check if database metadata exists
        db_rel = str(self.db_path.relative_to(self.test_dir))
        self.assertIn(db_rel, manifest["metadata"])
        self.assertIn("size", manifest["metadata"][db_rel])
        self.assertIn("mtime_ns", manifest["metadata"][db_rel])

    def test_database_size_divergence(self):
        """Verify content changes to the database are flagged."""
        self.manager.save_manifest()

        # Grow the database
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO data (val) VALUES (?)", ("more content" * 100,))
        conn.commit()
        conn.close()

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(any("database.db" in i for i in issues))

    # ------------------------------------------------------------------
    # Corrupt / malformed manifest
    # ------------------------------------------------------------------

    def test_corrupt_manifest_json(self):
        """check_integrity must not crash on invalid JSON in the manifest."""
        self.manager.save_manifest()
        with open(self.manager.manifest_path, "w") as f:
            f.write("{{{NOT JSON!!!")

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(any("Integrity check failed" in i for i in issues))

    def test_empty_manifest_file(self):
        """check_integrity must handle a 0-byte manifest gracefully."""
        self.manager.save_manifest()
        with open(self.manager.manifest_path, "w") as f:
            f.truncate(0)

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(any("Integrity check failed" in i for i in issues))

    def test_manifest_missing_keys(self):
        """Manifest with valid JSON but missing expected keys should not crash."""
        with open(self.manager.manifest_path, "w") as f:
            json.dump({"version": 2}, f)

        is_ok, issues = self.manager.check_integrity()
        self.assertTrue(is_ok or isinstance(issues, list))

    # ------------------------------------------------------------------
    # Hash consistency
    # ------------------------------------------------------------------

    def test_hash_file_consistency(self):
        """Same file content must always produce the same hash."""
        h1 = self.manager._hash_file(self.db_path)
        h2 = self.manager._hash_file(self.db_path)
        self.assertEqual(h1, h2)
        self.assertIsNotNone(h1)
        self.assertEqual(len(h1), 64)  # SHA-256 hex length

    def test_hash_file_missing(self):
        """_hash_file on a missing path must return None."""
        result = self.manager._hash_file(self.test_dir / "does_not_exist.bin")
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # DB integrity check
    # ------------------------------------------------------------------

    def test_check_db_integrity_valid(self):
        """_check_db_integrity on a valid DB returns (True, 'ok')."""
        ok, msg = self.manager._check_db_integrity(self.db_path)
        self.assertTrue(ok)
        self.assertEqual(msg, "ok")

    def test_check_db_integrity_not_sqlite(self):
        """_check_db_integrity on a non-SQLite file returns (False, ...)."""
        bad = self.test_dir / "bad.db"
        bad.write_text("this is not sqlite")
        ok, _msg = self.manager._check_db_integrity(bad)
        self.assertFalse(ok)

    def test_check_db_integrity_missing(self):
        """_check_db_integrity on missing file returns (False, ...)."""
        ok, msg = self.manager._check_db_integrity(self.test_dir / "gone.db")
        self.assertFalse(ok)
        self.assertIn("does not exist", msg)

    def test_check_db_integrity_empty_file(self):
        """_check_db_integrity on a 0-byte file should not crash."""
        empty_db = self.test_dir / "empty.db"
        empty_db.touch()
        ok, msg = self.manager._check_db_integrity(empty_db)
        # SQLite treats a 0-byte file as a valid empty database
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(msg, str)

    # ------------------------------------------------------------------
    # Clean-exit tracking / lenient mode
    # ------------------------------------------------------------------

    def test_unclean_shutdown_demotes_noncritical_drift(self):
        """Demote drift in non-critical files after an unclean shutdown."""
        notes = self.test_dir / "notes.bin"
        notes.write_bytes(b"before crash")
        self.manager.save_manifest(reason="initial")

        notes.write_bytes(b"changed during crashed run")

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(
            any("Expected change" in i and "notes.bin" in i for i in issues),
            f"Expected demoted drift in: {issues}",
        )
        self.assertFalse(
            any("File signature mismatch" in i for i in issues),
            f"Strict mismatch should not fire after unclean shutdown: {issues}",
        )

    def test_clean_shutdown_keeps_strict_drift(self):
        """A clean shutdown baseline flags the same drift as a mismatch."""
        notes = self.test_dir / "notes.bin"
        notes.write_bytes(b"before shutdown")
        self.manager.save_manifest(reason="shutdown")

        notes.write_bytes(b"changed while app was off")

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(any("File signature mismatch" in i for i in issues))

    def test_unclean_shutdown_still_flags_critical(self):
        """Critical files stay strict even after an unclean shutdown."""
        (self.test_dir / "identity").write_bytes(b"key-bytes")
        self.manager.save_manifest(reason="initial")

        (self.test_dir / "identity").write_bytes(b"tampered-key")

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(
            any("Critical security component" in i for i in issues),
            f"Identity drift must stay critical after crash: {issues}",
        )

    def test_app_version_change_is_lenient(self):
        """A baseline saved by an older app version tolerates drift."""
        self.manager.save_manifest(reason="shutdown")

        with open(self.manager.manifest_path) as f:
            manifest = json.load(f)
        manifest["app_version"] = "0.0.0-old"
        with open(self.manager.manifest_path, "w") as f:
            json.dump(manifest, f)

        manager = IntegrityManager(self.test_dir, self.db_path, app_version="9.9.9")
        notes = self.test_dir / "notes.bin"
        notes.write_bytes(b"installer touched this")

        is_ok, issues = manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(
            any("Expected change" in i and "notes.bin" in i for i in issues),
            f"Expected demoted drift after upgrade: {issues}",
        )

    # ------------------------------------------------------------------
    # Pending issues persist until acknowledged
    # ------------------------------------------------------------------

    def test_pending_issues_resurface_next_run(self):
        """Unacknowledged findings carry into the next manifest and resurface."""
        notes = self.test_dir / "notes.bin"
        notes.write_bytes(b"original")
        self.manager.save_manifest()

        notes.write_bytes(b"tampered while off")
        is_ok, _issues = self.manager.check_integrity()
        self.assertFalse(is_ok)

        # Simulate the app shutting down with the warning unacknowledged
        notes.write_bytes(b"tampered while off")  # state still differs
        self.manager.save_manifest(reason="shutdown")

        fresh = IntegrityManager(self.test_dir, self.db_path)
        is_ok, issues = fresh.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(
            any("Previously reported" in i for i in issues),
            f"Pending issues should resurface: {issues}",
        )

    def test_acknowledge_clears_pending_issues(self):
        """save_manifest(reason='acknowledge') drops carried findings."""
        notes = self.test_dir / "notes.bin"
        notes.write_bytes(b"original")
        self.manager.save_manifest()

        notes.write_bytes(b"tampered while off")
        is_ok, _issues = self.manager.check_integrity()
        self.assertFalse(is_ok)

        self.manager.save_manifest(reason="acknowledge")

        with open(self.manager.manifest_path) as f:
            manifest = json.load(f)
        self.assertEqual(manifest["pending_issues"], [])

        is_ok, issues = self.manager.check_integrity()
        self.assertTrue(is_ok, f"Baseline should be clean after ack: {issues}")

    # ------------------------------------------------------------------
    # Manifest authenticity (trust_dir)
    # ------------------------------------------------------------------

    def _trusted_manager(self):
        trust_dir = self.test_dir / "trust"
        storage = self.test_dir / "identities" / "id1"
        storage.mkdir(parents=True)
        db = storage / "database.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.close()
        (storage / "identity").write_bytes(b"key")
        return (
            IntegrityManager(
                storage,
                db,
                identity_hash="id1",
                trust_dir=trust_dir,
            ),
            storage,
            db,
        )

    def test_signed_manifest_detects_tamper(self):
        """Hand-editing a signed manifest must be flagged."""
        manager, _storage, _db = self._trusted_manager()
        manager.save_manifest()

        with open(manager.manifest_path) as f:
            manifest = json.load(f)
        self.assertIn("hmac", manifest)
        manifest["files"] = {}
        with open(manager.manifest_path, "w") as f:
            json.dump(manifest, f)

        is_ok, issues = manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(
            any("manifest tampered" in i.lower() for i in issues),
            f"Expected manifest tamper detection: {issues}",
        )

    def test_deleted_manifest_detected_via_registry(self):
        """Deleting the manifest must not downgrade the check to a pass."""
        manager, _storage, _db = self._trusted_manager()
        manager.save_manifest()

        manager.manifest_path.unlink()

        is_ok, issues = manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(
            any("manifest removed" in i.lower() for i in issues),
            f"Expected manifest-removal detection: {issues}",
        )

    def test_cross_identity_manifest_swap_detected(self):
        """A manifest copied from another identity fails signature binding."""
        manager1, _storage1, _db1 = self._trusted_manager()
        manager1.save_manifest()

        storage2 = self.test_dir / "identities" / "id2"
        storage2.mkdir(parents=True)
        db2 = storage2 / "database.db"
        conn = sqlite3.connect(db2)
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.close()
        (storage2 / "identity").write_bytes(b"other-key")

        # Attacker copies the valid manifest from identity 1 to identity 2
        shutil.copy(manager1.manifest_path, storage2 / manager1.MANIFEST_NAME)

        manager2 = IntegrityManager(
            storage2,
            db2,
            identity_hash="id2",
            trust_dir=manager1.trust_dir,
        )
        is_ok, issues = manager2.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(any("Identity mismatch" in i for i in issues))

    def test_unsigned_legacy_manifest_accepted(self):
        """Manifests written before signing existed still work once."""
        manager, _storage, _db = self._trusted_manager()
        # Write a v2-style manifest without hmac
        scanned = manager._scan_storage()
        manifest = {
            "version": 2,
            "identity": "id1",
            "files": {rel: e["sha256"] for rel, e in scanned.items()},
            "metadata": {},
        }
        manager.manifest_path.write_text(json.dumps(manifest))

        is_ok, issues = manager.check_integrity()
        self.assertTrue(is_ok, f"Legacy manifest should pass: {issues}")

    # ------------------------------------------------------------------
    # Stat pre-filter
    # ------------------------------------------------------------------

    def test_mtime_only_touch_does_not_flag(self):
        """Changing mtime without changing content must not alert."""
        notes = self.test_dir / "notes.bin"
        notes.write_bytes(b"stable content")
        self.manager.save_manifest()

        os.utime(notes, (1_700_000_000, 1_700_000_000))

        is_ok, issues = self.manager.check_integrity()
        self.assertTrue(is_ok, f"mtime-only change should pass: {issues}")

    def test_live_mode_skips_database_hash(self):
        """During a run the open database is expected to differ."""
        self.manager.save_manifest()

        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO data (val) VALUES ('live write')")
        conn.commit()
        conn.close()

        is_ok, issues = self.manager.check_integrity(live=True)
        self.assertTrue(is_ok, f"Live check must not flag db writes: {issues}")

    # ------------------------------------------------------------------
    # DB outside storage_dir
    # ------------------------------------------------------------------

    def test_db_outside_storage_dir(self):
        """check_integrity must not crash when DB is outside storage_dir."""
        import tempfile as tf

        ext_dir = Path(tf.mkdtemp())
        try:
            ext_db = ext_dir / "external.db"
            conn = sqlite3.connect(ext_db)
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
            conn.close()

            mgr = IntegrityManager(self.test_dir, ext_db)
            mgr.save_manifest()
            is_ok, issues = mgr.check_integrity()
            self.assertTrue(is_ok or isinstance(issues, list))
        finally:
            shutil.rmtree(ext_dir)

    # ------------------------------------------------------------------
    # Hypothesis: save_manifest then check_integrity always consistent
    # ------------------------------------------------------------------

    @settings(
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
        max_examples=10,
        derandomize=True,
    )
    @given(st.binary(min_size=1, max_size=512))
    def test_save_then_check_always_passes(self, extra_data):
        """After save_manifest(), check_integrity() must pass for unchanged state."""
        extra_file = self.test_dir / "extra.bin"
        extra_file.write_bytes(extra_data)
        self.manager.save_manifest()
        is_ok, issues = self.manager.check_integrity()
        self.assertTrue(is_ok, f"Should pass after save. Issues: {issues}")


if __name__ == "__main__":
    unittest.main()
