import gc
import os
import random
import secrets
import shutil
import tempfile
import time

import psutil

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.recovery import CrashRecovery


def get_memory_usage():
    """Returns current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def generate_hash():
    return secrets.token_hex(16)


class PerformanceBenchmarker:
    def __init__(self):
        self.results = []
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "perf_test.db")
        self.db = Database(self.db_path)
        self.db.initialize()
        self.my_hash = generate_hash()

    def cleanup(self):
        self.db.close()
        shutil.rmtree(self.temp_dir)

    def record_benchmark(self, name, operation, iterations=1):
        gc.collect()
        start_mem = get_memory_usage()
        start_time = time.time()

        operation()

        end_time = time.time()
        gc.collect()
        end_mem = get_memory_usage()

        duration = (end_time - start_time) / iterations
        mem_diff = end_mem - start_mem

        result = {
            "name": name,
            "duration_ms": duration * 1000,
            "memory_growth_mb": mem_diff,
            "iterations": iterations,
        }
        self.results.append(result)
        print(f"Benchmark: {name}")
        print(f"  Avg Duration: {result['duration_ms']:.2f} ms")
        print(f"  Memory Growth: {result['memory_growth_mb']:.2f} MB")
        return result

    def benchmark_message_flood(self, count=1000):
        peer_hashes = [generate_hash() for _ in range(50)]

        def run_flood():
            for i in range(count):
                peer_hash = random.choice(peer_hashes)
                is_incoming = i % 2 == 0
                msg = {
                    "hash": generate_hash(),
                    "source_hash": peer_hash if is_incoming else self.my_hash,
                    "destination_hash": self.my_hash if is_incoming else peer_hash,
                    "peer_hash": peer_hash,
                    "state": "delivered",
                    "progress": 1.0,
                    "is_incoming": is_incoming,
                    "method": "direct",
                    "delivery_attempts": 1,
                    "title": f"Flood Msg {i}",
                    "content": "X" * 1024,  # 1KB content
                    "fields": "{}",
                    "timestamp": time.time(),
                    "rssi": -50,
                    "snr": 5.0,
                    "quality": 3,
                    "is_spam": 0,
                }
                self.db.messages.upsert_lxmf_message(msg)

        self.record_benchmark(f"Message Flood ({count} msgs)", run_flood, count)

    def benchmark_conversation_fetching(self):
        def fetch_convs():
            for _ in range(100):
                self.db.messages.get_conversations()

        self.record_benchmark("Fetch 100 Conversations Lists", fetch_convs, 100)

    def benchmark_crash_recovery_overhead(self):
        recovery = CrashRecovery(
            storage_dir=self.temp_dir,
            database_path=self.db_path,
            public_dir=os.path.join(self.temp_dir, "public"),
        )
        os.makedirs(recovery.public_dir, exist_ok=True)
        with open(os.path.join(recovery.public_dir, "index.html"), "w") as f:
            f.write("test")

        def run_recovery_check():
            for _ in range(50):
                # Simulate the periodic or manual diagnosis check
                recovery.run_diagnosis(file=open(os.devnull, "w"))

        self.record_benchmark(
            "CrashRecovery Diagnosis Overhead (50 runs)",
            run_recovery_check,
            50,
        )

    def benchmark_identity_generation(self, count=20):
        import RNS

        def run_gen():
            for _ in range(count):
                RNS.Identity(create_keys=True)

        self.record_benchmark(
            f"RNS Identity Generation ({count} identities)",
            run_gen,
            count,
        )

    def benchmark_identity_listing(self, count=100):
        from meshchatx.src.backend.identity_manager import IdentityManager

        # We need to create identities with real DBs to test listing performance
        manager = IdentityManager(self.temp_dir)

        hashes = []
        for i in range(10):
            res = manager.create_identity(f"Test {i}")
            hashes.append(res["hash"])

        def run_list():
            for _ in range(count):
                manager.list_identities(current_identity_hash=hashes[0])

        self.record_benchmark(
            f"Identity Listing ({count} runs, 10 identities)",
            run_list,
            count,
        )

    def benchmark_announce_trim(self, seed_count=800, runs=40):
        aspect = "lxmf.delivery"

        def seed():
            with self.db.provider:
                for _ in range(seed_count):
                    self.db.announces.upsert_announce(
                        {
                            "destination_hash": generate_hash(),
                            "aspect": aspect,
                            "identity_hash": generate_hash(),
                            "identity_public_key": "cHVibmtleQ==",
                            "app_data": None,
                            "rssi": None,
                            "snr": None,
                            "quality": None,
                        },
                    )

        seed()

        def run_trim():
            for _ in range(runs):
                self.db.announces.trim_announces_for_aspect(
                    aspect,
                    max(1, seed_count // 2),
                )

        self.record_benchmark(
            f"Announce trim ({seed_count} rows, {runs} trims)",
            run_trim,
            runs,
        )


def main():
    print("Starting Backend Memory & Performance Benchmarking...")
    bench = PerformanceBenchmarker()
    try:
        bench.benchmark_message_flood(2000)
        bench.benchmark_conversation_fetching()
        bench.benchmark_crash_recovery_overhead()
        bench.benchmark_identity_generation()
        bench.benchmark_identity_listing()
        bench.benchmark_announce_trim()

        print("\n" + "=" * 80)
        print(f"{'Benchmark Name':40} | {'Avg Time':10} | {'Mem Growth':10}")
        print("-" * 80)
        for r in bench.results:
            print(
                f"{r['name']:40} | {r['duration_ms']:8.2f} ms | {r['memory_growth_mb']:8.2f} MB",
            )
        print("=" * 80)

    finally:
        bench.cleanup()


if __name__ == "__main__":
    main()
