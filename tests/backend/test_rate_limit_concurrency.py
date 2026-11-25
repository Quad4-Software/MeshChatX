# SPDX-License-Identifier: 0BSD
"""Threaded race test for the path-request rate limiter."""

import threading
import time

import pytest

from meshchatx.src.backend import reticulum_pathfinding as pf


@pytest.fixture(autouse=True)
def _reset():
    pf.reset_path_request_rate_limit_for_tests()
    yield
    pf.reset_path_request_rate_limit_for_tests()


class TestPathRequestRateLimitConcurrency:
    def test_n_threads_one_destination_exactly_one_request(self, monkeypatch):
        calls = []
        lock = threading.Lock()

        def fake_request_path(dest):
            with lock:
                calls.append(dest)
            # Give the other threads a real chance to race the window check.
            time.sleep(0.001)

        monkeypatch.setattr(
            "meshchatx.src.backend.reticulum_pathfinding.RNS.Transport.request_path",
            fake_request_path,
        )
        dest = b"\xaa" * 16
        threads = [
            threading.Thread(target=pf._request_path_once_per_window, args=(dest,))
            for _ in range(16)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert calls == [dest], f"expected 1 request_path, got {len(calls)}"

    def test_n_threads_distinct_destinations_each_gets_one(self, monkeypatch):
        monkeypatch.setattr(pf, "_PATH_REQUEST_GLOBAL_BURST", 32.0)
        pf.reset_path_request_rate_limit_for_tests()
        calls = []
        lock = threading.Lock()

        def fake_request_path(dest):
            with lock:
                calls.append(dest)

        monkeypatch.setattr(
            "meshchatx.src.backend.reticulum_pathfinding.RNS.Transport.request_path",
            fake_request_path,
        )
        dests = [bytes([i]) * 16 for i in range(16)]
        threads = [
            threading.Thread(target=pf._request_path_once_per_window, args=(d,))
            for d in dests
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert sorted(calls) == sorted(dests)

    def test_failed_request_does_not_consume_window(self, monkeypatch):
        def bad_request_path(dest):
            raise RuntimeError("transport down")

        monkeypatch.setattr(
            "meshchatx.src.backend.reticulum_pathfinding.RNS.Transport.request_path",
            bad_request_path,
        )
        dest = b"\xbb" * 16
        with pytest.raises(RuntimeError):
            pf._request_path_once_per_window(dest)
        assert dest not in pf._last_path_request_at

    def test_window_cap_evicts_oldest_entry_not_whole_table(self, monkeypatch):
        monkeypatch.setattr(pf, "_PATH_REQUEST_GLOBAL_BURST", 1000.0)
        pf.reset_path_request_rate_limit_for_tests()
        monkeypatch.setattr(
            "meshchatx.src.backend.reticulum_pathfinding.RNS.Transport.request_path",
            lambda d: None,
        )

        def dest(i):
            return bytes([i % 256, i // 256]) + b"\x00" * 14

        first = dest(0)
        newest = dest(pf._PATH_REQUEST_RATE_LIMIT_MAX_ENTRIES)
        for i in range(pf._PATH_REQUEST_RATE_LIMIT_MAX_ENTRIES):
            assert pf._request_path_once_per_window(dest(i)) is True
        assert first in pf._last_path_request_at

        assert pf._request_path_once_per_window(newest) is True
        assert len(pf._last_path_request_at) == pf._PATH_REQUEST_RATE_LIMIT_MAX_ENTRIES
        assert first not in pf._last_path_request_at
        assert dest(1) in pf._last_path_request_at
        assert newest in pf._last_path_request_at

    def test_global_token_bucket_limits_distinct_destinations(self, monkeypatch):
        monkeypatch.setattr(
            "meshchatx.src.backend.reticulum_pathfinding.RNS.Transport.request_path",
            lambda d: None,
        )
        results = [
            pf._request_path_once_per_window(bytes([i]) * 16)
            for i in range(int(pf._PATH_REQUEST_GLOBAL_BURST) + 2)
        ]
        assert results.count(True) == int(pf._PATH_REQUEST_GLOBAL_BURST)
        assert results.count(False) == 2

    def test_global_token_bucket_refills(self, monkeypatch):
        monkeypatch.setattr(
            "meshchatx.src.backend.reticulum_pathfinding.RNS.Transport.request_path",
            lambda d: None,
        )
        for i in range(int(pf._PATH_REQUEST_GLOBAL_BURST)):
            assert pf._request_path_once_per_window(bytes([i]) * 16) is True
        assert pf._request_path_once_per_window(b"\xff" * 16) is False

        # Simulate one full refill window without sleeping.
        pf._path_request_global_tokens_at -= pf._PATH_REQUEST_GLOBAL_WINDOW_SECONDS
        assert pf._request_path_once_per_window(b"\xff" * 16) is True
