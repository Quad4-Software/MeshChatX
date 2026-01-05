import gc
import os
import time
from functools import wraps

import psutil


def get_memory_usage_mb():
    """Returns the current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


class BenchmarkResult:
    def __init__(self, name, duration_ms, memory_delta_mb):
        self.name = name
        self.duration_ms = duration_ms
        self.memory_delta_mb = memory_delta_mb

    def __repr__(self):
        return f"<BenchmarkResult {self.name}: {self.duration_ms:.2f}ms, {self.memory_delta_mb:.2f}MB>"


def benchmark(name=None, iterations=1):
    """Decorator to benchmark a function's execution time and memory delta."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            bench_name = name or func.__name__

            # Warm up and GC
            gc.collect()
            time.sleep(0.1)

            start_mem = get_memory_usage_mb()
            start_time = time.time()

            result_val = None
            for _ in range(iterations):
                result_val = func(*args, **kwargs)

            end_time = time.time()
            # Force GC to see persistent memory growth
            gc.collect()
            end_mem = get_memory_usage_mb()

            duration = (end_time - start_time) * 1000 / iterations
            mem_delta = end_mem - start_mem

            print(f"BENCHMARK: {bench_name}")
            print(f"  Iterations: {iterations}")
            print(f"  Avg Duration: {duration:.2f} ms")
            print(f"  Memory Delta: {mem_delta:.2f} MB")

            return result_val, BenchmarkResult(bench_name, duration, mem_delta)

        return wrapper

    return decorator


class MemoryTracker:
    """Helper to track memory changes over a block of code."""

    def __init__(self, name):
        self.name = name
        self.start_mem = 0
        self.end_mem = 0

    def __enter__(self):
        gc.collect()
        self.start_mem = get_memory_usage_mb()
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        gc.collect()
        self.end_mem = get_memory_usage_mb()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.mem_delta = self.end_mem - self.start_mem
        print(
            f"TRACKER [{self.name}]: {self.duration_ms:.2f}ms, {self.mem_delta:.2f}MB",
        )
