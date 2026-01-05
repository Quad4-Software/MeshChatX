import gc
import json
import os
import random
import secrets
import shutil
import tempfile
import time
from unittest.mock import MagicMock

import psutil

from meshchatx.src.backend.database import Database


def get_memory_usage():
    """Returns current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def generate_hash():
    return secrets.token_hex(16)


class MapBenchmarker:
    def __init__(self):
        self.results = []
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "map_perf_test.db")
        self.db = Database(self.db_path)
        self.db.initialize()
        self.identity_hash = generate_hash()

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

    def benchmark_telemetry_insertion(self, count=1000):
        def run_telemetry():
            with self.db.provider:
                for i in range(count):
                    self.db.telemetry.upsert_telemetry(
                        destination_hash=generate_hash(),
                        timestamp=time.time(),
                        data=os.urandom(100),  # simulate packed telemetry
                        received_from=generate_hash(),
                    )

        self.record_benchmark(
            f"Telemetry Insertion ({count} entries)",
            run_telemetry,
            count,
        )

    def benchmark_telemetry_retrieval(self, count=100):
        # Seed some data first
        dest_hash = generate_hash()
        for i in range(500):
            self.db.telemetry.upsert_telemetry(
                destination_hash=dest_hash,
                timestamp=time.time() - i,
                data=os.urandom(100),
            )

        def run_retrieval():
            for _ in range(count):
                self.db.telemetry.get_telemetry_history(dest_hash, limit=100)

        self.record_benchmark(
            f"Telemetry History Retrieval ({count} calls)",
            run_retrieval,
            count,
        )

    def benchmark_drawing_storage(self, count=500):
        # Create a large GeoJSON-like string
        dummy_data = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                random.uniform(-180, 180),
                                random.uniform(-90, 90),
                            ],
                        },
                        "properties": {"name": f"Marker {i}"},
                    }
                    for i in range(100)
                ],
            },
        )

        def run_drawings():
            with self.db.provider:
                for i in range(count):
                    self.db.map_drawings.upsert_drawing(
                        identity_hash=self.identity_hash,
                        name=f"Layer {i}",
                        data=dummy_data,
                    )

        self.record_benchmark(
            f"Map Drawing Insertion ({count} layers)",
            run_drawings,
            count,
        )

    def benchmark_drawing_listing(self, count=100):
        def run_list():
            for _ in range(count):
                self.db.map_drawings.get_drawings(self.identity_hash)

        self.record_benchmark(f"Map Drawing Listing ({count} calls)", run_list, count)

    def benchmark_mbtiles_listing(self, count=100):
        from meshchatx.src.backend.map_manager import MapManager

        # Mock config
        config = MagicMock()
        config.map_mbtiles_dir.get.return_value = self.temp_dir

        # Create some dummy .mbtiles files
        for i in range(5):
            with open(os.path.join(self.temp_dir, f"test_{i}.mbtiles"), "w") as f:
                f.write("dummy")

        mm = MapManager(config, self.temp_dir)

        def run_list():
            for _ in range(count):
                mm.list_mbtiles()

        self.record_benchmark(
            f"MBTiles Listing ({count} calls, 5 files)",
            run_list,
            count,
        )


def main():
    print("Starting Map-related Performance Benchmarking...")
    bench = MapBenchmarker()
    try:
        bench.benchmark_telemetry_insertion(1000)
        bench.benchmark_telemetry_retrieval(100)
        bench.benchmark_drawing_storage(500)
        bench.benchmark_drawing_listing(100)
        bench.benchmark_mbtiles_listing(100)

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
