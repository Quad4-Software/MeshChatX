import os
import random
import secrets
import shutil
import sys
import tempfile
import time

# Ensure we can import meshchatx
sys.path.append(os.getcwd())

import json

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.telephone import TelephoneDAO
from meshchatx.src.backend.identity_manager import IdentityManager
from tests.backend.benchmarking_utils import (
    benchmark,
    get_memory_usage_mb,
)


class BackendBenchmarker:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "benchmark.db")
        self.db = Database(self.db_path)
        self.db.initialize()
        self.results = []
        self.my_hash = secrets.token_hex(16)

    def cleanup(self):
        self.db.close()
        shutil.rmtree(self.temp_dir)

    def run_all(self, extreme=False):
        print(f"\n{'=' * 20} BACKEND BENCHMARKING START {'=' * 20}")
        print(f"Mode: {'EXTREME (Breaking Space)' if extreme else 'Standard'}")
        print(f"Base Memory: {get_memory_usage_mb():.2f} MB")

        self.bench_db_initialization()

        if extreme:
            self.bench_extreme_message_flood()
            self.bench_extreme_announce_flood()
            self.bench_extreme_identity_bloat()
        else:
            self.bench_message_operations()
            self.bench_announce_operations()
            self.bench_identity_operations()

        self.bench_telephony_operations()

        self.print_summary()

    def bench_extreme_message_flood(self):
        """Insert 100,000 messages with large randomized content."""
        peer_hashes = [secrets.token_hex(16) for _ in range(200)]
        total_messages = 100000
        batch_size = 5000

        @benchmark("EXTREME: 100k Message Flood", iterations=1)
        def run_extreme_flood():
            for b in range(0, total_messages, batch_size):
                with self.db.provider:
                    for i in range(batch_size):
                        peer_hash = random.choice(peer_hashes)
                        msg = {
                            "hash": secrets.token_hex(16),
                            "source_hash": peer_hash,
                            "destination_hash": self.my_hash,
                            "peer_hash": peer_hash,
                            "state": "delivered",
                            "progress": 1.0,
                            "is_incoming": True,
                            "method": "direct",
                            "delivery_attempts": 1,
                            "title": f"Extreme Msg {b + i}",
                            "content": secrets.token_bytes(
                                1024,
                            ).hex(),  # 2KB hex string
                            "fields": json.dumps({"test": "data" * 10}),
                            "timestamp": time.time() - (total_messages - (b + i)),
                            "rssi": -random.randint(30, 120),
                            "snr": random.uniform(-20, 15),
                            "quality": random.randint(0, 3),
                            "is_spam": 0,
                        }
                        self.db.messages.upsert_lxmf_message(msg)
                print(
                    f"  Progress: {b + batch_size}/{total_messages} messages inserted...",
                )

        @benchmark("EXTREME: Search 100k Messages (Wildcard)", iterations=5)
        def run_extreme_search():
            return self.db.messages.get_conversation_messages(
                peer_hashes[0],
                limit=100,
                offset=50000,
            )

        _, res_flood = run_extreme_flood()
        self.results.append(res_flood)

        _, res_search = run_extreme_search()
        self.results.append(res_search)

    def bench_extreme_announce_flood(self):
        """Insert 50,000 unique announces and perform heavy filtering."""
        total = 50000
        batch = 5000

        @benchmark("EXTREME: 50k Announce Flood", iterations=1)
        def run_ann_flood():
            for b in range(0, total, batch):
                with self.db.provider:
                    for i in range(batch):
                        data = {
                            "destination_hash": secrets.token_hex(16),
                            "aspect": random.choice(
                                ["lxmf.delivery", "lxst.telephony", "group.chat"],
                            ),
                            "identity_hash": secrets.token_hex(16),
                            "identity_public_key": secrets.token_hex(32),
                            "app_data": secrets.token_hex(128),
                            "rssi": -random.randint(50, 100),
                            "snr": 5.0,
                            "quality": 3,
                        }
                        self.db.announces.upsert_announce(data)
                print(f"  Progress: {b + batch}/{total} announces inserted...")

        @benchmark("EXTREME: Filter 50k Announces (Complex)", iterations=10)
        def run_ann_filter():
            return self.db.announces.get_filtered_announces(
                aspect="lxmf.delivery",
                limit=100,
                offset=25000,
            )

        _, res_flood = run_ann_flood()
        self.results.append(res_flood)

        _, res_filter = run_ann_filter()
        self.results.append(res_filter)

    def bench_extreme_identity_bloat(self):
        """Create 1,000 identities and list them."""
        manager = IdentityManager(self.temp_dir)

        @benchmark("EXTREME: Create 1000 Identities", iterations=1)
        def run_id_bloat():
            for i in range(1000):
                manager.create_identity(f"Extreme ID {i}")
                if i % 100 == 0:
                    print(f"  Progress: {i}/1000 identities...")

        @benchmark("EXTREME: List 1000 Identities", iterations=5)
        def run_id_list():
            return manager.list_identities()

        _, res_bloat = run_id_bloat()
        self.results.append(res_bloat)

        _, res_list = run_id_list()
        self.results.append(res_list)

    def bench_db_initialization(self):
        @benchmark("Database Initialization", iterations=5)
        def run():
            tmp_db_path = os.path.join(
                self.temp_dir,
                f"init_test_{random.randint(0, 1000)}.db",
            )
            db = Database(tmp_db_path)
            db.initialize()
            db.close()
            os.remove(tmp_db_path)

        _, res = run()
        self.results.append(res)

    def bench_message_operations(self):
        peer_hashes = [secrets.token_hex(16) for _ in range(50)]

        @benchmark("Message Upsert (Batch of 100)", iterations=10)
        def upsert_batch():
            with self.db.provider:
                for i in range(100):
                    peer_hash = random.choice(peer_hashes)
                    msg = {
                        "hash": secrets.token_hex(16),
                        "source_hash": peer_hash,
                        "destination_hash": self.my_hash,
                        "peer_hash": peer_hash,
                        "state": "delivered",
                        "progress": 1.0,
                        "is_incoming": True,
                        "method": "direct",
                        "delivery_attempts": 1,
                        "title": f"Bench Msg {i}",
                        "content": "X" * 256,
                        "fields": "{}",
                        "timestamp": time.time(),
                        "rssi": -50,
                        "snr": 5.0,
                        "quality": 3,
                        "is_spam": 0,
                    }
                    self.db.messages.upsert_lxmf_message(msg)

        @benchmark("Get 100 Conversations List", iterations=10)
        def get_convs():
            return self.db.messages.get_conversations()

        @benchmark("Get Messages for Conversation (offset 500)", iterations=20)
        def get_messages():
            return self.db.messages.get_conversation_messages(
                peer_hashes[0],
                limit=50,
                offset=500,
            )

        _, res = upsert_batch()
        self.results.append(res)

        # Seed some messages for retrieval benchmarks
        for _ in range(10):
            upsert_batch()

        _, res = get_convs()
        self.results.append(res)

        _, res = get_messages()
        self.results.append(res)

    def bench_announce_operations(self):
        @benchmark("Announce Upsert (Batch of 100)", iterations=10)
        def upsert_announces():
            with self.db.provider:
                for i in range(100):
                    data = {
                        "destination_hash": secrets.token_hex(16),
                        "aspect": "lxmf.delivery",
                        "identity_hash": secrets.token_hex(16),
                        "identity_public_key": "pubkey",
                        "app_data": "bench data",
                        "rssi": -50,
                        "snr": 5.0,
                        "quality": 3,
                    }
                    self.db.announces.upsert_announce(data)

        @benchmark("Filtered Announce Retrieval", iterations=20)
        def get_announces():
            return self.db.announces.get_filtered_announces(limit=50)

        _, res = upsert_announces()
        self.results.append(res)
        _, res = get_announces()
        self.results.append(res)

    def bench_identity_operations(self):
        manager = IdentityManager(self.temp_dir)

        @benchmark("Create Identity", iterations=5)
        def create_id():
            return manager.create_identity(f"Bench {random.randint(0, 1000)}")

        @benchmark("List 50 Identities", iterations=10)
        def list_ids():
            return manager.list_identities()

        # Seed some identities
        for i in range(50):
            create_id()

        _, res = create_id()
        self.results.append(res)
        _, res = list_ids()
        self.results.append(res)

    def bench_telephony_operations(self):
        dao = TelephoneDAO(self.db.provider)

        @benchmark("Log Telephone Call", iterations=20)
        def log_call():
            dao.add_call_history(
                remote_identity_hash=secrets.token_hex(16),
                remote_identity_name="Bench Peer",
                is_incoming=False,
                status="completed",
                duration_seconds=120,
                timestamp=time.time(),
            )

        _, res = log_call()
        self.results.append(res)

    def print_summary(self):
        print(f"\n{'=' * 20} BENCHMARK SUMMARY {'=' * 20}")
        print(f"{'Benchmark Name':40} | {'Avg Time':10} | {'Mem Delta':10}")
        print(f"{'-' * 40}-|-{'-' * 10}-|-{'-' * 10}")
        for r in self.results:
            print(
                f"{r.name:40} | {r.duration_ms:8.2f} ms | {r.memory_delta_mb:8.2f} MB",
            )
        print(f"{'=' * 59}")
        print(f"Final Memory Usage: {get_memory_usage_mb():.2f} MB")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MeshChatX Backend Benchmarker")
    parser.add_argument(
        "--extreme",
        action="store_true",
        help="Run extreme stress tests",
    )
    args = parser.parse_args()

    bench = BackendBenchmarker()
    try:
        bench.run_all(extreme=args.extreme)
    finally:
        bench.cleanup()
