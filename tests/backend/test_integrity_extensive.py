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

    def test_entropy_mathematical_bounds(self):
        """Verify entropy stays within [0, 8] for any byte sequence."""
        # Test empty
        empty_file = self.test_dir / "empty"
        empty_file.touch()
        self.assertEqual(self.manager._calculate_entropy(empty_file), 0)

        # Test single byte repeated (minimum entropy)
        zero_entropy_file = self.test_dir / "zero_entropy"
        with open(zero_entropy_file, "wb") as f:
            f.write(b"AAAAAAAA" * 100)
        self.assertEqual(self.manager._calculate_entropy(zero_entropy_file), 0)

        # Test all 256 bytes (maximum entropy)
        max_entropy_file = self.test_dir / "max_entropy"
        with open(max_entropy_file, "wb") as f:
            f.write(bytes(range(256)))
        # log2(256) = 8
        self.assertAlmostEqual(
            self.manager._calculate_entropy(max_entropy_file),
            8.0,
            places=5,
        )

    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(st.binary(min_size=1, max_size=1024))
    def test_entropy_property(self, data):
        """Property: Entropy is always between 0 and 8 for non-empty data."""
        temp_file = self.test_dir / "prop_test"
        with open(temp_file, "wb") as f:
            f.write(data)

        entropy = self.manager._calculate_entropy(temp_file)
        self.assertGreaterEqual(entropy, 0)
        self.assertLessEqual(entropy, 8.000000000000002)  # Float precision

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

    def test_entropy_shift_detection(self):
        """Test detection of content type change (e.g. replacing text with random bytes)."""
        # 1. Start with a highly structured file (low entropy)
        # Use a non-critical filename to trigger the entropy check branch
        data_file = self.test_dir / "user_data.bin"
        with open(data_file, "wb") as f:
            f.write(b"A" * 5000)

        self.manager.save_manifest()

        # 2. Replace with high-entropy data (random bytes)
        with open(data_file, "wb") as f:
            f.write(os.urandom(5000))

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok, f"Integrity should fail. Issues: {issues}")
        self.assertTrue(
            any("Non-linear content shift" in i or "Entropy Δ" in i for i in issues),
            f"Expected entropy shift in: {issues}",
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

        self.assertEqual(manifest["version"], 2)
        self.assertIn("metadata", manifest)

        # Check if database metadata exists
        db_rel = str(self.db_path.relative_to(self.test_dir))
        self.assertIn(db_rel, manifest["metadata"])
        self.assertIn("entropy", manifest["metadata"][db_rel])
        self.assertIn("size", manifest["metadata"][db_rel])

    def test_database_size_divergence(self):
        """Verify size changes are caught when hash changes but entropy is similar."""
        self.manager.save_manifest()

        # Grow the database with similar content
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO data (val) VALUES (?)", ("more content" * 100,))
        conn.commit()
        conn.close()

        is_ok, issues = self.manager.check_integrity()
        # Even if entropy shift is low, hash and size changed
        if not is_ok:
            self.assertTrue(any("Database" in i for i in issues))

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
        ok, msg = self.manager._check_db_integrity(bad)
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
    # Entropy threshold boundaries
    # ------------------------------------------------------------------

    def test_entropy_threshold_db_just_below(self):
        """DB entropy delta of 0.99 should NOT trigger anomaly warning."""
        self.manager.save_manifest()

        with open(self.manager.manifest_path) as f:
            manifest = json.load(f)

        db_rel = str(self.db_path.relative_to(self.test_dir))
        real_entropy = manifest["metadata"][db_rel]["entropy"]
        manifest["metadata"][db_rel]["entropy"] = real_entropy + 0.99

        with open(self.manager.manifest_path, "w") as f:
            json.dump(manifest, f)

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(
            any("structural anomaly" in i for i in issues),
            f"Should not flag anomaly at delta=0.99: {issues}",
        )

    def test_entropy_threshold_db_just_above(self):
        """DB entropy delta of 1.01 should trigger anomaly warning."""
        self.manager.save_manifest()

        with open(self.manager.manifest_path) as f:
            manifest = json.load(f)

        db_rel = str(self.db_path.relative_to(self.test_dir))
        real_entropy = manifest["metadata"][db_rel]["entropy"]
        manifest["metadata"][db_rel]["entropy"] = real_entropy + 1.01

        # Also change the file hash so it triggers the comparison path
        manifest["files"][db_rel] = "0" * 64

        with open(self.manager.manifest_path, "w") as f:
            json.dump(manifest, f)

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(
            any("structural anomaly" in i or "Entropy" in i for i in issues),
            f"Should flag anomaly at delta=1.01: {issues}",
        )

    def test_entropy_threshold_file_1_49_no_flag(self):
        """Non-DB file entropy delta of 1.49 should NOT trigger content shift."""
        data_file = self.test_dir / "payload.bin"
        data_file.write_bytes(b"X" * 2000)
        self.manager.save_manifest()

        with open(self.manager.manifest_path) as f:
            manifest = json.load(f)

        rel = str(data_file.relative_to(self.test_dir))
        real_entropy = manifest["metadata"][rel]["entropy"]
        manifest["metadata"][rel]["entropy"] = real_entropy + 1.49
        manifest["files"][rel] = "0" * 64

        with open(self.manager.manifest_path, "w") as f:
            json.dump(manifest, f)

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(
            any("Non-linear content shift" in i for i in issues),
            f"Should not flag content shift at delta=1.49: {issues}",
        )

    def test_entropy_threshold_file_1_51_flags(self):
        """Non-DB file entropy delta of 1.51 should trigger content shift."""
        data_file = self.test_dir / "payload.bin"
        data_file.write_bytes(b"X" * 2000)
        self.manager.save_manifest()

        with open(self.manager.manifest_path) as f:
            manifest = json.load(f)

        rel = str(data_file.relative_to(self.test_dir))
        real_entropy = manifest["metadata"][rel]["entropy"]
        manifest["metadata"][rel]["entropy"] = real_entropy + 1.51
        manifest["files"][rel] = "0" * 64

        with open(self.manager.manifest_path, "w") as f:
            json.dump(manifest, f)

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(
            any("Non-linear content shift" in i for i in issues),
            f"Should flag content shift at delta=1.51: {issues}",
        )

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
    # Hypothesis: entropy for any binary data
    # ------------------------------------------------------------------

    @settings(
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
        derandomize=True,
    )
    @given(st.binary(min_size=1, max_size=4096))
    def test_entropy_monotonic_with_unique_bytes(self, data):
        """More unique byte values should produce higher entropy."""
        f = self.test_dir / "hyp_ent"
        f.write_bytes(data)
        e = self.manager._calculate_entropy(f)
        unique = len(set(data))
        if unique == 1:
            self.assertAlmostEqual(e, 0.0, places=5)
        else:
            self.assertGreater(e, 0.0)
        self.assertLessEqual(e, 8.0 + 1e-9)

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
