import os
import shutil
import sqlite3
import tempfile
import unittest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.legacy_migrator import LegacyMigrator
from meshchatx.src.backend.database.provider import DatabaseProvider


class TestDatabaseMigration(unittest.TestCase):
    def setUp(self):
        DatabaseProvider._instance = None
        self.test_dir = tempfile.mkdtemp()
        # Legacy migrator expects a specific structure: reticulum_config_dir/identities/identity_hash_hex/database.db
        self.identity_hash = "deadbeef"
        self.legacy_config_dir = os.path.join(self.test_dir, "legacy_config")
        self.legacy_db_subdir = os.path.join(
            self.legacy_config_dir, "identities", self.identity_hash,
        )
        os.makedirs(self.legacy_db_subdir, exist_ok=True)
        self.legacy_db_path = os.path.join(self.legacy_db_subdir, "database.db")

        # Create legacy database with 1.x/2.x schema
        self.create_legacy_db(self.legacy_db_path)

        # Current database
        self.current_db_path = os.path.join(self.test_dir, "current.db")
        self.db = Database(self.current_db_path)
        self.db.initialize()

    def tearDown(self):
        self.db.close_all()
        shutil.rmtree(self.test_dir)

    def create_legacy_db(self, path):
        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        # Based on liamcottle/reticulum-meshchat/database.py
        cursor.execute("""
            CREATE TABLE config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                created_at DATETIME,
                updated_at DATETIME
            )
        """)

        cursor.execute("""
            CREATE TABLE announces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destination_hash TEXT UNIQUE,
                aspect TEXT,
                identity_hash TEXT,
                identity_public_key TEXT,
                app_data TEXT,
                rssi INTEGER,
                snr REAL,
                quality REAL,
                created_at DATETIME,
                updated_at DATETIME
            )
        """)

        cursor.execute("""
            CREATE TABLE lxmf_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE,
                source_hash TEXT,
                destination_hash TEXT,
                state TEXT,
                progress REAL,
                is_incoming INTEGER,
                method TEXT,
                delivery_attempts INTEGER,
                next_delivery_attempt_at REAL,
                title TEXT,
                content TEXT,
                fields TEXT,
                timestamp REAL,
                rssi INTEGER,
                snr REAL,
                quality REAL,
                created_at DATETIME,
                updated_at DATETIME
            )
        """)

        # Insert some legacy data
        cursor.execute(
            "INSERT INTO config (key, value) VALUES (?, ?)",
            ("legacy_key", "legacy_value"),
        )
        cursor.execute(
            "INSERT INTO announces (destination_hash, aspect, identity_hash) VALUES (?, ?, ?)",
            ("dest1", "lxmf.delivery", "id1"),
        )
        cursor.execute(
            "INSERT INTO lxmf_messages (hash, source_hash, destination_hash, title, content, fields, is_incoming, state, progress, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "msg1",
                "src1",
                "dest1",
                "Old Title",
                "Old Content",
                "{}",
                1,
                "delivered",
                1.0,
                123456789.0,
            ),
        )

        conn.commit()
        conn.close()

    def test_migration_evolution(self):
        migrator = LegacyMigrator(
            self.db.provider, self.legacy_config_dir, self.identity_hash,
        )

        # Check if should migrate
        self.assertTrue(
            migrator.should_migrate(), "Should detect legacy database for migration",
        )

        # Perform migration
        success = migrator.migrate()
        self.assertTrue(success, "Migration should complete successfully")

        # Verify data in current database
        config_rows = self.db.provider.fetchall("SELECT * FROM config")
        print(f"Config rows: {config_rows}")

        config_val = self.db.provider.fetchone(
            "SELECT value FROM config WHERE key = ?", ("legacy_key",),
        )
        self.assertIsNotNone(config_val, "legacy_key should have been migrated")
        self.assertEqual(config_val["value"], "legacy_value")

        ann_count = self.db.provider.fetchone(
            "SELECT COUNT(*) as count FROM announces",
        )["count"]
        self.assertEqual(ann_count, 1)

        msg = self.db.provider.fetchone(
            "SELECT * FROM lxmf_messages WHERE hash = ?", ("msg1",),
        )
        self.assertIsNotNone(msg)
        self.assertEqual(msg["title"], "Old Title")
        self.assertEqual(msg["content"], "Old Content")
        self.assertEqual(msg["source_hash"], "src1")


if __name__ == "__main__":
    unittest.main()
