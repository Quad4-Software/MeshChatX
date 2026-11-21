# SPDX-License-Identifier: 0BSD

"""Live SIGTERM test: exit inside the deadline with a clean database.

Gated behind MESHCHAT_LIVE_VALIDATION=1 like the other live tests.
"""

from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.live_validation

_LIVE = (
    os.environ.get("MESHCHAT_LIVE_VALIDATION") == "1"
    or os.environ.get("MESHCHAT_LIVE_RETICULUM") == "1"
)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEADLINE_S = 15.0


def _wait_for_ready(proc, log_fh, timeout=90.0):
    deadline = time.monotonic() + timeout
    pos = 0
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            log_fh.flush()
            raise AssertionError("backend exited during startup")
        log_fh.flush()
        with open(log_fh.name, errors="replace") as fh:
            fh.seek(pos)
            text = fh.read()
            pos = fh.tell()
        if "Network stack ready" in text or "deferred setup complete" in text:
            return
        time.sleep(0.5)
    raise AssertionError("backend never reached ready")


@pytest.mark.skipif(not _LIVE, reason="Set MESHCHAT_LIVE_VALIDATION=1 for live tests")
@pytest.mark.integration
def test_sigterm_exits_within_deadline_with_clean_db(tmp_path):
    storage = tmp_path / "storage"
    rns_dir = tmp_path / "rns"
    rns_dir.mkdir()
    (rns_dir / "config").write_text(
        "[reticulum]\n  enable_transport = False\n  share_instance = No\n\n"
        "[interfaces]\n"
        "[[TCP Server]]\n"
        "  type = TCPServerInterface\n"
        "  enabled = yes\n"
        "  listen_ip = 127.0.0.1\n"
        "  listen_port = 42973\n"
    )
    status_file = tmp_path / "shutdown-status.json"
    log_path = tmp_path / "backend.log"
    env = dict(os.environ)
    env["MESHCHATX_SHUTDOWN_STATUS"] = str(status_file)

    log_fh = open(log_path, "w+")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "meshchatx.meshchat",
            "--headless",
            "--no-https",
            "--host",
            "127.0.0.1",
            "--port",
            "18190",
            "--storage-dir",
            str(storage),
            "--reticulum-config-dir",
            str(rns_dir),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_for_ready(proc, log_fh)
        start = time.monotonic()
        proc.send_signal(signal.SIGTERM)
        exit_s = None
        deadline = start + DEADLINE_S
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                exit_s = time.monotonic() - start
                break
            time.sleep(0.1)
        assert exit_s is not None, (
            f"backend still running {DEADLINE_S}s after SIGTERM; "
            f"log tail: {open(log_path, errors='replace').read()[-2000:]}"
        )

        # Progress reporting must have produced at least the early steps.
        assert status_file.exists(), "shutdown status file never written"
        import json

        payload = json.loads(status_file.read_text())
        assert payload["step"] in {
            "signal",
            "websocket-flush",
            "databases",
            "ratchet",
            "background-services",
            "propagation-tasks",
            "contexts",
            "websocket-clients",
            "network",
            "done",
            "cancelled",
            "teardown-error",
        }

        # Database integrity: opening and a quick check must succeed. The
        # WAL may be present but must be recoverable.
        dbs = list(storage.rglob("*.db")) + list(storage.rglob("*.sqlite*"))
        main_dbs = [d for d in dbs if d.suffix in {".db", ".sqlite", ".sqlite3"}]
        assert main_dbs, f"no databases found under {storage}"
        for db in main_dbs:
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                result = conn.execute("PRAGMA quick_check").fetchone()
                assert result and result[0] == "ok", (
                    f"{db} failed quick_check: {result}"
                )
            finally:
                conn.close()
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)
        log_fh.close()
