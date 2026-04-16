# SPDX-License-Identifier: 0BSD

import os
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


def test_bot_handler_load_save_state(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    test_state = [{"id": "bot1", "enabled": True, "storage_dir": "some/path"}]
    handler.bots_state = test_state
    handler._save_state()

    # New handler instance to load state
    handler2 = BotHandler(temp_identity_dir)
    assert len(handler2.bots_state) == 1
    assert handler2.bots_state[0]["id"] == "bot1"


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

    with patch("psutil.Process"):
        handler.stop_bot(bot_id)
        assert bot_id not in handler.running_bots


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
