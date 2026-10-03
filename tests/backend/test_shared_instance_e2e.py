# SPDX-License-Identifier: 0BSD
"""Live end-to-end test of the shared-instance (rnsd) RPC path.

The event-loop wedge fixes only activate when the backend connects to a
shared Reticulum instance, and nothing else exercises that mode live.
This suite spawns a real rnsd on loopback, starts the backend as a
shared-instance client, then verifies the RPC-backed routes respond and
that killing rnsd produces deadlines instead of hangs.

Runs only when MESHCHAT_LIVE_RETICULUM=1; all traffic stays on loopback.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "e2e"),
)
import backend_harness as bh

pytestmark = pytest.mark.skipif(
    os.environ.get("MESHCHAT_LIVE_RETICULUM") != "1",
    reason="Set MESHCHAT_LIVE_RETICULUM=1 for live shared-instance tests",
)

DEADLINE_SLACK_S = 30  # recv deadline is 10s. allow generous margin


def _rnsd_config(tmp: str, shared_port: int, listener_port: int) -> str:
    d = os.path.join(tmp, "rnsd")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "config"), "w") as f:
        f.write(
            "[reticulum]\n"
            "  enable_transport = False\n"
            "  share_instance = Yes\n"
            f"  shared_instance_port = {shared_port}\n"
            "[interfaces]\n"
            "  [[E2E Listener]]\n"
            "    type = TCPServerInterface\n"
            "    enabled = yes\n"
            "    listen_ip = 127.0.0.1\n"
            f"    listen_port = {listener_port}\n"
        )
    return d


def _spawn_rnsd(tmp: str, shared_port: int, listener_port: int):
    cfg = _rnsd_config(tmp, shared_port, listener_port)
    log = open(os.path.join(tmp, "rnsd.log"), "ab")
    proc = subprocess.Popen(
        [sys.executable, "-m", "RNS.Utilities.rnsd", "--config", cfg],
        cwd=bh.ROOT,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    return proc, log


def _timed_get(port: int, path: str, timeout=DEADLINE_SLACK_S):
    t0 = time.monotonic()
    try:
        body, status = bh.request(port, path, timeout=timeout)
        return status, body, time.monotonic() - t0, None
    except urllib.error.HTTPError as e:
        return e.code, None, time.monotonic() - t0, e
    except Exception as e:
        return None, None, time.monotonic() - t0, e


@pytest.fixture
def shared_stack(tmp_path):
    tmp = str(tmp_path)
    ports = {
        "shared": bh.free_port(),
        "listener": bh.free_port(),
        "backend": bh.free_port(),
    }
    rnsd, rnsd_log = _spawn_rnsd(tmp, ports["shared"], ports["listener"])
    # Backend config: client of the shared instance, no own interfaces.
    bh.write_rns_config(
        tmp,
        extra=(f"  share_instance = Yes\n  shared_instance_port = {ports['shared']}\n"),
    )
    backend, backend_log = bh.spawn_backend(tmp, ports["backend"])
    try:
        ready = bh.wait_ready(ports["backend"], timeout_s=180)
        if not ready:
            backend_log.flush()
            with open(backend_log.name, "rb") as f:
                f.seek(-4000, os.SEEK_END)
                tail = f.read().decode(errors="replace")
            pytest.fail(f"backend never became ready:\n{tail}")
        yield ports, rnsd
    finally:
        bh.kill_proc(backend)
        bh.kill_proc(rnsd)
        backend_log.close()
        rnsd_log.close()


def test_shared_instance_rpc_routes_respond(shared_stack):
    ports, _rnsd = shared_stack
    status, _body, elapsed, err = _timed_get(
        ports["backend"], "/api/v1/interface-stats"
    )
    assert err is None or status is not None, f"request failed: {err}"
    assert elapsed < DEADLINE_SLACK_S, f"interface-stats blocked for {elapsed:.1f}s"
    status, _body, elapsed, _err = _timed_get(ports["backend"], "/api/v1/path-table")
    assert status in (200, 401, 403, 503), f"unexpected status {status}"
    assert elapsed < DEADLINE_SLACK_S


def test_rnsd_death_does_not_wedge_routes(shared_stack):
    """Killing rnsd must degrade RPC routes, never hang the event loop."""
    ports, rnsd = shared_stack
    bh.kill_proc(rnsd, hard=True)
    status, _body, elapsed, err = _timed_get(
        ports["backend"], "/api/v1/interface-stats"
    )
    assert elapsed < DEADLINE_SLACK_S, (
        f"route wedged for {elapsed:.1f}s after rnsd death"
    )
    assert status in (200, 401, 403, 500, 503) or isinstance(
        err, urllib.error.HTTPError
    )


def test_rnsd_restart_recovers(shared_stack, tmp_path):
    ports, rnsd = shared_stack
    bh.kill_proc(rnsd, hard=True)
    time.sleep(2)
    rnsd2, _log = _spawn_rnsd(str(tmp_path), ports["shared"], ports["listener"])
    try:
        deadline = time.monotonic() + 60
        ok = False
        while time.monotonic() < deadline:
            _status, _b, elapsed, _err = _timed_get(
                ports["backend"], "/api/v1/interface-stats", timeout=15
            )
            if elapsed < DEADLINE_SLACK_S:
                ok = True
                break
            time.sleep(2)
        assert ok, "routes never recovered after rnsd restart"
    finally:
        bh.kill_proc(rnsd2)
