# SPDX-License-Identifier: 0BSD

"""Oracles for settings stamp restore and interface enable rollback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from meshchatx.meshchat import ReticulumMeshChat


@pytest.mark.asyncio
async def test_oracle_block_all_restore_preserves_zero_stamp_cost():
    """Disabling block-all must restore stamps-off (0), not fall back to 8."""
    app = MagicMock(spec=ReticulumMeshChat)
    app.config = MagicMock()
    app.message_router = None
    app.local_lxmf_destination = None
    app._parse_bool = staticmethod(ReticulumMeshChat._parse_bool)
    app.sync_telephone_call_policy = MagicMock()
    app.send_config_to_websocket_clients = AsyncMock()
    app.send_active_sessions_to_websocket_clients = AsyncMock()

    stamp_cost = {"v": 0}
    before = {"v": -1}
    block = {"v": False}

    app.config.lxmf_inbound_stamp_cost.get.side_effect = lambda: stamp_cost["v"]
    app.config.lxmf_inbound_stamp_cost.set.side_effect = lambda v: (
        stamp_cost.__setitem__(
            "v",
            v,
        )
    )
    app.config.lxmf_inbound_stamp_cost_before_block.get.side_effect = lambda: before[
        "v"
    ]
    app.config.lxmf_inbound_stamp_cost_before_block.set.side_effect = lambda v: (
        before.__setitem__("v", v)
    )
    app.config.block_all_from_strangers.get.side_effect = lambda: block["v"]
    app.config.block_all_from_strangers.set.side_effect = lambda v: block.__setitem__(
        "v",
        v,
    )

    await ReticulumMeshChat.update_config(app, {"block_all_from_strangers": True})
    assert stamp_cost["v"] == 254
    assert before["v"] == 0

    await ReticulumMeshChat.update_config(app, {"block_all_from_strangers": False})
    assert stamp_cost["v"] == 0
    assert before["v"] == -1


def test_oracle_enable_disable_pass_rollback_interfaces():
    src = Path("meshchatx/src/backend/http/routes/interfaces/crud.py").read_text(
        encoding="utf-8",
    )
    enable_idx = src.index("async def reticulum_interfaces_enable")
    disable_idx = src.index("async def reticulum_interfaces_disable")
    delete_idx = src.index("async def reticulum_interfaces_delete")
    enable_body = src[enable_idx:disable_idx]
    disable_body = src[disable_idx:delete_idx]
    assert "rollback_interfaces=interfaces_before_write" in enable_body
    assert "rollback_interfaces=interfaces_before_write" in disable_body
    assert "_get_interfaces_snapshot()" in enable_body
    assert "_get_interfaces_snapshot()" in disable_body


def test_oracle_discovery_patch_reports_reload_failure():
    src = Path(
        "meshchatx/src/backend/http/routes/reticulum_instance/discovery.py",
    ).read_text(encoding="utf-8")
    patch_idx = src.index("async def reticulum_discovery_patch")
    next_idx = src.index("async def reticulum_discovered_interfaces")
    body = src[patch_idx:next_idx]
    assert "RNS reload failed" in body
    assert "status=500" in body


def test_oracle_interface_stats_replace_map():
    src = Path(
        "meshchatx/src/frontend/features/interfaces/lib/interfacesApi.ts",
    ).read_text(encoding="utf-8")
    assert "const nextStats" in src
    assert "return nextStats" in src
