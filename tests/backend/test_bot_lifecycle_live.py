# SPDX-License-Identifier: 0BSD

"""Live create / start / stop / delete coverage for LXMFy bot subprocesses."""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import time

import pytest

import meshchatx.src.backend.bot_process as bot_process_mod
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


def _spawn_watched_bot(tmp_path, parent_pid):
    storage = tmp_path / "watchdog-storage"
    rns_dir = tmp_path / "watchdog-rns"
    storage.mkdir()
    rns_dir.mkdir()
    log_f = open(storage / "subprocess.log", "w", encoding="utf-8")
    cmd = [
        sys.executable,
        os.path.abspath(bot_process_mod.__file__),
        "--template",
        "echo",
        "--name",
        "Watchdog",
        "--storage",
        str(storage),
        "--reticulum-config-dir",
        str(rns_dir),
    ]
    if parent_pid is not None:
        cmd += ["--parent-pid", str(parent_pid)]
    return subprocess.Popen(
        cmd,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    ), log_f


def _kill_process_tree(proc):
    if proc is None or proc.poll() is not None:
        return
    with contextlib.suppress(Exception):
        os.killpg(proc.pid, 9)
    with contextlib.suppress(Exception):
        proc.kill()
    with contextlib.suppress(Exception):
        proc.wait(timeout=5)


def test_bot_process_exits_when_watched_parent_dies(tmp_path):
    """A bot must self-exit once the backend that spawned it is gone.

    A helper process plays the role of the backend: it spawns the bot with
    --parent-pid set to itself, prints the bot pid, then sleeps. Killing the
    helper orphans the bot exactly like a backend crash does.

    Oracle: after the helper exits, the bot is not alive within the watchdog
    interval plus startup margin.
    """
    storage = tmp_path / "watchdog-storage"
    rns_dir = tmp_path / "watchdog-rns"
    storage.mkdir()
    rns_dir.mkdir()
    log_path = storage / "subprocess.log"
    runner = os.path.abspath(bot_process_mod.__file__)
    helper_src = (
        "import subprocess, sys, time\n"
        f"log = open({str(log_path)!r}, 'w')\n"
        "bot = subprocess.Popen([sys.executable, "
        f"{runner!r}, '--template', 'echo', '--name', 'Watchdog', "
        f"'--storage', {str(storage)!r}, '--reticulum-config-dir', "
        f"{str(rns_dir)!r}, '--parent-pid', str(os.getpid())], "
        "stdout=log, stderr=subprocess.STDOUT, start_new_session=True)\n"
        "print(bot.pid, flush=True)\n"
        "time.sleep(300)\n"
    )
    helper_src = "import os\n" + helper_src
    helper = subprocess.Popen(
        [sys.executable, "-c", helper_src],
        stdout=subprocess.PIPE,
        text=True,
    )
    bot_pid = None
    try:
        line = helper.stdout.readline()
        assert line.strip(), "helper exited before reporting the bot pid"
        bot_pid = int(line.strip())
        helper.terminate()
        helper.wait(timeout=5)
        assert _wait_pid_dead(bot_pid, timeout=20.0), (
            "bot survived the death of the backend that spawned it"
        )
    finally:
        _kill_process_tree(helper)
        if bot_pid:
            with contextlib.suppress(Exception):
                os.killpg(bot_pid, 9)


def test_bot_process_exits_when_parent_pid_is_not_real_parent(tmp_path):
    """A mismatched --parent-pid exits at the first watchdog tick.

    Guards against the arg silently diverging from the real parent: getppid
    will never equal the bogus pid, so the bot must not linger.

    Oracle: the bot is dead within the watchdog interval plus margin even
    though the bogus watched pid stays alive.
    """
    sleeper = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(300)"],
    )
    bot = None
    log_f = None
    try:
        bot, log_f = _spawn_watched_bot(tmp_path, sleeper.pid)
        assert _wait_pid_dead(bot.pid, timeout=20.0), (
            "bot lingered with a --parent-pid that is not its real parent"
        )
        assert BotHandler._is_pid_alive(sleeper.pid)
    finally:
        if log_f is not None:
            log_f.close()
        _kill_process_tree(sleeper)
        _kill_process_tree(bot)


def test_bot_process_with_live_parent_stays_up(tmp_path):
    """The watchdog must not false-positive while the backend lives.

    Oracle: a bot watching this test process is still alive after several
    watchdog intervals, then dies when signalled normally.
    """
    bot = None
    log_f = None
    try:
        bot, log_f = _spawn_watched_bot(tmp_path, os.getpid())
        time.sleep(4.0)
        assert BotHandler._is_pid_alive(bot.pid), (
            "bot exited even though its watched parent is still alive"
        )
    finally:
        if log_f is not None:
            log_f.close()
        _kill_process_tree(bot)


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
