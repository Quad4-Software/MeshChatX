# SPDX-License-Identifier: 0BSD

import gc
import os
import statistics
import time
from functools import wraps

import psutil


def get_memory_usage_mb():
    """Returns the current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def median(values):
    """Return the median of a non-empty sequence of numbers."""
    return statistics.median(values)


def median_abs_deviation(values, center=None):
    """Median absolute deviation (MAD) of values around center."""
    if not values:
        return 0.0
    if center is None:
        center = median(values)
    return median([abs(v - center) for v in values])


def coefficient_of_variation(values):
    """Sample CV (stdev / mean). Returns 0 when mean is near zero."""
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    if abs(mean) < 1e-12:
        return 0.0
    return statistics.stdev(values) / abs(mean)


class BenchmarkResult:
    def __init__(
        self,
        name,
        duration_ms,
        memory_delta_mb,
        samples_ms=None,
        iterations=1,
    ):
        self.name = name
        self.duration_ms = duration_ms
        self.memory_delta_mb = memory_delta_mb
        self.samples_ms = list(samples_ms) if samples_ms else [duration_ms]
        self.iterations = iterations
        self.mad_ms = median_abs_deviation(self.samples_ms, center=duration_ms)
        self.cv = coefficient_of_variation(self.samples_ms)

    def __repr__(self):
        return (
            f"<BenchmarkResult {self.name}: {self.duration_ms:.2f}ms "
            f"(mad={self.mad_ms:.2f}, cv={self.cv:.2f}), "
            f"{self.memory_delta_mb:.2f}MB>"
        )

    def merge_runs(self, others):
        """Return a new result whose duration is the median across run medians."""
        run_medians = [self.duration_ms] + [o.duration_ms for o in others]
        run_mem = [self.memory_delta_mb] + [o.memory_delta_mb for o in others]
        all_samples = list(self.samples_ms)
        for o in others:
            all_samples.extend(o.samples_ms)
        return BenchmarkResult(
            self.name,
            median(run_medians),
            median(run_mem),
            samples_ms=all_samples,
            iterations=self.iterations,
        )


def benchmark(name=None, iterations=1, warmup=1):
    """Decorator to benchmark a function's execution time and memory delta.

    Each iteration is timed separately with perf_counter. The reported
    duration is the median of per-iteration samples (more stable than mean
    under CI noise). A short warmup pass is discarded.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            bench_name = name or func.__name__

            gc.collect()
            time.sleep(0.05)

            for _ in range(max(0, warmup)):
                func(*args, **kwargs)

            gc.collect()
            start_mem = get_memory_usage_mb()
            samples_ms = []
            result_val = None
            for _ in range(iterations):
                t0 = time.perf_counter()
                result_val = func(*args, **kwargs)
                t1 = time.perf_counter()
                samples_ms.append((t1 - t0) * 1000.0)

            gc.collect()
            end_mem = get_memory_usage_mb()

            duration = median(samples_ms)
            mem_delta = end_mem - start_mem
            mad = median_abs_deviation(samples_ms, center=duration)
            cv = coefficient_of_variation(samples_ms)

            print(f"BENCHMARK: {bench_name}")
            print(f"  Iterations: {iterations} (warmup={warmup})")
            print(f"  Median Duration: {duration:.3f} ms")
            print(f"  MAD: {mad:.3f} ms  CV: {cv:.3f}")
            if len(samples_ms) >= 2:
                print(
                    f"  Range: {min(samples_ms):.3f} .. {max(samples_ms):.3f} ms",
                )
            print(f"  Memory Delta: {mem_delta:.2f} MB")

            return result_val, BenchmarkResult(
                bench_name,
                duration,
                mem_delta,
                samples_ms=samples_ms,
                iterations=iterations,
            )

        return wrapper

    return decorator


def aggregate_run_results(runs):
    """Aggregate a list of result-lists (one per suite run) by benchmark name.

    Returns a list of BenchmarkResult with median-of-run-medians duration.
    """
    if not runs:
        return []
    by_name = {}
    order = []
    for run_results in runs:
        for result in run_results:
            if result.name not in by_name:
                by_name[result.name] = []
                order.append(result.name)
            by_name[result.name].append(result)

    aggregated = []
    for name in order:
        group = by_name[name]
        first, rest = group[0], group[1:]
        aggregated.append(first.merge_runs(rest) if rest else first)
    return aggregated


def adaptive_alert_ratio(baseline_ms):
    """Looser ratio thresholds for tiny baselines (CI scheduler noise)."""
    if baseline_ms < 1.0:
        return 4.0
    if baseline_ms < 5.0:
        return 2.5
    if baseline_ms < 20.0:
        return 2.0
    return 1.5


class MemoryTracker:
    """Context manager that records process RSS delta for memory profiling tests."""

    def __init__(self, name: str):
        self.name = name
        self.mem_start = 0.0
        self.mem_end = 0.0
        self.mem_delta = 0.0

    def __enter__(self):
        gc.collect()
        self.mem_start = get_memory_usage_mb()
        return self

    def __exit__(self, exc_type, exc, tb):
        gc.collect()
        self.mem_end = get_memory_usage_mb()
        self.mem_delta = self.mem_end - self.mem_start
        print(
            f"MEMORY: {self.name}: delta={self.mem_delta:.2f} MB "
            f"(start={self.mem_start:.2f}, end={self.mem_end:.2f})",
        )
        return False


def should_alert_regression(
    current_ms,
    previous_ms,
    *,
    noise_floor_ms=0.5,
    min_abs_delta_ms=1.5,
    fail_ratio=None,
    current_cv=None,
    previous_cv=None,
    max_cv_for_strict=0.35,
):
    """Decide whether a slower current value is a real regression.

    Returns (alert: bool, reason: str). Skips alerts when both values sit
    under the noise floor, when the absolute delta is tiny, or when the ratio
    is within an adaptive threshold. High CV on either side widens the bar.
    """
    if previous_ms <= 0:
        return False, "no previous baseline"

    abs_delta = current_ms - previous_ms
    if abs_delta <= 0:
        return False, "improved or unchanged"

    if current_ms < noise_floor_ms and previous_ms < noise_floor_ms:
        return False, f"both under noise floor ({noise_floor_ms} ms)"

    if abs_delta < min_abs_delta_ms:
        return (
            False,
            f"abs delta {abs_delta:.3f} ms < min {min_abs_delta_ms} ms",
        )

    ratio = current_ms / previous_ms
    threshold = adaptive_alert_ratio(previous_ms)
    if fail_ratio is not None:
        threshold = fail_ratio

    noisy = False
    if current_cv is not None and current_cv > max_cv_for_strict:
        noisy = True
    if previous_cv is not None and previous_cv > max_cv_for_strict:
        noisy = True
    if noisy:
        threshold = max(threshold, threshold * 1.25)

    if ratio < threshold:
        return (
            False,
            f"ratio {ratio:.2f}x within adaptive threshold {threshold:.2f}x",
        )

    return (
        True,
        f"{ratio:.2f}x slower (threshold {threshold:.2f}x), +{abs_delta:.3f} ms",
    )


def parse_extra_stats(extra):
    """Parse mad= / cv= / runs= fields from github-action-benchmark extra."""
    out = {}
    if not extra:
        return out
    for part in str(extra).replace(",", " ").split():
        if "=" not in part:
            continue
        key, _, raw = part.partition("=")
        try:
            out[key.strip().lower()] = float(raw)
        except ValueError:
            continue
    return out
