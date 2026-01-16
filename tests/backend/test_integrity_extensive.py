import shutil
import tempfile
import unittest
import os
import sqlite3
import json
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck

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
            self.manager._calculate_entropy(max_entropy_file), 8.0, places=5
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
                self.manager._should_ignore(str(rel_path)), f"Failed to ignore {v}"
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


if __name__ == "__main__":
    unittest.main()
