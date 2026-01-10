import shutil
import tempfile
import unittest
from pathlib import Path

from meshchatx.src.backend.integrity_manager import IntegrityManager


class TestIntegrityManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "database.db"
        self.identities_dir = self.test_dir / "identities"
        self.identities_dir.mkdir()

        # Create a dummy database
        with open(self.db_path, "w") as f:
            f.write("dummy db content")

        # Create a dummy identity
        self.id_path = self.identities_dir / "test_id"
        self.id_path.mkdir()
        with open(self.id_path / "identity", "w") as f:
            f.write("dummy identity content")

        self.manager = IntegrityManager(self.test_dir, self.db_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_initial_run(self):
        """Test integrity check when no manifest exists."""
        is_ok, issues = self.manager.check_integrity()
        self.assertTrue(is_ok)
        self.assertIn("Initial run", issues[0])

    def test_integrity_success(self):
        """Test integrity check matches saved state."""
        self.manager.save_manifest()
        is_ok, issues = self.manager.check_integrity()
        self.assertTrue(is_ok)
        self.assertEqual(len(issues), 0)

    def test_database_tampered(self):
        """Test detection of database modification."""
        self.manager.save_manifest()

        # Modify DB
        with open(self.db_path, "a") as f:
            f.write("tampered")

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(any("Database modified" in i for i in issues))
        self.assertTrue(any("Last integrity snapshot" in i for i in issues))

    def test_identity_mismatch(self):
        """Test detection of identity mismatch in manifest."""
        self.manager.identity_hash = "original_hash"
        self.manager.save_manifest()

        # Change identity hash
        self.manager.identity_hash = "new_hash"

        # Tamper a file to trigger issues list which includes the metadata check
        with open(self.db_path, "a") as f:
            f.write("tampered")

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(any("Identity mismatch" in i for i in issues))
        self.assertTrue(any("Manifest belongs to: original_hash" in i for i in issues))

    def test_identity_tampered(self):
        """Test detection of identity file modification."""
        self.manager.save_manifest()

        # Modify Identity
        with open(self.id_path / "identity", "a") as f:
            f.write("tampered")

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(any("File modified" in i for i in issues))

    def test_new_identity_detected(self):
        """Test detection of unauthorized new identity files."""
        self.manager.save_manifest()

        # Add new identity
        new_id = self.identities_dir / "new_id"
        new_id.mkdir()
        with open(new_id / "identity", "w") as f:
            f.write("unauthorized")

        is_ok, issues = self.manager.check_integrity()
        self.assertFalse(is_ok)
        self.assertTrue(any("New file detected" in i for i in issues))


if __name__ == "__main__":
    unittest.main()
