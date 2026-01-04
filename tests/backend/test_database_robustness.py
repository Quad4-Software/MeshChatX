import unittest
import os
import tempfile
import shutil
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


class TestDatabaseRobustness(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_meshchat.db")
        # Ensure we start with a fresh provider instance
        if hasattr(DatabaseProvider, "_instance"):
            DatabaseProvider._instance = None
        self.provider = DatabaseProvider.get_instance(self.db_path)
        self.schema = DatabaseSchema(self.provider)

    def tearDown(self):
        self.provider.close_all()
        if hasattr(DatabaseProvider, "_instance"):
            DatabaseProvider._instance = None
        shutil.rmtree(self.test_dir)

    def test_missing_column_healing(self):
        # 1. Create a "legacy" table without the peer_hash column
        self.provider.execute("""
            CREATE TABLE lxmf_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE,
                source_hash TEXT,
                destination_hash TEXT
            )
        """)

        # 2. Also need the config table so initialize doesn't fail on version check
        self.provider.execute("""
            CREATE TABLE config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT
            )
        """)
        self.provider.execute(
            "INSERT INTO config (key, value) VALUES (?, ?)", ("database_version", "1")
        )

        # 3. Attempt initialization.
        # Previously this would crash with OperationalError: no such column: peer_hash
        try:
            self.schema.initialize()
        except Exception as e:
            self.fail(f"Initialization failed with missing column: {e}")

        # 4. Verify the column was added
        cursor = self.provider.execute("PRAGMA table_info(lxmf_messages)")
        columns = [row[1] for row in cursor.fetchall()]
        self.assertIn("peer_hash", columns)
        self.assertIn("is_spam", columns)

    def test_corrupt_config_initialization(self):
        # 1. Create a database where the version is missing or garbled
        self.provider.execute("""
            CREATE TABLE config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT
            )
        """)
        # No version inserted

        # 2. Initialization should still work
        try:
            self.schema.initialize()
        except Exception as e:
            self.fail(f"Initialization failed with missing version: {e}")

        # 3. Version should now be set to LATEST
        row = self.provider.fetchone(
            "SELECT value FROM config WHERE key = 'database_version'"
        )
        self.assertEqual(int(row["value"]), self.schema.LATEST_VERSION)


if __name__ == "__main__":
    unittest.main()
