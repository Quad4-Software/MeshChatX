# SPDX-License-Identifier: 0BSD

import json
import os
import tempfile
import unittest

from tests.backend.benchmarking_utils import (
    BenchmarkResult,
    adaptive_alert_ratio,
    aggregate_run_results,
    coefficient_of_variation,
    median,
    median_abs_deviation,
    parse_extra_stats,
    should_alert_regression,
)
from tests.backend.compare_benchmarks import (
    compare,
    main as compare_main,
    update_baseline,
)


class TestBenchmarkStats(unittest.TestCase):
    def test_median_odd_even(self):
        self.assertEqual(median([3, 1, 2]), 2)
        self.assertEqual(median([4, 1, 3, 2]), 2.5)

    def test_mad_and_cv(self):
        samples = [10.0, 10.0, 10.0, 12.0, 8.0]
        self.assertEqual(median_abs_deviation(samples), 0.0)
        self.assertGreater(coefficient_of_variation(samples), 0.0)
        self.assertEqual(coefficient_of_variation([5.0]), 0.0)

    def test_aggregate_run_results_median_of_medians(self):
        r1 = BenchmarkResult("A", 10.0, 0.1, samples_ms=[9, 10, 11])
        r2 = BenchmarkResult("A", 20.0, 0.2, samples_ms=[19, 20, 21])
        r3 = BenchmarkResult("A", 12.0, 0.15, samples_ms=[11, 12, 13])
        b1 = BenchmarkResult("B", 1.0, 0.0, samples_ms=[1.0])
        b2 = BenchmarkResult("B", 3.0, 0.0, samples_ms=[3.0])
        b3 = BenchmarkResult("B", 2.0, 0.0, samples_ms=[2.0])
        out = aggregate_run_results([[r1, b1], [r2, b2], [r3, b3]])
        by_name = {r.name: r for r in out}
        self.assertEqual(by_name["A"].duration_ms, 12.0)
        self.assertEqual(by_name["B"].duration_ms, 2.0)
        self.assertEqual(len(by_name["A"].samples_ms), 9)

    def test_adaptive_alert_ratio_widens_for_tiny_baselines(self):
        self.assertEqual(adaptive_alert_ratio(0.2), 4.0)
        self.assertEqual(adaptive_alert_ratio(2.0), 2.5)
        self.assertEqual(adaptive_alert_ratio(10.0), 2.0)
        self.assertEqual(adaptive_alert_ratio(50.0), 1.5)

    def test_should_alert_skips_noise_floor(self):
        alert, reason = should_alert_regression(0.4, 0.15)
        self.assertFalse(alert)
        self.assertIn("noise floor", reason)

    def test_should_alert_skips_tiny_abs_delta(self):
        # 3x ratio but only +0.4 ms absolute — not actionable
        alert, reason = should_alert_regression(0.6, 0.2, noise_floor_ms=0.1)
        self.assertFalse(alert)
        self.assertIn("abs delta", reason)

    def test_should_alert_real_regression(self):
        # Large baseline, clear absolute and ratio regression
        alert, reason = should_alert_regression(40.0, 10.0)
        self.assertTrue(alert)
        self.assertIn("slower", reason)

    def test_should_alert_within_adaptive_threshold(self):
        # 1.8x on a 10 ms baseline — adaptive threshold is 2.0x
        alert, reason = should_alert_regression(18.0, 10.0)
        self.assertFalse(alert)
        self.assertIn("within adaptive", reason)

    def test_should_alert_widens_when_cv_high(self):
        # Would alert at 2.1x on 10 ms baseline (threshold 2.0), but high CV
        # bumps threshold to 2.5 so this stays quiet.
        alert, _ = should_alert_regression(
            21.0,
            10.0,
            current_cv=0.5,
            previous_cv=0.1,
        )
        self.assertFalse(alert)

    def test_parse_extra_stats(self):
        stats = parse_extra_stats("mad=0.012 cv=0.150 runs=3 mem_delta_mb=0.10")
        self.assertAlmostEqual(stats["mad"], 0.012)
        self.assertAlmostEqual(stats["cv"], 0.15)
        self.assertAlmostEqual(stats["runs"], 3.0)


