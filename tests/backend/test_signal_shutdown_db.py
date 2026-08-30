# SPDX-License-Identifier: 0BSD

"""Tests for Ctrl+C-safe SQLite shutdown."""

from __future__ import annotations

import signal
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from aiohttp.web_runner import GracefulExit

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.lifecycle import signal_shutdown as ss


@pytest.fixture(autouse=True)
def _reset_signal_shutdown_state():
    ss.reset_shutdown_state_for_tests()
    DatabaseProvider._instance = None
    yield
    ss.reset_shutdown_state_for_tests()
    if DatabaseProvider._instance is not None:
        DatabaseProvider._instance.close_all()
        DatabaseProvider._instance = None


def test_durable_shutdown_checkpoints_wal_and_leaves_healthy_db(tmp_path: Path):
    db_path = tmp_path / "database.db"
    db = Database(str(db_path))
    db.initialize()
    db.execute_sql("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
    db.execute_sql("INSERT INTO t (v) VALUES (?)", ("hello",))
    db.provider.commit()

    db.durable_shutdown()

    assert db_path.is_file()
    wal = Path(f"{db_path}-wal")
    # Truncate checkpoint should clear or empty the WAL when quiet.
    if wal.exists():
        assert wal.stat().st_size == 0

    conn = sqlite3.connect(str(db_path))
    try:
        assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT v FROM t").fetchone()[0] == "hello"
    finally:
        conn.close()


def test_signal_handler_flushes_registered_app_then_raises_graceful_exit(
    tmp_path: Path,
):
    db_path = tmp_path / "database.db"
    db = Database(str(db_path))
    db.initialize()
    db.execute_sql("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
    db.execute_sql("INSERT INTO t (v) VALUES (?)", ("sigint",))
    db.provider.commit()

    ctx = MagicMock()
    ctx.database = db
    app = MagicMock()
    app.contexts = {"abc": ctx}
    app.current_context = ctx
    ss.register_shutdown_app(app)

    with pytest.raises(GracefulExit):
        ss.meshchat_signal_handler(signal.SIGINT, None)

    conn = sqlite3.connect(str(db_path))
    try:
        assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT v FROM t").fetchone()[0] == "sigint"
    finally:
        conn.close()


def test_install_meshchat_signal_handlers_registers_sigint_sigterm():
    seen = {}

    def fake_signal(signum, handler):
        seen[signum] = handler

    assert (
        ss.install_meshchat_signal_handlers(force=True, signal_fn=fake_signal) is True
    )
    assert seen[signal.SIGINT] is ss.meshchat_signal_handler
    assert seen[signal.SIGTERM] is ss.meshchat_signal_handler


def test_durable_flush_all_databases_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "database.db"
    db = Database(str(db_path))
    db.initialize()
    ctx = MagicMock()
    ctx.database = db
    app = MagicMock()
    app.contexts = {"abc": ctx}
    app.current_context = ctx

    assert ss.durable_flush_all_databases(app) == 1
    # Second flush after close should not raise.
    assert ss.durable_flush_all_databases(app) >= 0
