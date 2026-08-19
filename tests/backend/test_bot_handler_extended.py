# SPDX-License-Identifier: 0BSD

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.bot_handler import BotHandler


@pytest.fixture
def temp_identity_dir(tmp_path):
    dir_path = tmp_path / "identity"
    dir_path.mkdir()
    return str(dir_path)


def test_bot_handler_init(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    assert os.path.exists(handler.bots_dir)
    assert handler.bots_state == []


def test_bot_handler_default_reticulum_dir_falls_back_to_home(
    temp_identity_dir,
    monkeypatch,
):
    monkeypatch.delenv("MESHCHAT_BOT_RETICULUM_CONFIG_DIR", raising=False)
    handler = BotHandler(temp_identity_dir)
    assert handler.bot_reticulum_config_dir == os.path.abspath(
        os.path.expanduser("~/.reticulum"),
    )


def test_bot_handler_uses_app_reticulum_config_dir_for_portable_mode(
    temp_identity_dir,
    tmp_path,
    monkeypatch,
):
    """Bots must stay inside a custom --data-dir / --reticulum-config-dir.

    Root instead of leaking their own RNS instance to the home directory.
    """
    monkeypatch.delenv("MESHCHAT_BOT_RETICULUM_CONFIG_DIR", raising=False)
    portable_reticulum_dir = tmp_path / "persist" / ".reticulum"
    handler = BotHandler(
        temp_identity_dir,
        default_reticulum_config_dir=str(portable_reticulum_dir),
    )
    assert handler.bot_reticulum_config_dir == os.path.abspath(
        str(portable_reticulum_dir),
    )


def test_bot_handler_env_override_wins_over_app_reticulum_config_dir(
    temp_identity_dir,
    tmp_path,
    monkeypatch,
):
    override_dir = tmp_path / "separate-bot-rns"
    monkeypatch.setenv("MESHCHAT_BOT_RETICULUM_CONFIG_DIR", str(override_dir))
    handler = BotHandler(
        temp_identity_dir,
        default_reticulum_config_dir=str(tmp_path / "persist" / ".reticulum"),
    )
    assert handler.bot_reticulum_config_dir == os.path.abspath(str(override_dir))


def test_bot_handler_load_save_state(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    storage = os.path.join(handler.bots_dir, "bot1")
    os.makedirs(storage, exist_ok=True)
    test_state = [{"id": "bot1", "enabled": True, "storage_dir": storage}]
    handler.bots_state = test_state
    handler._save_state()

    handler2 = BotHandler(temp_identity_dir)
    assert len(handler2.bots_state) == 1
    assert handler2.bots_state[0]["id"] == "bot1"
    assert os.path.realpath(handler2.bots_state[0]["storage_dir"]) == os.path.realpath(
        storage,
    )


def test_get_available_templates(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    templates = handler.get_available_templates()
    assert len(templates) > 0
    assert any(t["id"] == "echo" for t in templates)


def test_get_status_empty(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    status = handler.get_status()
    assert isinstance(status, dict)
    assert status["bots"] == []


def test_delete_bot_not_found(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    assert handler.delete_bot("nonexistent") is False


def test_create_bot(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    # start_bot acts as create_bot if bot_id is None
    bot_id = handler.start_bot("echo", "Echo")
    assert any(b["id"] == bot_id for b in handler.bots_state)
    assert os.path.exists(os.path.join(handler.bots_dir, bot_id))


def test_delete_bot_success(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    bot_id = handler.start_bot("echo", "Echo")
    assert handler.delete_bot(bot_id) is True
    assert not any(b["id"] == bot_id for b in handler.bots_state)


def test_get_bot_identity_path(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    bot_id = handler.start_bot("echo", "Echo")
    storage_dir = os.path.join(handler.bots_dir, bot_id)
    id_path = os.path.join(storage_dir, "config", "identity")
    os.makedirs(os.path.dirname(id_path), exist_ok=True)
    with open(id_path, "w") as f:
        f.write("test")

    assert handler.get_bot_identity_path(bot_id) == id_path


def test_restore_enabled_bots(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    handler.bots_state = [
        {
            "id": "b1",
            "template_id": "echo",
            "name": "N",
            "enabled": True,
            "storage_dir": "/tmp/b1",
        },
    ]
    with patch.object(handler, "start_bot") as mock_start:
        handler.restore_enabled_bots()
        mock_start.assert_called_once()


def test_get_status_default_name_from_template(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    sid = "b1"
    storage = os.path.join(handler.bots_dir, sid)
    os.makedirs(storage, exist_ok=True)
    handler.bots_state = [{"id": sid, "template_id": "echo", "storage_dir": storage}]
    status = handler.get_status()
    assert status["bots"][0]["name"] == "Echo Bot"


def test_get_status_reads_sidecar_lxmf_address(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    sid = "b1"
    storage = os.path.join(handler.bots_dir, sid)
    os.makedirs(storage, exist_ok=True)
    hx = "a" * 32
    with open(
        os.path.join(storage, "meshchatx_lxmf_address.txt"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(hx)
    handler.bots_state = [{"id": sid, "template_id": "echo", "storage_dir": storage}]
    status = handler.get_status()
    assert status["bots"][0]["lxmf_address"] == hx
    assert status["bots"][0]["full_address"] == hx
    assert status["bots"][0]["address"] is not None


@patch("subprocess.Popen")
def test_start_stop_bot(mock_popen, temp_identity_dir):
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_popen.return_value = mock_process

    handler = BotHandler(temp_identity_dir)
    bot_id = handler.start_bot("echo", "My Echo Bot")

    assert bot_id in handler.running_bots
    status = handler.get_status()
    assert any(b["id"] == bot_id and b["running"] for b in status["bots"])

    with patch("meshchatx.src.backend.bot_handler.os.kill") as mock_kill:
        handler.stop_bot(bot_id)
        assert mock_kill.called
        assert bot_id not in handler.running_bots


@patch("subprocess.Popen")
def test_start_bot_unfrozen_uses_bot_process_script(mock_popen, temp_identity_dir):
    mock_process = MagicMock()
    mock_process.pid = 4242
    mock_popen.return_value = mock_process

    handler = BotHandler(temp_identity_dir)
    with patch.object(BotHandler, "_is_frozen_executable", return_value=False):
        handler.start_bot("echo", "Script Bot")

    cmd = mock_popen.call_args.args[0]
    assert cmd[0] == sys.executable
    assert cmd[1] == handler.runner_path
    assert "--meshchatx-run-module" not in cmd
    assert cmd[cmd.index("--template") + 1] == "echo"


@patch("subprocess.Popen")
def test_start_bot_frozen_uses_meshchatx_run_module(mock_popen, temp_identity_dir):
    mock_process = MagicMock()
    mock_process.pid = 4243
    mock_popen.return_value = mock_process

    handler = BotHandler(temp_identity_dir)
    with patch.object(BotHandler, "_is_frozen_executable", return_value=True):
        handler.start_bot("echo", "Frozen Bot")

    cmd = mock_popen.call_args.args[0]
    assert cmd[0] == sys.executable
    assert cmd[1] == "--meshchatx-run-module"
    assert cmd[2] == "meshchatx.src.backend.bot_process"
    assert handler.runner_path not in cmd
    assert cmd[cmd.index("--template") + 1] == "echo"


def test_update_bot_name_writes_sidecar(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    sid = "b1"
    storage = os.path.join(handler.bots_dir, sid)
    cfg = os.path.join(storage, "config")
    os.makedirs(cfg, exist_ok=True)
    handler.bots_state = [
        {
            "id": sid,
            "template_id": "echo",
            "name": "Old",
            "storage_dir": storage,
            "bot_config_dir": cfg,
        },
    ]
    handler.update_bot_name(sid, "New Name")
    assert handler.bots_state[0]["name"] == "New Name"
    with open(os.path.join(cfg, "bot_display_name.txt"), encoding="utf-8") as f:
        assert f.read() == "New Name"


def test_update_bot_name_rejects_empty(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    sid = "b1"
    storage = os.path.join(handler.bots_dir, sid)
    os.makedirs(storage, exist_ok=True)
    handler.bots_state = [{"id": sid, "template_id": "echo", "storage_dir": storage}]
    with pytest.raises(ValueError, match="name is required"):
        handler.update_bot_name(sid, "   ")


@patch.object(BotHandler, "_is_pid_alive", return_value=True)
def test_request_announce_writes_trigger(mock_alive, temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    sid = "b1"
    storage = os.path.join(handler.bots_dir, sid)
    os.makedirs(storage, exist_ok=True)
    handler.bots_state = [
        {"id": sid, "template_id": "echo", "storage_dir": storage, "pid": 99999},
    ]
    handler.request_announce(sid)
    req = os.path.join(storage, "meshchatx_request_announce")
    assert os.path.isfile(req)
    with open(req, encoding="utf-8") as f:
        assert f.read() == "1"


def test_request_announce_not_running(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    sid = "b1"
    storage = os.path.join(handler.bots_dir, sid)
    os.makedirs(storage, exist_ok=True)
    handler.bots_state = [
        {"id": sid, "template_id": "echo", "storage_dir": storage, "pid": None},
    ]
    with pytest.raises(RuntimeError, match="not running"):
        handler.request_announce(sid)


def test_get_status_subprocess_log_not_shown_as_last_error(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    sid = "b1"
    storage = os.path.join(handler.bots_dir, sid)
    os.makedirs(storage, exist_ok=True)
    log_path = os.path.join(storage, "meshchatx_bot_subprocess.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("[Info] Received SIGTERM, shutting down now!\n")
    handler.bots_state = [
        {"id": sid, "template_id": "echo", "storage_dir": storage, "pid": None},
    ]
    status = handler.get_status()
    assert status["bots"][0]["last_error"] is None


def test_read_subprocess_log(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    sid = "b1"
    storage = os.path.join(handler.bots_dir, sid)
    os.makedirs(storage, exist_ok=True)
    log_path = os.path.join(storage, "meshchatx_bot_subprocess.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("line1\nline2\n")
    handler.bots_state = [
        {"id": sid, "template_id": "echo", "storage_dir": storage, "pid": None},
    ]
    out = handler.read_subprocess_log(sid)
    assert out["truncated"] is False
    assert out["total_bytes"] > 0
    assert "line2" in (out["log"] or "")


def test_read_subprocess_log_unknown_bot(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    with pytest.raises(ValueError, match="Unknown bot"):
        handler.read_subprocess_log("nope")


def _outside_bait_identity(tmp_path):
    outside = tmp_path / "outside-bot"
    outside.mkdir()
    bait = outside / "identity"
    bait.write_bytes(b"SECRET_BAIT_BYTES")
    log_path = outside / "meshchatx_bot_subprocess.log"
    log_path.write_text("OUTSIDE_LOG\n", encoding="utf-8")
    return outside, bait, log_path


def test_get_bot_identity_path_rejects_escaped_storage(temp_identity_dir, tmp_path):
    handler = BotHandler(temp_identity_dir)
    outside, bait, _log = _outside_bait_identity(tmp_path)
    bot_id = "escaped"
    handler.bots_state = [
        {
            "id": bot_id,
            "storage_dir": str(outside),
            "bot_config_dir": str(outside),
        },
    ]
    assert handler.get_bot_identity_path(bot_id) is None
    assert bait.read_bytes() == b"SECRET_BAIT_BYTES"


def test_corrupt_bots_state_does_not_overwrite_file(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    storage = os.path.join(handler.bots_dir, "bot1")
    os.makedirs(storage, exist_ok=True)
    handler.bots_state = [
        {"id": "bot1", "enabled": True, "storage_dir": storage},
    ]
    handler._save_state()
    original = "{not-json"
    with open(handler.state_file, "w", encoding="utf-8") as handle:
        handle.write(original)
    handler2 = BotHandler(temp_identity_dir)
    handler2._save_state()
    with open(handler.state_file, encoding="utf-8") as handle:
        assert handle.read() == original
    assert handler2.bots_state == []


def test_load_state_drops_escaped_storage(temp_identity_dir, tmp_path):
    handler = BotHandler(temp_identity_dir)
    outside, bait, _log = _outside_bait_identity(tmp_path)
    handler.bots_state = [
        {
            "id": "escaped",
            "enabled": True,
            "storage_dir": str(outside),
            "bot_config_dir": str(outside),
        },
    ]
    handler._save_state()
    handler2 = BotHandler(temp_identity_dir)
    assert handler2.bots_state == []
    assert bait.read_bytes() == b"SECRET_BAIT_BYTES"


def test_read_subprocess_log_rejects_escaped_storage(temp_identity_dir, tmp_path):
    handler = BotHandler(temp_identity_dir)
    outside, bait, log_path = _outside_bait_identity(tmp_path)
    handler.bots_state = [
        {
            "id": "escaped",
            "storage_dir": str(outside),
            "bot_config_dir": str(outside),
        },
    ]
    with pytest.raises(ValueError, match="invalid bot storage directory"):
        handler.read_subprocess_log("escaped")
    assert log_path.read_text(encoding="utf-8") == "OUTSIDE_LOG\n"
    assert bait.read_bytes() == b"SECRET_BAIT_BYTES"


@patch.object(BotHandler, "_is_pid_alive", return_value=True)
def test_request_announce_rejects_escaped_storage(
    mock_alive,
    temp_identity_dir,
    tmp_path,
):
    handler = BotHandler(temp_identity_dir)
    outside, bait, _log = _outside_bait_identity(tmp_path)
    handler.bots_state = [
        {
            "id": "escaped",
            "storage_dir": str(outside),
            "bot_config_dir": str(outside),
            "pid": 99999,
        },
    ]
    with pytest.raises(RuntimeError, match="invalid bot storage directory"):
        handler.request_announce("escaped")
    assert not (outside / "meshchatx_request_announce").exists()
    assert bait.read_bytes() == b"SECRET_BAIT_BYTES"


@pytest.mark.skipif(os.name == "nt", reason="symlink jail oracle is POSIX")
def test_get_bot_identity_path_rejects_symlink_out_bot_config_dir(
    temp_identity_dir,
    tmp_path,
):
    handler = BotHandler(temp_identity_dir)
    bot_id = handler.start_bot("echo", "Echo")
    storage = os.path.join(handler.bots_dir, bot_id)
    outside, bait, _log = _outside_bait_identity(tmp_path)
    cfg_link = os.path.join(storage, "config_link")
    os.symlink(str(outside), cfg_link)
    handler.bots_state[0]["bot_config_dir"] = cfg_link
    assert handler.get_bot_identity_path(bot_id) is None
    assert bait.read_bytes() == b"SECRET_BAIT_BYTES"
