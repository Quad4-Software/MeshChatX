# SPDX-License-Identifier: 0BSD

"""Resilience checks for android/app/src/main/python/meshchat_wrapper.py."""

from __future__ import annotations

import http.server
import importlib
import json
import socket
import sys
import threading
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ANDROID_PY = _REPO_ROOT / "android" / "app" / "src" / "main" / "python"
if str(_ANDROID_PY) not in sys.path:
    sys.path.insert(0, str(_ANDROID_PY))


def _free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _FakeStatusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/v1/status":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(
            {
                "status": "ok",
                "stage": "ready",
                "network_ready": True,
                "network_degraded": False,
                "listen_port": self.server.server_port,
                "https_enabled": True,
            },
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args, **_kwargs):
        pass


def test_start_server_second_call_skips_while_main_blocks(monkeypatch):
    import meshchatx.meshchat as mm

    entered = threading.Event()
    release = threading.Event()
    calls: list[int] = []

    def fake_main():
        calls.append(1)
        entered.set()
        assert release.wait(timeout=10.0)

    monkeypatch.setattr(mm, "main", fake_main)
    import meshchat_wrapper

    importlib.reload(meshchat_wrapper)

    th = threading.Thread(
        target=lambda: meshchat_wrapper.start_server(8000, None),
        daemon=True,
    )
    th.start()
    assert entered.wait(timeout=10.0)
    assert calls == [1]

    meshchat_wrapper.start_server(8000, None)
    assert calls == [1]

    release.set()
    th.join(timeout=10.0)


def test_start_server_hook_failure_still_invokes_main(monkeypatch):
    import meshchatx.meshchat as mm

    calls: list[int] = []

    monkeypatch.setattr(mm, "main", lambda: calls.append(1))

    def boom(*_a, **_k):
        raise RuntimeError("hook test")

    monkeypatch.setattr("meshchatx.android_push_bridge.install_websocket_hook", boom)
    import meshchat_wrapper

    importlib.reload(meshchat_wrapper)
    meshchat_wrapper.start_server(8000, None)
    assert calls == [1]


def test_start_server_clears_stale_storage_lock(monkeypatch, tmp_path):
    import meshchatx.meshchat as mm

    calls: list[int] = []
    monkeypatch.setattr(mm, "main", lambda: calls.append(1))

    storage = tmp_path / "meshchatx" / "storage"
    storage.mkdir(parents=True)
    lock_path = storage / ".meshchatx.lock"
    lock_path.write_bytes(b"12345")

    import meshchat_wrapper

    importlib.reload(meshchat_wrapper)
    meshchat_wrapper.start_server(8000, str(tmp_path))
    assert calls == [1]
    assert not lock_path.exists()


def test_clear_stale_storage_lock_missing_is_ok(tmp_path):
    import meshchat_wrapper

    importlib.reload(meshchat_wrapper)
    meshchat_wrapper._clear_stale_storage_lock(str(tmp_path / "missing"))
    storage = tmp_path / "storage"
    storage.mkdir()
    meshchat_wrapper._clear_stale_storage_lock(str(storage))


def test_start_server_systemexit_includes_cause(monkeypatch):
    import pytest

    import meshchatx.meshchat as mm

    def fake_main():
        try:
            raise RuntimeError("storage lock held by pid 12345")
        except RuntimeError as exc:
            raise SystemExit(1) from exc

    monkeypatch.setattr(mm, "main", fake_main)
    import meshchat_wrapper

    importlib.reload(meshchat_wrapper)
    with pytest.raises(RuntimeError) as excinfo:
        meshchat_wrapper.start_server(8000, None)
    message = str(excinfo.value)
    assert "code=1" in message
    assert "storage lock held by pid 12345" in message


def test_wait_for_own_backend_or_free_port_reports_free_port():
    import meshchat_wrapper

    importlib.reload(meshchat_wrapper)
    port = _free_port()
    outcome = meshchat_wrapper._wait_for_own_backend_or_free_port(
        port,
        wait_seconds=1.0,
        poll_interval=0.1,
    )
    assert outcome == "free"


def test_wait_for_own_backend_or_free_port_detects_existing_backend():
    import meshchat_wrapper

    importlib.reload(meshchat_wrapper)
    port = _free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), _FakeStatusHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        started = time.monotonic()
        outcome = meshchat_wrapper._wait_for_own_backend_or_free_port(
            port,
            wait_seconds=5.0,
            poll_interval=0.1,
            probe_timeout=1.0,
        )
        elapsed = time.monotonic() - started
        assert outcome == "serving"
        assert elapsed < 4.0
    finally:
        server.shutdown()
        thread.join(timeout=5.0)


def test_wait_for_own_backend_or_free_port_reports_busy_for_foreign_listener():
    import meshchat_wrapper

    importlib.reload(meshchat_wrapper)
    port = _free_port()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", port))
    listener.listen(1)
    try:
        outcome = meshchat_wrapper._wait_for_own_backend_or_free_port(
            port,
            wait_seconds=0.2,
            poll_interval=0.1,
            probe_timeout=0.3,
        )
        assert outcome == "busy"
    finally:
        listener.close()


def test_start_server_skips_duplicate_when_backend_already_serving(monkeypatch):
    import meshchatx.meshchat as mm

    calls: list[int] = []
    monkeypatch.setattr(mm, "main", lambda: calls.append(1))

    import meshchat_wrapper

    importlib.reload(meshchat_wrapper)
    monkeypatch.setattr(
        meshchat_wrapper,
        "_wait_for_own_backend_or_free_port",
        lambda *_a, **_k: "serving",
    )

    meshchat_wrapper.start_server(8000, None)
    assert calls == []
    assert meshchat_wrapper._server_loop_active is False
