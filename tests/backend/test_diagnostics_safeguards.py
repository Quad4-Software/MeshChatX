# SPDX-License-Identifier: 0BSD

import logging
import sys
import threading
import unittest
from unittest.mock import MagicMock

from meshchatx.src.backend.diagnostics import MemoryDiagnostics
from meshchatx.src.backend.persistent_log_handler import PersistentLogHandler
from meshchatx.src.backend.recovery.crash_recovery import CrashRecovery
from meshchatx.src.backend.recovery.health_monitor import HealthMonitor


class TestMemoryDiagnosticsBounding(unittest.TestCase):
    """The leak detector must not itself leak by retaining every snapshot."""

    def test_snapshots_are_bounded_and_baseline_preserved(self):
        diag = MemoryDiagnostics(max_snapshots=4)
        diag.start()
        try:
            baseline = diag._snapshots[0]
            for _ in range(30):
                diag.snapshot()
            self.assertLessEqual(len(diag._snapshots), 4)
            self.assertLessEqual(len(diag._gc_stats), 4)
            self.assertIs(diag._snapshots[0], baseline)
        finally:
            diag.stop()

    def test_total_snapshots_is_monotonic(self):
        diag = MemoryDiagnostics(max_snapshots=4)
        diag.start()
        try:
            for _ in range(10):
                diag.snapshot()
            self.assertEqual(diag.total_snapshots, 11)
        finally:
            diag.stop()

    def test_type_tracker_history_is_bounded(self):
        diag = MemoryDiagnostics(max_snapshots=4)
        diag.start()
        try:
            for _ in range(20):
                diag.snapshot()
            self.assertLessEqual(len(diag._type_tracker._history), 4)
            self.assertTrue(diag._type_tracker._first)
        finally:
            diag.stop()

    def test_reset_clears_history_and_counter(self):
        diag = MemoryDiagnostics(max_snapshots=4)
        diag.start()
        diag.snapshot()
        diag.reset()
        self.assertEqual(diag.total_snapshots, 0)
        self.assertEqual(len(diag._snapshots), 0)
        self.assertEqual(len(diag._gc_stats), 0)


class TestPersistentLogFilterParity(unittest.TestCase):
    """In-memory fallback must apply the same filters as the database path."""

    def setUp(self):
        self.handler = PersistentLogHandler(flush_interval=999)
        self.handler.logs_buffer.extend(
            [
                {
                    "timestamp": 1.0,
                    "level": "INFO",
                    "module": "alpha",
                    "message": "hello world",
                    "is_anomaly": 0,
                    "anomaly_type": None,
                },
                {
                    "timestamp": 2.0,
                    "level": "ERROR",
                    "module": "beta",
                    "message": "boom",
                    "is_anomaly": 1,
                    "anomaly_type": "repeat",
                },
            ],
        )

    def test_module_filter_applied_in_fallback(self):
        logs = self.handler.get_logs(module="alpha")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["module"], "alpha")

    def test_total_count_respects_filters(self):
        self.assertEqual(self.handler.get_total_count(level="ERROR"), 1)
        self.assertEqual(self.handler.get_total_count(is_anomaly=True), 1)
        self.assertEqual(self.handler.get_total_count(), 2)

    def test_emit_survives_anomaly_detector_failure(self):
        self.handler._detect_anomaly = MagicMock(side_effect=RuntimeError("boom"))
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="resilient",
            args=(),
            exc_info=None,
        )
        self.handler.emit(record)
        self.assertEqual(len(self.handler.logs_buffer), 3)
        self.assertEqual(self.handler.logs_buffer[-1]["message"], "resilient")


class TestCrashRecoveryThreadHook(unittest.TestCase):
    def setUp(self):
        self.recovery = CrashRecovery()
        self._orig_sys = sys.excepthook
        self._orig_thread = threading.excepthook

    def tearDown(self):
        sys.excepthook = self._orig_sys
        threading.excepthook = self._orig_thread

    def test_install_sets_threading_hook(self):
        self.recovery.install()
        self.assertEqual(threading.excepthook, self.recovery._handle_thread_exception)

    def test_disable_restores_threading_hook(self):
        original = threading.excepthook
        self.recovery.install()
        self.recovery.disable()
        self.assertEqual(threading.excepthook, original)

    def test_thread_exception_does_not_exit_process(self):
        orig_exit = sys.exit
        sys.exit = MagicMock()
        try:
            args = MagicMock()
            args.exc_type = ValueError
            args.exc_value = ValueError("worker died")
            args.exc_traceback = None
            args.thread = MagicMock(name="worker")
            self.recovery._handle_thread_exception(args)
            sys.exit.assert_not_called()
        finally:
            sys.exit = orig_exit

    def test_reentrancy_guard_prevents_recursion(self):
        calls = {"default": 0}

        def fake_default(et, ev, tb):
            calls["default"] += 1

        orig_default = sys.__excepthook__
        sys.__excepthook__ = fake_default
        try:
            self.recovery._handling = True
            self.recovery.handle_exception(
                ValueError,
                ValueError("x"),
                None,
                exit_process=False,
            )
            self.assertEqual(calls["default"], 1)
        finally:
            sys.__excepthook__ = orig_default
            self.recovery._handling = False


class TestHealthMonitorStop(unittest.TestCase):
    def test_stop_signals_and_joins(self):
        monitor = HealthMonitor(log_handler=MagicMock(), app=None)
        monitor.log_handler.current_log_entropy = 0.1
        monitor.log_handler.current_error_rate = 0.0
        monitor.CHECK_INTERVAL = 0.05
        monitor.start()
        self.assertTrue(monitor._running)
        monitor.stop(timeout=2.0)
        self.assertFalse(monitor._running)
        self.assertTrue(monitor._stop_event.is_set())
        if monitor._thread is not None:
            self.assertFalse(monitor._thread.is_alive())


if __name__ == "__main__":
    unittest.main()
