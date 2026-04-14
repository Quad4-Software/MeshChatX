"""Wall-clock database throughput tests (large seeds + strict ms ceilings).

Excluded from default `task test:be` / CI (like test_performance_hotpaths.py and
test_memory_profiling.py). Run locally: `task test:be:perf` or
`pytest tests/backend/test_performance_bottlenecks.py`.
"""

import os
import secrets
import shutil
import tempfile
import time
import unittest
from unittest.mock import MagicMock

from meshchatx.src.backend.announce_manager import AnnounceManager
from meshchatx.src.backend.database import Database


def _ci_ms_ceiling(local_ms: float, factor: float = 3.0) -> float:
    """Shared runners are noisy; relax ceilings when CI is set."""
    if os.environ.get("CI"):
        return local_ms * factor
    return local_ms


def _ci_seconds_ceiling(local_s: float, factor: float = 3.0) -> float:
    if os.environ.get("CI"):
        return local_s * factor
    return local_s


class TestPerformanceBottlenecks(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "perf_bottleneck.db")
        self.db = Database(self.db_path)
        self.db.initialize()
        self.announce_manager = AnnounceManager(self.db)
        self.reticulum_mock = MagicMock()
        self.reticulum_mock.get_packet_rssi.return_value = -50
        self.reticulum_mock.get_packet_snr.return_value = 5.0
        self.reticulum_mock.get_packet_q.return_value = 3

    def tearDown(self):
        self.db.close_all()
        shutil.rmtree(self.test_dir)

    def test_message_pagination_performance(self):
        """Test performance of message pagination with a large dataset."""
        num_messages = 10000
        peer_hash = secrets.token_hex(16)

        print(f"\nSeeding {num_messages} messages for pagination test...")
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
                    "content": "Content",
                    "fields": "{}",
                    "timestamp": time.time() - i,
                    "rssi": -50,
                    "snr": 5.0,
                    "quality": 3,
                    "is_spam": 0,
                }
                self.db.messages.upsert_lxmf_message(msg)

        # Benchmark different offsets
        offsets = [0, 1000, 5000, 9000]
        limit = 50
        for offset in offsets:
            start = time.time()
            msgs = self.db.messages.get_conversation_messages(
                peer_hash,
                limit=limit,
                offset=offset,
            )
            duration = (time.time() - start) * 1000
            print(f"Fetch {limit} messages at offset {offset}: {duration:.2f}ms")
            self.assertEqual(len(msgs), limit)
            self.assertLess(
                duration,
                _ci_ms_ceiling(50),
                f"Pagination at offset {offset} is too slow!",
            )

    def test_announce_flood_bottleneck(self):
        """Simulate a flood of incoming announces and measure processing time."""
        num_announces = 500
        identities = [MagicMock() for _ in range(num_announces)]
        for i, ident in enumerate(identities):
            ident.hash = MagicMock()
            ident.hash.hex.return_value = secrets.token_hex(16)
            ident.get_public_key.return_value = b"public_key"

        print(f"\nSimulating flood of {num_announces} announces...")
        start_total = time.time()

        # We simulate what meshchat.on_lxmf_announce_received does
        with self.db.provider:
            for i in range(num_announces):
                dest_hash = secrets.token_hex(16)
                aspect = "lxmf.delivery"
                app_data = b"app_data"
                packet_hash = b"packet_hash"

                self.announce_manager.upsert_announce(
                    self.reticulum_mock,
                    identities[i],
                    dest_hash,
                    aspect,
                    app_data,
                    packet_hash,
                )

                # Simulate the fetch after upsert which is also done in the app
                self.db.announces.get_announce_by_hash(dest_hash)

        duration_total = time.time() - start_total
        avg_duration = (duration_total / num_announces) * 1000
        print(
            f"Processed {num_announces} announces in {duration_total:.2f}s (Avg: {avg_duration:.2f}ms/announce)",
        )

        self.assertLess(
            avg_duration,
            _ci_ms_ceiling(20),
            "Announce processing is too slow!",
        )

    def test_announce_pagination_performance(self):
        """Test performance of announce pagination with search and filtering."""
        num_announces = 5000
        print(f"\nSeeding {num_announces} announces for pagination test...")
        with self.db.provider:
            for i in range(num_announces):
                data = {
                    "destination_hash": secrets.token_hex(16),
                    "aspect": "lxmf.delivery" if i % 2 == 0 else "lxst.telephony",
                    "identity_hash": secrets.token_hex(16),
                    "identity_public_key": "pubkey",
                    "app_data": "data",
                    "rssi": -50,
                    "snr": 5.0,
                    "quality": 3,
                }
                self.db.announces.upsert_announce(data)

        # Benchmark filtered search with pagination
        start = time.time()
        results = self.announce_manager.get_filtered_announces(
            aspect="lxmf.delivery",
            limit=50,
            offset=1000,
        )
        duration = (time.time() - start) * 1000
        print(f"Filtered announce pagination (offset 1000): {duration:.2f}ms")
        self.assertEqual(len(results), 50)
        self.assertLess(
            duration,
            _ci_ms_ceiling(50),
            "Announce pagination is too slow!",
        )

    def test_concurrent_announce_handling(self):
        """Test how the database handles concurrent announce insertions from multiple threads."""
        import threading

        num_threads = 10
        announces_per_thread = 50

        def insert_announces():
            for _ in range(announces_per_thread):
                dest_hash = secrets.token_hex(16)
                ident = MagicMock()
                ident.hash.hex.return_value = secrets.token_hex(16)
                ident.get_public_key.return_value = b"pubkey"

                self.announce_manager.upsert_announce(
                    self.reticulum_mock,
                    ident,
                    dest_hash,
                    "lxmf.delivery",
                    b"data",
                    b"packet",
                )

        threads = [
            threading.Thread(target=insert_announces) for _ in range(num_threads)
        ]

        print(
            f"\nRunning {num_threads} threads inserting {announces_per_thread} announces each...",
        )
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        duration = time.time() - start

        print(
            f"Concurrent insertion took {duration:.2f}s for {num_threads * announces_per_thread} announces",
        )
        self.assertLess(
            duration,
            _ci_seconds_ceiling(10.0),
            "Concurrent announce insertion is too slow!",
        )


if __name__ == "__main__":
    unittest.main()
