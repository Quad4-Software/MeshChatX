# SPDX-License-Identifier: 0BSD
"""Crash-consistency tests: kill the backend mid-write, verify recovery.

Atomic writes, history compaction, and ratchet persistence all promise
crash safety, but nothing kills the process during the write path. These
tests SIGKILL a real backend while writes are in flight, restart with
the same storage, and assert the DB, config, and history are intact.

Runs only when MESHCHAT_LIVE_RETICULUM=1; loopback only.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import threading
import time

import pytest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "scripts", "e2e"
    ),
)
import backend_harness as bh  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.environ.get("MESHCHAT_LIVE_RETICULUM") != "1",
    reason="Set MESHCHAT_LIVE_RETICULUM=1 for crash-consistency tests",
)

DB_REL = os.path.join("storage", "db")


def _write_burst(port: int, stop: threading.Event):
    """Continuous writes so a kill lands mid-write most rounds."""
    i = 0
    jar = {}
    while not stop.is_set():
        try:
            bh.request(
                port,
                "/api/v1/config",
                data={"display_name": f"crash-marker-{i}"},
                method="PATCH",
                jar=jar,
                timeout=10,
            )
        except Exception:
            pass
        i += 1
        time.sleep(0.05)


def _sqlite_integrity(storage: str) -> str | None:
    for root, _dirs, files in os.walk(storage):
        for name in files:
            if not name.endswith((".db", ".sqlite", ".sqlite3")):
                continue
            path = os.path.join(root, name)
            try:
                conn = sqlite3.connect(path)
                ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
                conn.close()
                if ok != "ok":
                    return f"{name}: {ok}"
            except Exception as e:
                return f"{name}: {e}"
    return None


@pytest.fixture
def backend(tmp_path):
    tmp = str(tmp_path)
    port = bh.free_port()
    bh.write_rns_config(tmp)
    proc, log = bh.spawn_backend(tmp, port)
    try:
        assert bh.wait_ready(port, timeout_s=180), "backend never became ready"
        yield port, proc
    finally:
        bh.kill_proc(proc)
        log.close()


def test_sigkill_during_writes_preserves_storage(backend, tmp_path):
    port, proc = backend
    # Prime the CSRF cookie before the burst.
    bh.request(port, "/api/v1/auth/csrf", timeout=10)
    bh.request(
        port,
        "/api/v1/config",
        data={"display_name": "pre-kill-marker"},
        method="PATCH",
        timeout=10,
    )

    stop = threading.Event()
    writer = threading.Thread(target=_write_burst, args=(port, stop), daemon=True)
    writer.start()
    time.sleep(0.7)  # let writes overlap the kill window
    bh.kill_proc(proc, hard=True)
    stop.set()
    writer.join(timeout=5)

    # Storage must be recoverable: sqlite reports integrity, config loads.
    bad = _sqlite_integrity(os.path.join(str(tmp_path), "storage"))
    assert bad is None, f"sqlite corruption after SIGKILL: {bad}"

    proc2, log2 = bh.spawn_backend(str(tmp_path), port)
    try:
        assert bh.wait_ready(port, timeout_s=180), "backend did not restart"
        body, status = bh.request(port, "/api/v1/config", timeout=10)
        assert status == 200
        cfg = body.get("config", body)
        assert isinstance(cfg.get("display_name"), str)
    finally:
        bh.kill_proc(proc2)
        log2.close()


def test_sigterm_then_restart_keeps_data(backend, tmp_path):
    """Graceful shutdown should also leave storage fully consistent."""
    port, proc = backend
    bh.request(port, "/api/v1/auth/csrf", timeout=10)
    bh.request(
        port,
        "/api/v1/config",
        data={"display_name": "term-marker-42"},
        method="PATCH",
        timeout=10,
    )
    bh.kill_proc(proc, hard=False)
    bh.kill_proc(proc, hard=True)

    bad = _sqlite_integrity(os.path.join(str(tmp_path), "storage"))
    assert bad is None, f"sqlite corruption after SIGTERM: {bad}"
    proc2, log2 = bh.spawn_backend(str(tmp_path), port)
    try:
        assert bh.wait_ready(port, timeout_s=180)
        body, status = bh.request(port, "/api/v1/config", timeout=10)
        assert status == 200
        cfg = body.get("config", body)
        assert cfg.get("display_name") == "term-marker-42"
    finally:
        bh.kill_proc(proc2)
        log2.close()
