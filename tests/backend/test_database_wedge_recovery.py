# SPDX-License-Identifier: 0BSD
"""Database wedge recovery tests.

Sustained retryable failures on fresh connections must reset the
connection generation once, then escalate to on_unrecoverable.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import time

import pytest

from meshchatx.src.backend.database.provider import DatabaseProvider


@pytest.fixture
def provider():
    providers = []

    def make(db_path=None):
        if db_path is None:
            tmp = tempfile.mkdtemp()
            db_path = os.path.join(tmp, "wedge.db")
        p = DatabaseProvider(db_path)
        providers.append(p)
        return p

    yield make
    for p in providers:
        p._wedge_suppressed = True
        try:
            p.close_all()
        except Exception:
            pass


def _boom():
    raise sqlite3.OperationalError("disk I/O error")


def _fail(p: DatabaseProvider):
    with pytest.raises(sqlite3.OperationalError):
        p._call_with_reconnect(_boom)


def test_single_failures_do_not_reset(provider):
    p = provider()
    p.execute("CREATE TABLE t (a INTEGER)")
    gen = p._close_generation
    for _ in range(3):
        _fail(p)
    assert p._close_generation == gen
    assert p._persistent_failures == 3


def test_sustained_failures_force_connection_reset(provider):
    p = provider()
    p.execute("CREATE TABLE t (a INTEGER)")
    gen = p._close_generation
    for _ in range(4):
        _fail(p)
    assert p._close_generation == gen  # inside the detect window
    # Pretend the failures have been going on past the detect window.
    with p._lock:
        p._persistent_failure_started = time.monotonic() - 16
    _fail(p)
    assert p._close_generation == gen + 1
    assert p._connection_meta == {}
    # Reaper must survive a wedge reset.
    assert p._reaper_thread is not None and p._reaper_thread.is_alive()


def test_success_clears_failure_state(provider):
    p = provider()
    p.execute("CREATE TABLE t (a INTEGER)")
    _fail(p)
    _fail(p)
    assert p._persistent_failure_started is not None
    p.execute("SELECT 1")
    assert p._persistent_failure_started is None
    assert p._persistent_failures == 0


def test_escalates_once_after_reset_still_failing(provider):
    p = provider()
    p.execute("CREATE TABLE t (a INTEGER)")
    calls = []
    p.on_unrecoverable = lambda: calls.append(1)
    # A reset already ran 31s ago and fresh connections still fail.
    p._wedge_reset_at = time.monotonic() - 31
    with p._lock:
        p._persistent_failure_started = time.monotonic() - 20
        p._persistent_failures = 4
    _fail(p)
    assert calls == [1]
    _fail(p)
    assert calls == [1]


def test_close_all_suppresses_wedge_recovery(provider):
    p = provider()
    p.execute("CREATE TABLE t (a INTEGER)")
    calls = []
    p.on_unrecoverable = lambda: calls.append(1)
    p.close_all()
    with p._lock:
        p._persistent_failure_started = time.monotonic() - 120
        p._persistent_failures = 99
    p._wedge_reset_at = time.monotonic() - 120
    _fail(p)
    assert calls == []
    assert p._connection_meta == {}


def test_memory_db_skips_wedge_detection(provider):
    p = provider(":memory:")
    _fail(p)
    for _ in range(10):
        _fail(p)
    assert p._persistent_failure_started is None


def test_real_connection_recovers_after_wal_unlink(provider):
    """Deleting wal/shm under a live connection must not wedge writes."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "real.db")
        p = DatabaseProvider(db_path)
        p.execute("CREATE TABLE t (a INTEGER)")
        p.execute("INSERT INTO t VALUES (1)")
        for suffix in ("-wal", "-shm"):
            path = db_path + suffix
            if os.path.exists(path):
                os.unlink(path)
        # Force enough failures for detection, then simulate the reset that
        # the detector performs.
        p._force_connection_reset()
        p.execute("INSERT INTO t VALUES (2)")
        rows = p.fetchall("SELECT a FROM t ORDER BY a")
        assert [r["a"] for r in rows] == [1, 2]
        p.close_all()
