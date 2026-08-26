# SPDX-License-Identifier: 0BSD

"""Independent oracles for per-bot LXMF config merge, resolve, and sidecar I/O."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.bot_handler import BotHandler
from meshchatx.src.backend.bot_lxmf_config import (
    describe_bot_lxmf_config,
    load_bot_lxmf_config_sidecar,
    merge_bot_lxmf_overrides,
    normalize_bot_lxmf_overrides,
    resolve_effective_bot_lxmf_settings,
    validate_bot_lxmf_patch,
    write_bot_lxmf_config_sidecar,
)


@pytest.fixture
def temp_identity_dir(tmp_path):
    dir_path = tmp_path / "identity"
    dir_path.mkdir()
    return str(dir_path)


def _mock_config(*, preferred_hash=None, auto_select=False, fallback_enabled=True):
    config = MagicMock()
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        preferred_hash
    )
    config.lxmf_preferred_propagation_node_auto_select.get.return_value = auto_select
    config.auto_send_failed_messages_to_propagation_node.get.return_value = (
        fallback_enabled
    )
    return config


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, {}),
        ("not-a-dict", {}),
        ({"propagation_mode": "inherit"}, {}),
        ({"propagation_mode": "bogus"}, {}),
        ({"propagation_mode": "manual"}, {}),
        (
            {"propagation_mode": "manual", "propagation_node": "ab" * 16},
            {"propagation_mode": "manual", "propagation_node": "ab" * 16},
        ),
        ({"direct_delivery_retries": -1}, {}),
        ({"direct_delivery_retries": 33}, {}),
        ({"direct_delivery_retries": 3}, {"direct_delivery_retries": 3}),
        ({"announce_interval_seconds": 10}, {}),
        ({"announce_interval_seconds": 120}, {"announce_interval_seconds": 120}),
        ({"stamp_cost": -1}, {}),
        (
            {"propagation_mode": "autopeer", "propagation_node": "cd" * 16},
            {"propagation_mode": "autopeer"},
        ),
    ],
)
def test_normalize_bot_lxmf_overrides_oracle(raw, expected):
    assert normalize_bot_lxmf_overrides(raw) == expected


def test_merge_autopeer_drops_stale_manual_node():
    stored = {
        "propagation_mode": "manual",
        "propagation_node": "a" * 32,
    }
    merged = merge_bot_lxmf_overrides(stored, {"propagation_mode": "autopeer"})
    assert merged == {"propagation_mode": "autopeer"}
    effective = resolve_effective_bot_lxmf_settings(
        _mock_config(preferred_hash="b" * 32),
        {"lxmf_config": merged},
    )
    assert "propagation_node" not in effective
    assert effective["autopeer_propagation"] is True


def test_merge_inherit_clears_all_propagation_overrides():
    stored = {
        "propagation_mode": "manual",
        "propagation_node": "c" * 32,
        "propagation_fallback_enabled": False,
    }
    merged = merge_bot_lxmf_overrides(stored, {"propagation_mode": "inherit"})
    assert merged == {"propagation_fallback_enabled": False}
    effective = resolve_effective_bot_lxmf_settings(
        _mock_config(preferred_hash="d" * 32, fallback_enabled=False),
        {"lxmf_config": merged},
    )
    assert effective["propagation_node"] == "d" * 32


def test_merge_null_clears_optional_numeric_override():
    stored = {"direct_delivery_retries": 2, "stamp_cost": 5}
    merged = merge_bot_lxmf_overrides(
        stored,
        {"direct_delivery_retries": None, "stamp_cost": None},
    )
    assert merged == {}


def test_validate_rejects_manual_without_node():
    with pytest.raises(ValueError, match="propagation_node is required"):
        validate_bot_lxmf_patch(
            {"propagation_mode": "manual", "propagation_node": "too-short"},
        )


def test_update_bot_lxmf_config_rejects_invalid_manual(temp_identity_dir):
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
    with pytest.raises(ValueError, match="propagation_node is required"):
        handler.update_bot_lxmf_config(
            "bot1",
            {"propagation_mode": "manual", "propagation_node": "nope"},
        )


def test_sidecar_preserves_disabled_propagation_fallback(tmp_path):
    storage = tmp_path / "bot"
    storage.mkdir()
    settings = {
        "autopeer_propagation": True,
        "propagation_fallback_enabled": False,
    }
    path = write_bot_lxmf_config_sidecar(str(storage), settings)
    loaded = load_bot_lxmf_config_sidecar(path)
    assert loaded["autopeer_propagation"] is True
    assert loaded["propagation_fallback_enabled"] is False


def test_sidecar_rejects_invalid_json(tmp_path):
    storage = tmp_path / "bot"
    storage.mkdir()
    path = storage / "meshchatx_bot_lxmf_config.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_bot_lxmf_config_sidecar(str(path)) == {}


def test_describe_bot_lxmf_config_matches_resolve(temp_identity_dir):
    handler = BotHandler(
        temp_identity_dir,
        config_manager=_mock_config(preferred_hash="e" * 32),
    )
    storage = os.path.join(handler.bots_dir, "bot1")
    os.makedirs(storage, exist_ok=True)
    entry = {
        "id": "bot1",
        "storage_dir": storage,
        "lxmf_config": {
            "propagation_mode": "none",
            "direct_delivery_retries": 1,
        },
    }
    described = describe_bot_lxmf_config(handler.config_manager, entry)
    assert described["lxmf_config"]["propagation_mode"] == "none"
    assert described["effective_lxmf_config"]["direct_delivery_retries"] == 1
    assert "propagation_node" not in described["effective_lxmf_config"]
    assert described["host_lxmf_propagation"]["propagation_node"] == "e" * 32


@patch("subprocess.Popen")
def test_restart_rewrites_sidecar_from_updated_config(mock_popen, temp_identity_dir):
    mock_process = MagicMock()
    mock_process.pid = 111
    mock_popen.return_value = mock_process

    handler = BotHandler(
        temp_identity_dir,
        config_manager=_mock_config(preferred_hash="f" * 32),
    )
    bot_id = handler.start_bot("echo", "Restart Me")
    handler.update_bot_lxmf_config(
        bot_id,
        {"propagation_mode": "manual", "propagation_node": "1" * 32},
    )
    handler.restart_bot(bot_id)

    cmd = mock_popen.call_args.args[0]
    idx = cmd.index("--lxmf-config-file")
    loaded = load_bot_lxmf_config_sidecar(cmd[idx + 1])
    assert loaded["propagation_node"] == "1" * 32
    assert loaded.get("autopeer_propagation") is not True


def test_orphan_propagation_node_overrides_host_without_mode():
    effective = resolve_effective_bot_lxmf_settings(
        _mock_config(preferred_hash="a" * 32),
        {"lxmf_config": {"propagation_node": "b" * 32}},
    )
    assert effective["propagation_node"] == "b" * 32
    assert effective["autopeer_propagation"] is False


def test_host_fallback_disabled_propagates_when_bot_inherits():
    effective = resolve_effective_bot_lxmf_settings(
        _mock_config(fallback_enabled=False),
        {"lxmf_config": {}},
    )
    assert effective["propagation_fallback_enabled"] is False


def test_bot_fallback_override_beats_host():
    effective = resolve_effective_bot_lxmf_settings(
        _mock_config(fallback_enabled=False),
        {"lxmf_config": {"propagation_fallback_enabled": True}},
    )
    assert effective["propagation_fallback_enabled"] is True


def test_state_roundtrip_json_serializable(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    storage = os.path.join(handler.bots_dir, "bot1")
    os.makedirs(storage, exist_ok=True)
    handler.bots_state = [
        {
            "id": "bot1",
            "template_id": "echo",
            "name": "Bot",
            "storage_dir": storage,
            "lxmf_config": {"propagation_mode": "autopeer"},
        },
    ]
    handler._save_state()
    handler2 = BotHandler(temp_identity_dir)
    assert handler2.bots_state[0]["lxmf_config"]["propagation_mode"] == "autopeer"
    raw = json.loads(open(handler2.state_file, encoding="utf-8").read())
    assert raw[0]["lxmf_config"]["propagation_mode"] == "autopeer"
