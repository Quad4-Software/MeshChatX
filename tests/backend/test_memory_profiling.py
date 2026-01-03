import unittest
import os
import shutil
import tempfile
import random
import secrets
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.identity_manager import IdentityManager
from meshchatx.src.backend.announce_manager import AnnounceManager
from tests.backend.benchmarking_utils import MemoryTracker, get_memory_usage_mb


class TestMemoryProfiling(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")
        self.db = Database(self.db_path)
        self.db.initialize()

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_database_growth(self):
        """Profile memory growth during heavy database insertions."""
        with MemoryTracker("Database Growth (10k messages)") as tracker:
            num_messages = 10000
            peer_hash = secrets.token_hex(16)

            # Using transaction for speed, but tracking overall memory
            with self.db.provider:
                for i in range(num_messages):
                    msg = {
                        "hash": secrets.token_hex(16),
                        "source_hash": peer_hash,
                        "destination_hash": "my_hash",
                        "peer_hash": peer_hash,
                        "state": "delivered",
                        "progress": 1.0,
                        "is_incoming": 1,
                        "method": "direct",
                        "delivery_attempts": 1,
                        "title": f"Msg {i}",
                        "content": "A" * 512,  # 512 bytes content
                        "fields": "{}",
                        "timestamp": 1234567890 + i,
                        "rssi": -50,
                        "snr": 5.0,
                        "quality": 3,
                        "is_spam": 0,
                    }
                    self.db.messages.upsert_lxmf_message(msg)

        # We expect some growth due to DB internal caching, but not excessive
        # 10k messages * 512 bytes is ~5MB of raw content.
        # SQLite should handle this efficiently.
        self.assertLess(
            tracker.mem_delta, 20.0, "Excessive memory growth during DB insertion"
        )

    def test_identity_manager_memory(self):
        """Profile memory usage of identity manager with many identities."""
        manager = IdentityManager(self.test_dir)

        with MemoryTracker("Identity Manager (50 identities)") as tracker:
            for i in range(50):
                manager.create_identity(f"Profile {i}")

            # Listing all identities
            identities = manager.list_identities()
            self.assertEqual(len(identities), 50)

        self.assertLess(
            tracker.mem_delta, 10.0, "Identity management consumed too much memory"
        )

    def test_large_message_processing(self):
        """Profile memory when handling very large messages."""
        large_content = "B" * (1024 * 1024)  # 1MB message
        peer_hash = secrets.token_hex(16)

        with MemoryTracker("Large Message (1MB)") as tracker:
            msg = {
                "hash": secrets.token_hex(16),
                "source_hash": peer_hash,
                "destination_hash": "my_hash",
                "peer_hash": peer_hash,
                "state": "delivered",
                "progress": 1.0,
                "is_incoming": 1,
                "method": "direct",
                "delivery_attempts": 1,
                "title": "Large Message",
                "content": large_content,
                "fields": "{}",
                "timestamp": 1234567890,
                "rssi": -50,
                "snr": 5.0,
                "quality": 3,
                "is_spam": 0,
            }
            self.db.messages.upsert_lxmf_message(msg)

            # Fetch it back
            fetched = self.db.messages.get_lxmf_message_by_hash(msg["hash"])
            self.assertEqual(len(fetched["content"]), len(large_content))

        # 1MB message shouldn't cause much more than a few MBs of overhead
        self.assertLess(tracker.mem_delta, 5.0, "Large message handling leaked memory")

    def test_announce_manager_leaks(self):
        """Test for memory leaks in AnnounceManager during repeated updates."""
        announce_manager = AnnounceManager(self.db)

        with MemoryTracker("Announce Stress (2k unique announces)") as tracker:
            for i in range(2000):
                data = {
                    "destination_hash": secrets.token_hex(16),
                    "aspect": "lxmf.delivery",
                    "identity_hash": secrets.token_hex(16),
                    "identity_public_key": "pubkey",
                    "app_data": "some data " * 10,
                    "rssi": -50,
                    "snr": 5.0,
                    "quality": 3,
                }
                self.db.announces.upsert_announce(data)

        self.assertLess(
            tracker.mem_delta, 15.0, "Announce updates causing memory bloat"
        )


if __name__ == "__main__":
    unittest.main()
