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

    @patch("meshchatx.src.backend.recovery.health_monitor.psutil")
    def test_memory_single_dip_is_false_positive(self, mock_psutil):
        """One low reading alone must not warn (needs consecutive samples)."""
        mem_mock = MagicMock()
        mem_mock.available = 50 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mem_mock
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            calls = [c[0][0] for c in mock_bc.call_args_list]
            mem_warnings = [c for c in calls if c["kind"] == "memory_low"]
            self.assertEqual(len(mem_warnings), 0)

    @patch("meshchatx.src.backend.recovery.health_monitor.psutil")
    def test_memory_recovered_broadcast_after_pressure(self, mock_psutil):
        mem_mock = MagicMock()
        mem_mock.available = 500 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mem_mock
        self.monitor._memory_pressure_active = True
        self.monitor._mem_available_history.append(450.0)
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            calls = [c[0][0] for c in mock_bc.call_args_list]
            recovered = [c for c in calls if c["kind"] == "memory_recovered"]
            self.assertEqual(len(recovered), 1)
            self.assertFalse(self.monitor._memory_pressure_active)

    @patch("meshchatx.src.backend.recovery.health_monitor.psutil")
    def test_memory_still_low_does_not_broadcast_recovered(self, mock_psutil):
        mem_mock = MagicMock()
        mem_mock.available = 50 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mem_mock
        self.monitor._memory_pressure_active = True
        self.monitor._mem_available_history.append(80.0)
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            calls = [c[0][0] for c in mock_bc.call_args_list]
            recovered = [c for c in calls if c["kind"] == "memory_recovered"]
            self.assertEqual(len(recovered), 0)
            self.assertTrue(self.monitor._memory_pressure_active)

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


def test_loop_probe_dumps_stacks_on_stall(monkeypatch):
    """A frozen main loop triggers a one-shot stack dump + warning."""
    import faulthandler

    monitor = HealthMonitor(log_handler=None, app=None)

    class DeadLoop:
        def is_running(self):
            return True

        def call_soon_threadsafe(self, cb):
            pass  # never runs the callback: wedged loop

    from meshchatx.src.backend.async_utils import AsyncUtils

    monkeypatch.setattr(AsyncUtils, "main_loop", DeadLoop())
    monitor.LOOP_PROBE_INTERVAL_S = 0.05
    monitor.LOOP_STALL_S = 0.05
    monitor._running = True

    dumps = []
    monkeypatch.setattr(faulthandler, "dump_traceback", lambda: dumps.append(1))
    import time

    deadline = time.monotonic() + 5
    import threading

    t = threading.Thread(target=monitor._loop_probe_loop, daemon=True)
    t.start()
    while time.monotonic() < deadline and not dumps:
        time.sleep(0.05)
    monitor._running = False
    monitor._stop_event.set()
    t.join(timeout=3)
    assert dumps, "stalled loop should trigger a faulthandler dump"
    assert monitor._loop_stall_reported


def test_loop_probe_ignores_healthy_loop(monkeypatch):
    monitor = HealthMonitor(log_handler=None, app=None)

    import asyncio
    import threading

    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    try:
        from meshchatx.src.backend.async_utils import AsyncUtils

        monkeypatch.setattr(AsyncUtils, "main_loop", loop)
        monitor.LOOP_PROBE_INTERVAL_S = 0.05
        monitor.LOOP_STALL_S = 1.0
        monitor._running = True
        import faulthandler
        import time

        dumps = []
        monkeypatch.setattr(faulthandler, "dump_traceback", lambda: dumps.append(1))
        t = threading.Thread(target=monitor._loop_probe_loop, daemon=True)
        t.start()
        time.sleep(0.4)
        monitor._running = False
        monitor._stop_event.set()
        t.join(timeout=3)
        assert not dumps
    finally:
        loop.call_soon_threadsafe(loop.stop)


class TestHealthMonitorFdTracking(unittest.TestCase):
    """fd/handle accounting: absolute limit warning plus leak trend."""

    def setUp(self):
        self.log_handler = MagicMock()
        self.log_handler.current_log_entropy = 0.5
        self.log_handler.current_error_rate = 0.0
        self.monitor = HealthMonitor(log_handler=self.log_handler, app=None)

    def _mock_process(self, fd_count):
        proc = MagicMock()
        proc.num_fds.return_value = fd_count
        del proc.num_handles  # force the num_fds branch
        return proc

    @patch("meshchatx.src.backend.recovery.health_monitor.resource")
    def test_fd_pressure_when_near_limit(self, mock_resource):
        mock_resource.getrlimit.return_value = (1024, 4096)
        mock_resource.RLIMIT_NOFILE = 7
        self.monitor._process = self._mock_process(900)  # 88% of 1024
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            kinds = [c[0][0]["kind"] for c in mock_bc.call_args_list]
            assert "fd_pressure" in kinds

    @patch("meshchatx.src.backend.recovery.health_monitor.resource")
    def test_fd_growth_trend_detected(self, mock_resource):
        mock_resource.getrlimit.return_value = (1048576, 1048576)
        mock_resource.RLIMIT_NOFILE = 7
        self.monitor._process = MagicMock()
        # Fill the window with a near-monotonic climb: 200 -> 460.
        self.monitor._fd_history.extend([200, 240, 280, 310, 370, 430])
        self.monitor._process.num_fds.return_value = 460
        del self.monitor._process.num_handles
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            kinds = [c[0][0]["kind"] for c in mock_bc.call_args_list]
            assert "fd_growth" in kinds

    @patch("meshchatx.src.backend.recovery.health_monitor.resource")
    def test_fd_no_warning_on_stable_count(self, mock_resource):
        mock_resource.getrlimit.return_value = (1048576, 1048576)
        mock_resource.RLIMIT_NOFILE = 7
        self.monitor._process = MagicMock()
        self.monitor._fd_history.extend([300, 310, 295, 305, 300, 305])
        self.monitor._process.num_fds.return_value = 305
        del self.monitor._process.num_handles
        with patch.object(self.monitor, "_broadcast") as mock_bc:
            self.monitor._check()
            kinds = [c[0][0]["kind"] for c in mock_bc.call_args_list]
            assert "fd_growth" not in kinds
            assert "fd_pressure" not in kinds

    def test_fd_handles_missing_gracefully(self):
        proc = MagicMock()
        del proc.num_fds
        del proc.num_handles
        self.monitor._process = proc
        assert self.monitor._read_fd_stats() == (None, None)
