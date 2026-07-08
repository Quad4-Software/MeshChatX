# SPDX-License-Identifier: 0BSD

"""Live create / start / stop / delete coverage for LXMFy bot subprocesses."""

from __future__ import annotations

import os
import time

import pytest

from meshchatx.src.backend.bot_handler import BotHandler


@pytest.fixture
def bot_lifecycle_dirs(tmp_path, monkeypatch):
    identity_dir = tmp_path / "identity"
    rns_dir = tmp_path / "reticulum"
    identity_dir.mkdir()
    rns_dir.mkdir()
    monkeypatch.setenv("MESHCHAT_BOT_RETICULUM_CONFIG_DIR", str(rns_dir))
    return identity_dir, rns_dir


def _wait_pid_dead(pid: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not BotHandler._is_pid_alive(pid):
            return True
        time.sleep(0.05)
    return not BotHandler._is_pid_alive(pid)


def test_bot_create_start_stop_delete_live(bot_lifecycle_dirs):
    identity_dir, _rns_dir = bot_lifecycle_dirs
    handler = BotHandler(str(identity_dir))

    bot_id = handler.start_bot("echo", "Lifecycle Echo")
    entry = next(e for e in handler.bots_state if e["id"] == bot_id)
    pid = entry["pid"]
    storage_dir = entry["storage_dir"]

    assert pid
    assert BotHandler._is_pid_alive(pid)
    assert os.path.isdir(storage_dir)

    # Give the child a moment to write its start banner / RNS config.
    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        if not BotHandler._is_pid_alive(pid):
            err = BotHandler._read_bot_last_error(storage_dir)
            log = handler.read_subprocess_log(bot_id)
            pytest.fail(
                f"bot died early: err={err!r} log={log.get('log')!r}",
            )
        log = handler.read_subprocess_log(bot_id)
        if (log.get("total_bytes") or 0) > 0:
            break
        time.sleep(0.1)

    assert handler.stop_bot(bot_id) is True
    assert _wait_pid_dead(pid)
    assert bot_id not in handler.running_bots

    status = handler.get_status()
    stopped = next(b for b in status["bots"] if b["id"] == bot_id)
    assert stopped["running"] is False

    assert handler.delete_bot(bot_id) is True
    assert not any(e.get("id") == bot_id for e in handler.bots_state)
    assert not os.path.exists(storage_dir)


def test_bot_frozen_launcher_prefix_avoids_script_path(bot_lifecycle_dirs, monkeypatch):
    identity_dir, _rns_dir = bot_lifecycle_dirs
    handler = BotHandler(str(identity_dir))
    monkeypatch.setattr(BotHandler, "_is_frozen_executable", staticmethod(lambda: True))

    cmd = handler._resolve_bot_launcher()
    assert cmd[0]
    assert cmd[1] == "--meshchatx-run-module"
    assert cmd[2] == "meshchatx.src.backend.bot_process"
    assert handler.runner_path not in cmd


def test_check_bot_lifecycle_self_test_helper(tmp_path):
    """Exercise ReticulumMeshChat._check_bot_lifecycle without full app boot."""
    from meshchatx.meshchat import ReticulumMeshChat

    storage = tmp_path / "storage"
    storage.mkdir()
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.current_context = None
    app.storage_dir = str(storage)

    ok, reason = app._check_bot_lifecycle()
    assert ok is True, reason
    assert reason == ""
    assert not (storage / ".self_test_bots").exists()