class TestCompareBenchmarks(unittest.TestCase):
    def _write(self, path, entries):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f)

    def test_compare_flags_real_regression_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            current = os.path.join(tmp, "current.json")
            previous = os.path.join(tmp, "previous.json")
            self._write(
                current,
                [
                    {
                        "name": "Tiny Noise",
                        "unit": "ms",
                        "value": 0.4,
                        "extra": "cv=0.1",
                    },
                    {
                        "name": "Real Slowdown",
                        "unit": "ms",
                        "value": 40.0,
                        "extra": "cv=0.05",
                    },
                    {
                        "name": "Ratio Noise",
                        "unit": "ms",
                        "value": 0.455,
                        "extra": "cv=0.2",
                    },
                ],
            )
            self._write(
                previous,
                [
                    {
                        "name": "Tiny Noise",
                        "unit": "ms",
                        "value": 0.15,
                        "extra": "cv=0.1",
                    },
                    {
                        "name": "Real Slowdown",
                        "unit": "ms",
                        "value": 10.0,
                        "extra": "cv=0.05",
                    },
                    {
                        "name": "Ratio Noise",
                        "unit": "ms",
                        "value": 0.177,
                        "extra": "cv=0.2",
                    },
                ],
            )
            code, rows = compare(
                current,
                previous,
                noise_floor_ms=0.5,
                min_abs_delta_ms=1.5,
            )
            by_name = {r["name"]: r for r in rows}
            self.assertEqual(code, 1)
            self.assertEqual(by_name["Real Slowdown"]["status"], "REGRESSION")
            self.assertEqual(by_name["Tiny Noise"]["status"], "noise")
            self.assertEqual(by_name["Ratio Noise"]["status"], "noise")

    def test_compare_trim_announce_style_false_positive(self):
        """The exact CI false-positive pattern: 0.177 -> 0.455 (2.57x)."""
        with tempfile.TemporaryDirectory() as tmp:
            current = os.path.join(tmp, "current.json")
            previous = os.path.join(tmp, "previous.json")
            self._write(
                current,
                [
                    {
                        "name": "Trim Announces for Aspect",
                        "unit": "ms",
                        "value": 0.455,
                        "extra": "mad=0.05 cv=0.3 runs=1",
                    }
                ],
            )
            self._write(
                previous,
                [
                    {
                        "name": "Trim Announces for Aspect",
                        "unit": "ms",
                        "value": 0.177,
                        "extra": "mad=0.02 cv=0.2 runs=1",
                    }
                ],
            )
            code, rows = compare(current, previous)
            self.assertEqual(code, 0)
            self.assertEqual(rows[0]["status"], "noise")

    def test_update_baseline_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            current = os.path.join(tmp, "current.json")
            baseline = os.path.join(tmp, "cache", "benchmark-data.json")
            self._write(
                current,
                [{"name": "Config Get (50 keys)", "unit": "ms", "value": 0.4}],
            )
            update_baseline(current, baseline)
            self.assertTrue(os.path.isfile(baseline))
            code, rows = compare(current, baseline)
            self.assertEqual(code, 0)
            self.assertEqual(rows[0]["status"], "ok")

    def test_cli_exits_nonzero_on_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            current = os.path.join(tmp, "current.json")
            previous = os.path.join(tmp, "previous.json")
            self._write(
                current,
                [{"name": "Create Identity", "unit": "ms", "value": 200.0}],
            )
            self._write(
                previous,
                [{"name": "Create Identity", "unit": "ms", "value": 80.0}],
            )
            code = compare_main(
                [
                    "--current",
                    current,
                    "--previous",
                    previous,
                    "--noise-floor-ms",
                    "0.5",
                    "--min-abs-delta-ms",
                    "1.5",
                ]
            )
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
