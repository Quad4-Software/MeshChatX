"""Lightweight predictive health monitor.

Runs as a daemon thread on a 5-minute interval, reading in-memory
metrics (log entropy, error rate, memory) and emitting WebSocket
warnings when anomalous trends are detected.

No database queries are made in the monitor loop — all reads come
from in-memory deques kept by PersistentLogHandler and psutil.
"""

import asyncio
import collections
import json
import logging
import threading

import psutil

_log = logging.getLogger("meshchatx.health_monitor")


class HealthMonitor:
    CHECK_INTERVAL = 300  # 5 minutes
    ENTROPY_WINDOW = 6  # readings kept (~30 min at default interval)
    ENTROPY_WARN_THRESHOLD = 1.5  # out of max ~2.32 for 5 log levels
    ERROR_RATE_WARN = 0.3
    MEMORY_WARN_MB = 100  # warn when available < 100 MB
    CONSECUTIVE_NEEDED = 2  # consecutive bad readings before alert

    def __init__(self, log_handler, app=None):
        self.log_handler = log_handler
        self.app = app
        self._running = False
        self._thread = None

        self._entropy_history = collections.deque(maxlen=self.ENTROPY_WINDOW)
        self._error_rate_history = collections.deque(maxlen=self.ENTROPY_WINDOW)
        self._mem_available_history = collections.deque(maxlen=self.ENTROPY_WINDOW)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        _log.info("HealthMonitor started (interval=%ds)", self.CHECK_INTERVAL)

    def stop(self):
        self._running = False

    def _run_loop(self):
        asyncio.run(self._async_loop())

    async def _async_loop(self):
        while self._running:
            try:
                self._check()
            except Exception as exc:
                _log.debug("HealthMonitor check error: %s", exc)
            await asyncio.sleep(self.CHECK_INTERVAL)

    def _check(self):
        entropy = 0.0
        error_rate = 0.0
        if self.log_handler:
            entropy = self.log_handler.current_log_entropy
            error_rate = self.log_handler.current_error_rate

        mem = psutil.virtual_memory()
        available_mb = mem.available / (1024 * 1024)

        self._entropy_history.append(entropy)
        self._error_rate_history.append(error_rate)
        self._mem_available_history.append(available_mb)

        warnings = []

        if self._detect_entropy_climb():
            warnings.append(
                {
                    "kind": "entropy_climbing",
                    "message": f"Log entropy rising: {entropy:.2f} bits (threshold {self.ENTROPY_WARN_THRESHOLD})",
                    "value": round(entropy, 4),
                }
            )

        if self._consecutive_above(self._error_rate_history, self.ERROR_RATE_WARN):
            warnings.append(
                {
                    "kind": "error_rate_high",
                    "message": f"Error rate elevated: {error_rate:.0%}",
                    "value": round(error_rate, 4),
                }
            )

        if self._consecutive_below(self._mem_available_history, self.MEMORY_WARN_MB):
            warnings.append(
                {
                    "kind": "memory_low",
                    "message": f"Available memory low: {available_mb:.0f} MB",
                    "value": round(available_mb, 1),
                }
            )

        for w in warnings:
            _log.warning("Health warning: %s", w["message"])
            self._broadcast(w)

    def _detect_entropy_climb(self):
        """True if 3+ consecutive entropy readings are strictly increasing
        AND the latest exceeds the warning threshold."""
        h = self._entropy_history
        if len(h) < 3:
            return False
        vals = list(h)
        last_three = vals[-3:]
        if last_three[-1] <= self.ENTROPY_WARN_THRESHOLD:
            return False
        return last_three[0] < last_three[1] < last_three[2]

    @staticmethod
    def _consecutive_above(deq, threshold):
        if len(deq) < 2:
            return False
        vals = list(deq)
        return vals[-1] > threshold and vals[-2] > threshold

    @staticmethod
    def _consecutive_below(deq, threshold):
        if len(deq) < 2:
            return False
        vals = list(deq)
        return vals[-1] < threshold and vals[-2] < threshold

    def _broadcast(self, warning_data):
        if not self.app:
            return
        try:
            from meshchatx.src.backend.async_utils import AsyncUtils

            AsyncUtils.run_async(
                self.app.websocket_broadcast(
                    json.dumps({"type": "health_warning", "data": warning_data})
                )
            )
        except Exception:
            pass

    @property
    def latest_snapshot(self):
        """Return latest metrics as a dict (useful for diagnostics/tests)."""
        return {
            "entropy": list(self._entropy_history),
            "error_rate": list(self._error_rate_history),
            "memory_mb": list(self._mem_available_history),
        }
