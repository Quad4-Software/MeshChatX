# SPDX-License-Identifier: 0BSD

"""Resilience checks for android/app/src/main/python/meshchat_wrapper.py."""

from __future__ import annotations

import importlib
import sys
import threading
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ANDROID_PY = _REPO_ROOT / "android" / "app" / "src" / "main" / "python"
if str(_ANDROID_PY) not in sys.path:
    sys.path.insert(0, str(_ANDROID_PY))


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
