# SPDX-License-Identifier: 0BSD

import os
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.bot_handler import BotHandler
from meshchatx.src.backend.bot_lxmf_config import (
    load_bot_lxmf_config_sidecar,
    merge_bot_lxmf_overrides,
    normalize_lxmf_destination_hash,
    resolve_effective_bot_lxmf_settings,
    resolve_host_lxmf_propagation_settings,
    write_bot_lxmf_config_sidecar,
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
    assert normalize_lxmf_destination_hash(f"<{'abcd' * 8}>") == "abcd" * 8
    assert normalize_lxmf_destination_hash("too-short") is None


def test_resolve_host_uses_manual_propagation_node_over_autopeer():
    node = "1234567890abcdef1234567890abcdef"
    settings = resolve_host_lxmf_propagation_settings(
        _mock_config(preferred_hash=node, auto_select=True),
    )
    assert settings["propagation_node"] == node
    assert settings["autopeer_propagation"] is False
    assert settings["propagation_fallback_enabled"] is True


def test_per_bot_manual_propagation_overrides_host():
    host_node = "a" * 32
    bot_node = "b" * 32
    effective = resolve_effective_bot_lxmf_settings(
        _mock_config(preferred_hash=host_node, auto_select=True),
        {
            "lxmf_config": {
                "propagation_mode": "manual",
                "propagation_node": bot_node,
            },
        },
    )
    assert effective["propagation_node"] == bot_node
    assert effective["autopeer_propagation"] is False


def test_per_bot_autopeer_overrides_host_manual():
    host_node = "a" * 32
    effective = resolve_effective_bot_lxmf_settings(
        _mock_config(preferred_hash=host_node),
        {"lxmf_config": {"propagation_mode": "autopeer"}},
    )
    assert "propagation_node" not in effective
    assert effective["autopeer_propagation"] is True


def test_per_bot_none_disables_host_propagation():
    host_node = "a" * 32
    effective = resolve_effective_bot_lxmf_settings(
        _mock_config(preferred_hash=host_node),
        {"lxmf_config": {"propagation_mode": "none"}},
    )
    assert "propagation_node" not in effective
    assert effective["autopeer_propagation"] is False


def test_per_bot_delivery_and_announce_overrides():
    effective = resolve_effective_bot_lxmf_settings(
        _mock_config(),
        {
            "lxmf_config": {
                "direct_delivery_retries": 1,
                "opportunistic_sending": False,
                "announce_interval_seconds": 120,
                "stamp_cost": 4,
            },
        },
    )
    assert effective["direct_delivery_retries"] == 1
    assert effective["opportunistic_sending"] is False
    assert effective["announce"] == 120
    assert effective["stamp_cost"] == 4


def test_merge_clears_overrides_with_nulls():
    stored = {
        "propagation_mode": "manual",
        "propagation_node": "c" * 32,
        "direct_delivery_retries": 2,
    }
    merged = merge_bot_lxmf_overrides(
        stored,
        {
            "propagation_mode": "inherit",
            "direct_delivery_retries": None,
        },
    )
    assert merged == {}


def test_sidecar_roundtrip(tmp_path):
    storage = tmp_path / "bot"
    storage.mkdir()
    settings = {
        "propagation_node": "d" * 32,
        "propagation_fallback_enabled": True,
        "direct_delivery_retries": 2,
        "announce": 300,
    }
    path = write_bot_lxmf_config_sidecar(str(storage), settings)
    loaded = load_bot_lxmf_config_sidecar(path)
    assert loaded["propagation_node"] == "d" * 32
    assert loaded["direct_delivery_retries"] == 2
    assert loaded["announce"] == 300


@patch("subprocess.Popen")
def test_start_bot_writes_lxmf_sidecar_and_passes_path(mock_popen, temp_identity_dir):
    mock_process = MagicMock()
    mock_process.pid = 9001
    mock_popen.return_value = mock_process

    bot_node = "e" * 32
    handler = BotHandler(
        temp_identity_dir,
        config_manager=_mock_config(preferred_hash="f" * 32),
    )
    bot_id = handler.start_bot(
        "echo",
        "Custom Prop",
        lxmf_config={
            "propagation_mode": "manual",
            "propagation_node": bot_node,
        },
    )

    cmd = mock_popen.call_args.args[0]
    idx = cmd.index("--lxmf-config-file")
    sidecar = cmd[idx + 1]
    loaded = load_bot_lxmf_config_sidecar(sidecar)
    assert loaded["propagation_node"] == bot_node

    entry = next(e for e in handler.bots_state if e["id"] == bot_id)
    assert entry["lxmf_config"]["propagation_node"] == bot_node


@patch("subprocess.Popen")
def test_start_bot_inherits_host_when_no_bot_override(mock_popen, temp_identity_dir):
    mock_process = MagicMock()
    mock_process.pid = 9002
    mock_popen.return_value = mock_process

    host_node = "a" * 32
    handler = BotHandler(
        temp_identity_dir,
        config_manager=_mock_config(preferred_hash=host_node),
    )
    handler.start_bot("echo", "Host Prop")

    cmd = mock_popen.call_args.args[0]
    idx = cmd.index("--lxmf-config-file")
    loaded = load_bot_lxmf_config_sidecar(cmd[idx + 1])
    assert loaded["propagation_node"] == host_node


def test_update_bot_lxmf_config_persists(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    storage = os.path.join(handler.bots_dir, "bot1")
    os.makedirs(storage, exist_ok=True)
    handler.bots_state = [
        {
            "id": "bot1",
            "template_id": "echo",
            "name": "Bot",
            "storage_dir": storage,
            "enabled": False,
        },
    ]
    saved = handler.update_bot_lxmf_config(
        "bot1",
        {"propagation_mode": "autopeer", "direct_delivery_retries": 5},
    )
    assert saved["propagation_mode"] == "autopeer"
    assert saved["direct_delivery_retries"] == 5
    handler2 = BotHandler(temp_identity_dir)
    entry = handler2.bots_state[0]
    assert entry["lxmf_config"]["propagation_mode"] == "autopeer"


def test_echo_bot_template_forwards_lxmf_settings(tmp_path):
    node = "c" * 32
    bot = EchoBotTemplate(
        name="Echo",
        storage_path=str(tmp_path / "storage"),
        test_mode=True,
        config_path=str(tmp_path / "config"),
        reticulum_config_dir=str(tmp_path / "rns"),
        lxmf_settings={
            "propagation_node": node,
            "propagation_fallback_enabled": True,
            "direct_delivery_retries": 1,
        },
    )
    assert bot.bot.config.propagation_node == node
    assert bot.bot.config.propagation_fallback_enabled is True
    assert bot.bot.config.direct_delivery_retries == 1
    bot.bot.cleanup()
