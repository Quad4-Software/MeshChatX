import os
import secrets
import shutil
import tempfile
import threading
import time
import unittest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.identity_manager import IdentityManager


class TestConcurrencyStress(unittest.TestCase):
    def setUp(self):
        # Reset DatabaseProvider singleton for clean state
        DatabaseProvider._instance = None

        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "stress.db")
        self.db = Database(self.db_path)
        self.db.initialize()
        self.stop_threads = False
        self.errors = []

    def tearDown(self):
        self.stop_threads = True
        self.db.close_all()
        # Reset again
        DatabaseProvider._instance = None
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def db_writer_worker(self, worker_id):
        """Spams the message table with inserts and updates."""
        try:
            from meshchatx.src.backend.database.messages import MessageDAO

            provider = DatabaseProvider.get_instance(self.db_path)
            dao = MessageDAO(provider)
            peer_hash = secrets.token_hex(16)
            count = 0
            while not self.stop_threads and count < 50:
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
                    "title": f"Stress Msg {worker_id}-{count}",
                    "content": "A" * 128,
                    "fields": "{}",
                    "timestamp": time.time(),
                    "rssi": -50,
                    "snr": 5.0,
                    "quality": 3,
                    "is_spam": 0,
                }
                with provider:
                    dao.upsert_lxmf_message(msg)
                count += 1
                time.sleep(0.001)
        except Exception as e:
            self.errors.append(f"Writer Worker {worker_id} ERROR: {e}")

    def db_reader_worker(self, worker_id):
        """Spams the message table with reads and searches."""
        try:
            from meshchatx.src.backend.database.announces import AnnounceDAO
            from meshchatx.src.backend.database.messages import MessageDAO

            provider = DatabaseProvider.get_instance(self.db_path)
            msg_dao = MessageDAO(provider)
            ann_dao = AnnounceDAO(provider)

            count = 0
            while not self.stop_threads and count < 50:
                # Perform various reads
                msg_dao.get_conversations()
                ann_dao.get_filtered_announces(limit=10)
                count += 1
                time.sleep(0.001)
        except Exception as e:
            self.errors.append(f"Reader Worker {worker_id} ERROR: {e}")

    def test_database_concurrency(self):
        """Launches multiple reader and writer threads to check for lock contention."""
        writers = [
            threading.Thread(target=self.db_writer_worker, args=(i,)) for i in range(5)
        ]
        readers = [
            threading.Thread(target=self.db_reader_worker, args=(i,)) for i in range(5)
        ]

        for t in writers + readers:
            t.start()

        for t in writers + readers:
            t.join()

        # Assert no errors occurred in threads
        if self.errors:
            self.fail("Errors occurred in threads: \n" + "\n".join(self.errors))

        # Check if we ended up with the expected number of messages
        total = self.db.provider.fetchone(
            "SELECT COUNT(*) as count FROM lxmf_messages",
        )["count"]
        self.assertEqual(
            total, 5 * 50, "Total messages inserted doesn't match expected count",
        )
        print(f"Stress test completed. Total messages inserted: {total}")

    def test_identity_and_db_collision(self):
        """Tests potential collisions between IdentityManager and Database access."""
        manager = IdentityManager(self.test_dir)

        def identity_worker():
            try:
                for i in range(20):
                    if self.stop_threads:
                        break
                    manager.create_identity(f"Stress ID {i}")
                    manager.list_identities()
                    time.sleep(0.01)
            except Exception as e:
                self.errors.append(f"Identity Worker ERROR: {e}")

        id_thread = threading.Thread(target=identity_worker)
        db_thread = threading.Thread(
            target=self.db_writer_worker, args=("id_collision",),
        )

        id_thread.start()
        db_thread.start()

        id_thread.join()
        db_thread.join()

        # Assert no errors occurred
        if self.errors:
            self.fail("Errors occurred in threads: \n" + "\n".join(self.errors))

        identities = manager.list_identities()
        self.assertEqual(len(identities), 20, "Should have created 20 identities")

        total_messages = self.db.provider.fetchone(
            "SELECT COUNT(*) as count FROM lxmf_messages",
        )["count"]
        self.assertEqual(
            total_messages, 50, "Should have inserted 50 messages during collision test",
        )


if __name__ == "__main__":
    unittest.main()
