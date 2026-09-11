# SPDX-License-Identifier: 0BSD

"""Bot handler coverage for icon appearance, custom commands, uptime.

Also covers the extended LXMF override keys.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.bot_handler import BotHandler


@pytest.fixture
def temp_identity_dir(tmp_path):
    dir_path = tmp_path / "identity"
    dir_path.mkdir()
    return str(dir_path)


@pytest.fixture
def mock_popen():
    with patch("subprocess.Popen") as popen:
        proc = MagicMock()
        proc.pid = 43210
        popen.return_value = proc
        yield popen


def _runtime_sidecar(handler, bot_id):
    path = os.path.join(handler.bots_dir, bot_id, "meshchatx_bot_runtime.json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _bot_status(handler, bot_id):
    status = handler.get_status()
    return next(b for b in status["bots"] if b["id"] == bot_id)


def test_templates_include_custom_and_rrc(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    ids = {t["id"] for t in handler.get_available_templates()}
    assert {"echo", "note", "reminder", "custom", "rrc"} <= ids


@patch("subprocess.Popen")
def test_start_bot_with_icon_stores_and_sidecars(popen, temp_identity_dir):
    popen.return_value = MagicMock(pid=1)
    handler = BotHandler(temp_identity_dir)
    icon = {"icon_name": "robot", "fg_color": "AABBCC", "bg_color": "#112233"}
    bot_id = handler.start_bot("echo", "Icon Bot", icon=icon)

    status = _bot_status(handler, bot_id)
    assert status["icon"] == {
        "icon_name": "robot",
        "fg_color": "#aabbcc",
        "bg_color": "#112233",
    }
    assert status["uptime_seconds"] is not None
    assert status["last_started_at"]

    sidecar = _runtime_sidecar(handler, bot_id)
    assert sidecar["icon"]["icon_name"] == "robot"

    cmd = popen.call_args.args[0]
    assert "--runtime-config-file" in cmd


@patch("subprocess.Popen")
def test_start_bot_rejects_bad_icon(popen, temp_identity_dir):
    popen.return_value = MagicMock(pid=1)
    handler = BotHandler(temp_identity_dir)
    with pytest.raises(ValueError):
        handler.start_bot("echo", "Bad", icon={"icon_name": "not ok!"})
    popen.assert_not_called()


@patch("subprocess.Popen")
def test_update_bot_icon_set_and_clear(popen, temp_identity_dir):
    popen.return_value = MagicMock(pid=1)
    handler = BotHandler(temp_identity_dir)
    bot_id = handler.start_bot("echo", "E")

    saved = handler.update_bot_icon(
        bot_id, {"icon_name": "alien", "fg_color": "#00ff00"}
    )
    assert saved["icon_name"] == "alien"
    assert _bot_status(handler, bot_id)["icon"]["icon_name"] == "alien"

    cleared = handler.update_bot_icon(bot_id, None)
    assert cleared is None
    assert _bot_status(handler, bot_id)["icon"] is None

    with pytest.raises(ValueError):
        handler.update_bot_icon("nonexistent", {"icon_name": "x"})
    with pytest.raises(ValueError):
        handler.update_bot_icon(bot_id, {"icon_name": "bad name"})


@patch("subprocess.Popen")
def test_custom_template_requires_commands(popen, temp_identity_dir):
    popen.return_value = MagicMock(pid=1)
    handler = BotHandler(temp_identity_dir)
    with pytest.raises(ValueError):
        handler.start_bot("custom", "C")
    with pytest.raises(ValueError):
        handler.start_bot(
            "custom", "C", custom={"commands": [{"name": "x", "response": ""}]}
        )
    popen.assert_not_called()


@patch("subprocess.Popen")
def test_custom_template_start_and_update(popen, temp_identity_dir):
    popen.return_value = MagicMock(pid=1)
    handler = BotHandler(temp_identity_dir)
    custom = {
        "commands": [{"name": "joke", "response": "ha"}],
        "welcome": "hi there",
    }
    bot_id = handler.start_bot("custom", "C", custom=custom)
    status = _bot_status(handler, bot_id)
    assert status["custom"]["commands"][0]["name"] == "joke"
    assert status["custom"]["welcome"] == "hi there"

    saved = handler.update_bot_custom(
        bot_id, {"commands": [{"name": "ping", "response": "pong"}]}
    )
    assert saved["commands"][0]["name"] == "ping"

    # restart keeps the stored custom config
    bot_id2 = handler.start_bot("custom", "C", bot_id=bot_id, storage_dir=None)
    assert _bot_status(handler, bot_id2)["custom"]["commands"][0]["name"] == "ping"


@patch("subprocess.Popen")
def test_custom_config_rejected_on_non_custom_template(popen, temp_identity_dir):
    popen.return_value = MagicMock(pid=1)
    handler = BotHandler(temp_identity_dir)
    with pytest.raises(ValueError):
        handler.start_bot(
            "echo", "E", custom={"commands": [{"name": "x", "response": "y"}]}
        )
    bot_id = handler.start_bot("echo", "E")
    with pytest.raises(ValueError):
        handler.update_bot_custom(
            bot_id, {"commands": [{"name": "x", "response": "y"}]}
        )


@patch("subprocess.Popen")
def test_extended_lxmf_overrides_round_trip(popen, temp_identity_dir):
    popen.return_value = MagicMock(pid=1)
    handler = BotHandler(temp_identity_dir)
    bot_id = handler.start_bot("echo", "E")

    saved = handler.update_bot_lxmf_config(
        bot_id,
        {
            "command_prefix": "?",
            "rate_limit": "7",
            "cooldown": 5,
            "max_warnings": 2,
            "warning_timeout": 120,
            "message_queue_size": 80,
            "signature_verification_enabled": True,
            "require_message_signatures": False,
            "require_stamps": True,
            "request_unknown_identities": True,
            "identity_pinning_enabled": False,
            "permissions_enabled": True,
            "lxmf_commands_enabled": True,
            "message_persistence_enabled": False,
            "announce_enabled": True,
            "admins": ["a" * 32, "junk", "b" * 32],
            "autopeer_maxdepth": 3,
        },
    )
    assert saved["command_prefix"] == "?"
    assert saved["rate_limit"] == 7
    assert saved["cooldown"] == 5
    assert saved["max_warnings"] == 2
    assert saved["warning_timeout"] == 120
    assert saved["message_queue_size"] == 80
    assert saved["signature_verification_enabled"] is True
    assert saved["require_message_signatures"] is False
    assert saved["require_stamps"] is True
    assert saved["announce_enabled"] is True
    assert saved["admins"] == ["a" * 32, "b" * 32]
    assert saved["autopeer_maxdepth"] == 3

    # clearing via explicit null restores template defaults
    cleared = handler.update_bot_lxmf_config(
        bot_id, {"command_prefix": None, "admins": None, "rate_limit": None}
    )
    assert "command_prefix" not in cleared
    assert "admins" not in cleared
    assert "rate_limit" not in cleared


@patch("subprocess.Popen")
def test_runtime_sidecar_written_for_lxmf_settings(popen, temp_identity_dir):
    """The lxmf sidecar still carries effective overrides alongside runtime."""
    popen.return_value = MagicMock(pid=1)
    handler = BotHandler(temp_identity_dir)
    bot_id = handler.start_bot(
        "echo",
        "E",
        icon={"icon_name": "forum"},
        lxmf_config={"command_prefix": "?", "rate_limit": 3},
    )
    lxmf = json.load(
        open(
            os.path.join(handler.bots_dir, bot_id, "meshchatx_bot_lxmf_config.json"),
            encoding="utf-8",
        )
    )
    assert lxmf["command_prefix"] == "?"
    assert lxmf["rate_limit"] == 3
    sidecar = _runtime_sidecar(handler, bot_id)
    assert sidecar["icon"]["icon_name"] == "forum"
