# SPDX-License-Identifier: 0BSD
"""Oracle: DatabaseProvider must not close a live thread's SQLite handle."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import threading

import pytest

from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.sqlite_errors import sqlite_error_is_retryable


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
        barrier.wait(timeout=10)
        for thread in threads:
            thread.join(timeout=5)
            assert not thread.is_alive()

        assert errors == []
        pruned = provider.prune_orphaned_connections()
        assert pruned >= 1
        # Main thread still owns the connection from CREATE TABLE / setup.
        assert provider.connection_count() <= 1


def test_live_thread_keeps_working_during_announce_burst():
    """Cap-eviction used to close the HTTP worker's handle mid-request."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "burst.db")
        provider = DatabaseProvider(db_path)
        provider.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")

        hold = threading.Event()
        started = threading.Barrier(41)
        errors: list[BaseException] = []

        def announce_worker(n: int):
            try:
                provider.execute("INSERT INTO t (val) VALUES (?)", (f"a{n}",))
                started.wait(timeout=10)
                hold.wait(timeout=10)
                provider.execute("SELECT COUNT(*) FROM t")
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=announce_worker, args=(i,)) for i in range(40)]
        for thread in threads:
            thread.start()
        started.wait(timeout=10)
        row = provider.fetchone("SELECT COUNT(*) AS n FROM t")
        assert row is not None
        assert int(row["n"]) >= 40
        hold.set()
        for thread in threads:
            thread.join(timeout=5)
        assert errors == []


def test_closed_handle_reopens_on_next_execute():
    """Another thread closing this handle must not stick HTTP on 500."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "reopen.db")
        provider = DatabaseProvider(db_path)
        provider.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")
        conn = provider.connection
        conn.close()
        provider.execute("INSERT INTO t (val) VALUES (?)", ("ok",))
        row = provider.fetchone("SELECT val FROM t")
        assert row["val"] == "ok"


def test_sqlite_closed_database_is_retryable():
    exc = sqlite3.ProgrammingError("Cannot operate on a closed database.")
    assert sqlite_error_is_retryable(exc) is True
    assert sqlite_error_is_retryable(RuntimeError("boom")) is False
