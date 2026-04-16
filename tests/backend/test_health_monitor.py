# SPDX-License-Identifier: 0BSD

import math
import time
import unittest
from unittest.mock import MagicMock, patch

from meshchatx.src.backend.persistent_log_handler import PersistentLogHandler
from meshchatx.src.backend.recovery.health_monitor import HealthMonitor


class TestPersistentLogEntropy(unittest.TestCase):
    """Tests for the log entropy and error rate properties."""

    def setUp(self):
        self.handler = PersistentLogHandler(capacity=5000, flush_interval=999)

    def test_entropy_zero_when_empty(self):
        self.assertEqual(self.handler.current_log_entropy, 0.0)

    def test_error_rate_zero_when_empty(self):
        self.assertEqual(self.handler.current_error_rate, 0.0)

    def test_entropy_zero_single_level(self):
        now = time.monotonic()
        with self.handler.lock:
            for _ in range(100):
                self.handler._level_events.append((now, "INFO"))
        self.assertAlmostEqual(self.handler.current_log_entropy, 0.0, places=5)

    def test_entropy_max_uniform_distribution(self):
        now = time.monotonic()
        with self.handler.lock:
            for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                for _ in range(20):
                    self.handler._level_events.append((now, level))
        expected = math.log2(5)
        self.assertAlmostEqual(self.handler.current_log_entropy, expected, places=3)

    def test_entropy_ignores_old_events(self):
        old = time.monotonic() - 120.0
        now = time.monotonic()
        with self.handler.lock:
            for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                for _ in range(20):
                    self.handler._level_events.append((old, level))
            for _ in range(50):
                self.handler._level_events.append((now, "ERROR"))
        self.assertAlmostEqual(self.handler.current_log_entropy, 0.0, places=5)

    def test_error_rate_all_errors(self):
        now = time.monotonic()
        with self.handler.lock:
            for _ in range(50):
                self.handler._level_events.append((now, "ERROR"))
                self.handler._error_events.append(now)
        self.assertAlmostEqual(self.handler.current_error_rate, 1.0)

    def test_error_rate_half(self):
        now = time.monotonic()
        with self.handler.lock:
            for _ in range(50):
                self.handler._level_events.append((now, "INFO"))
            for _ in range(50):
                self.handler._level_events.append((now, "ERROR"))
                self.handler._error_events.append(now)
        self.assertAlmostEqual(self.handler.current_error_rate, 0.5)


class TestHealthMonitorDetection(unittest.TestCase):
    """Tests for HealthMonitor detection logic (no real threads)."""

    def setUp(self):
        self.log_handler = MagicMock()
        self.log_handler.current_log_entropy = 0.5
        self.log_handler.current_error_rate = 0.0
        self.monitor = HealthMonitor(log_handler=self.log_handler, app=None)

    def test_no_warnings_normal_state(self):
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            mock_bc.assert_not_called()

    def test_entropy_climb_detected(self):
        self.monitor._entropy_history.extend([0.8, 1.2, 1.4])
        self.log_handler.current_log_entropy = 1.6
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            mock_bc.assert_called_once()
            args = mock_bc.call_args[0][0]
            self.assertEqual(args["kind"], "entropy_climbing")

    def test_entropy_not_climbing_when_below_threshold(self):
        self.monitor._entropy_history.extend([0.2, 0.4, 0.6])
        self.log_handler.current_log_entropy = 0.8
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            mock_bc.assert_not_called()

    def test_error_rate_high_warning(self):
        self.log_handler.current_error_rate = 0.5
        self.monitor._error_rate_history.append(0.4)
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            calls = [c[0][0] for c in mock_bc.call_args_list]
            error_warnings = [c for c in calls if c["kind"] == "error_rate_high"]
            self.assertEqual(len(error_warnings), 1)

    @patch("meshchatx.src.backend.recovery.health_monitor.psutil")
    def test_memory_low_warning(self, mock_psutil):
        mem_mock = MagicMock()
        mem_mock.available = 50 * 1024 * 1024  # 50 MB
        mock_psutil.virtual_memory.return_value = mem_mock
        self.monitor._mem_available_history.append(80.0)
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            calls = [c[0][0] for c in mock_bc.call_args_list]
            mem_warnings = [c for c in calls if c["kind"] == "memory_low"]
            self.assertEqual(len(mem_warnings), 1)

    def test_latest_snapshot_structure(self):
        self.monitor._check()
        snap = self.monitor.latest_snapshot
        self.assertIn("entropy", snap)
        self.assertIn("error_rate", snap)
        self.assertIn("memory_mb", snap)
        self.assertEqual(len(snap["entropy"]), 1)

    def test_entropy_climb_needs_three_readings(self):
        self.monitor._entropy_history.extend([1.2, 1.6])
        self.log_handler.current_log_entropy = 1.8
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            calls = [c[0][0] for c in mock_bc.call_args_list]
            entropy_warns = [c for c in calls if c["kind"] == "entropy_climbing"]
            self.assertEqual(len(entropy_warns), 1)

    def test_entropy_no_climb_when_decreasing(self):
        self.monitor._entropy_history.extend([2.0, 1.8, 1.6])
        self.log_handler.current_log_entropy = 1.4
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            calls = [c[0][0] for c in mock_bc.call_args_list]
            entropy_warns = [c for c in calls if c["kind"] == "entropy_climbing"]
            self.assertEqual(len(entropy_warns), 0)

    def test_stop_prevents_further_checks(self):
        self.monitor.stop()
        self.assertFalse(self.monitor._running)


class TestHealthMonitorEdgeCases(unittest.TestCase):
    def test_check_with_no_log_handler(self):
        monitor = HealthMonitor(log_handler=None, app=None)
        monitor._check()
        snap = monitor.latest_snapshot
        self.assertEqual(snap["entropy"], [0.0])

    def test_deque_fixed_size(self):
        monitor = HealthMonitor(log_handler=MagicMock(), app=None)
        monitor.log_handler.current_log_entropy = 1.0
        monitor.log_handler.current_error_rate = 0.0
        for _ in range(20):
            monitor._check()
        self.assertEqual(len(monitor._entropy_history), monitor.ENTROPY_WINDOW)


if __name__ == "__main__":
    unittest.main()
