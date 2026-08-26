# SPDX-License-Identifier: 0BSD

from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.bot_handler import BotHandler
from meshchatx.src.backend.bot_propagation import (
    normalize_lxmf_destination_hash,
    propagation_settings_from_cli,
    propagation_settings_to_cli_args,
    resolve_bot_lxmf_propagation_settings,
)
from meshchatx.src.backend.bot_templates import EchoBotTemplate


@pytest.fixture
def temp_identity_dir(tmp_path):
    dir_path = tmp_path / "identity"
    dir_path.mkdir()
    return str(dir_path)


def _mock_config(
    *,
    preferred_hash=None,
    auto_select=False,
    fallback_enabled=True,
):
    config = MagicMock()
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        preferred_hash
    )
    config.lxmf_preferred_propagation_node_auto_select.get.return_value = auto_select
    config.auto_send_failed_messages_to_propagation_node.get.return_value = (
        fallback_enabled
    )
    return config


def test_normalize_lxmf_destination_hash_accepts_bytes_and_pretty():
    raw = bytes.fromhex("abcd" * 8)
    assert normalize_lxmf_destination_hash(raw) == "abcd" * 8
    assert normalize_lxmf_destination_hash(f"<{ 'abcd' * 8 }>") == "abcd" * 8
    assert normalize_lxmf_destination_hash("too-short") is None


def test_resolve_uses_manual_propagation_node_over_autopeer():
    node = "1234567890abcdef1234567890abcdef"
    settings = resolve_bot_lxmf_propagation_settings(
        _mock_config(preferred_hash=node, auto_select=True),
    )
    assert settings["propagation_node"] == node
    assert settings["autopeer_propagation"] is False
    assert settings["propagation_fallback_enabled"] is True


def test_resolve_enables_autopeer_when_no_manual_node():
    settings = resolve_bot_lxmf_propagation_settings(
        _mock_config(preferred_hash=None, auto_select=True),
    )
    assert "propagation_node" not in settings
    assert settings["autopeer_propagation"] is True


def test_resolve_honors_propagation_fallback_toggle():
    settings = resolve_bot_lxmf_propagation_settings(
        _mock_config(fallback_enabled=False),
    )
    assert settings["propagation_fallback_enabled"] is False


def test_resolve_without_config_manager_defaults_to_lxmfy_like_fallback():
    settings = resolve_bot_lxmf_propagation_settings(None)
    assert settings == {
        "propagation_fallback_enabled": True,
        "autopeer_propagation": False,
    }


def test_propagation_cli_roundtrip_manual_node():
    node = "fedcba0987654321fedcba0987654321"
    settings = {
        "propagation_node": node,
        "autopeer_propagation": False,
        "propagation_fallback_enabled": True,
    }
    args = propagation_settings_to_cli_args(settings)
    assert args == ["--propagation-node", node]
    rebuilt = propagation_settings_from_cli(
        propagation_node=node,
        autopeer_propagation=False,
        propagation_fallback_enabled=True,
    )
    assert rebuilt["propagation_node"] == node
    assert rebuilt["autopeer_propagation"] is False


def test_propagation_cli_autopeer_and_disabled_fallback():
    settings = {
        "autopeer_propagation": True,
        "propagation_fallback_enabled": False,
    }
    assert propagation_settings_to_cli_args(settings) == [
        "--autopeer-propagation",
        "--no-propagation-fallback",
    ]


@patch("subprocess.Popen")
def test_start_bot_passes_host_propagation_cli(mock_popen, temp_identity_dir):
    mock_process = MagicMock()
    mock_process.pid = 9001
    mock_popen.return_value = mock_process

    node = "a" * 32
    handler = BotHandler(
        temp_identity_dir,
        config_manager=_mock_config(preferred_hash=node, auto_select=True),
    )
    handler.start_bot("echo", "Prop Echo")

    cmd = mock_popen.call_args.args[0]
    idx = cmd.index("--propagation-node")
    assert cmd[idx + 1] == node
    assert "--autopeer-propagation" not in cmd
    assert "--no-propagation-fallback" not in cmd


@patch("subprocess.Popen")
def test_start_bot_passes_autopeer_when_host_auto_select(mock_popen, temp_identity_dir):
    mock_process = MagicMock()
    mock_process.pid = 9002
    mock_popen.return_value = mock_process

    handler = BotHandler(
        temp_identity_dir,
        config_manager=_mock_config(preferred_hash=None, auto_select=True),
    )
    handler.start_bot("echo", "Auto Echo")

    cmd = mock_popen.call_args.args[0]
    assert "--autopeer-propagation" in cmd
    assert "--propagation-node" not in cmd


def test_echo_bot_template_forwards_propagation_settings(tmp_path):
    node = "c" * 32
    bot = EchoBotTemplate(
        name="Echo",
        storage_path=str(tmp_path / "storage"),
        test_mode=True,
        config_path=str(tmp_path / "config"),
        reticulum_config_dir=str(tmp_path / "rns"),
        propagation_settings={
            "propagation_node": node,
            "propagation_fallback_enabled": True,
            "autopeer_propagation": False,
        },
    )
    assert bot.bot.config.propagation_node == node
    assert bot.bot.config.propagation_fallback_enabled is True
    assert bot.bot.config.autopeer_propagation is False
    bot.bot.cleanup()
