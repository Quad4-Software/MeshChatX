# SPDX-License-Identifier: 0BSD
"""Oracle: DatabaseProvider must not retain one SQLite FD set per dead thread."""

from __future__ import annotations

import os
import tempfile
import threading

import pytest

from meshchatx.src.backend.database.provider import DatabaseProvider, _MAX_CONNECTIONS


@pytest.fixture(autouse=True)
def reset_provider():
    DatabaseProvider._instance = None
    yield
    if DatabaseProvider._instance is not None:
        DatabaseProvider._instance.close_all()
    DatabaseProvider._instance = None


def test_announce_style_threads_do_not_accumulate_connections():
    """RNS starts a Thread per announce callback that touches the DB.

    After those threads exit, orphaned connections must be pruned so WAL FDs
    cannot grow without bound (Docker Errno 24).
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "announces.db")
        provider = DatabaseProvider(db_path)
        provider.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")

        barrier = threading.Barrier(33)
        errors: list[BaseException] = []

        def worker(n: int):
            try:
                provider.execute("INSERT INTO t (val) VALUES (?)", (f"w{n}",))
                barrier.wait(timeout=10)
                barrier.wait(timeout=10)
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(32)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=10)
        # While all workers are alive, connection count is capped.
        assert provider.connection_count() <= _MAX_CONNECTIONS
        barrier.wait(timeout=10)
        for thread in threads:
            thread.join(timeout=5)
            assert not thread.is_alive()

        assert errors == []
        pruned = provider.prune_orphaned_connections()
        assert pruned >= 1
        # Main thread still owns the connection from CREATE TABLE / setup.
        assert provider.connection_count() <= 1


def test_connection_cap_evicts_when_threads_still_alive():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "cap.db")
        provider = DatabaseProvider(db_path)
        provider.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")

        hold = threading.Event()
        started = threading.Barrier(_MAX_CONNECTIONS + 2)

        def worker():
            provider.execute("INSERT INTO t DEFAULT VALUES")
            started.wait(timeout=10)
            hold.wait(timeout=10)

        threads = [threading.Thread(target=worker) for _ in range(_MAX_CONNECTIONS + 1)]
        for thread in threads:
            thread.start()
        started.wait(timeout=10)
        assert provider.connection_count() <= _MAX_CONNECTIONS
        hold.set()
        for thread in threads:
            thread.join(timeout=5)
        provider.prune_orphaned_connections()
        assert provider.connection_count() <= 1
