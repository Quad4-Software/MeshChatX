# SPDX-License-Identifier: 0BSD

"""Wall-time budgets for live WS fan-out and gap_hint."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.websocket_runtime import BroadcastSeqState, WsRuntimeCounters

FANOUT_BUDGET_MS = 2500.0
GAP_HINT_BUDGET_MS = 50.0


class MagicWs:
    def __init__(self):
        self.send_str = AsyncMock(return_value=None)
        self.close = AsyncMock(return_value=None)


@pytest.mark.asyncio
async def test_broadcast_fanout_budget(mock_app):
    mock_app.websocket_clients.clear()
    mock_app.ws_seq_state = BroadcastSeqState()
    mock_app.ws_counters = WsRuntimeCounters()
    mock_app._ws_coalesce = None
    clients = [MagicWs() for _ in range(200)]
    mock_app.websocket_clients.extend(clients)
    real = ReticulumMeshChat.websocket_broadcast.__get__(mock_app, ReticulumMeshChat)
    t0 = time.perf_counter()
    await real({"type": "announce", "n": 1})
    wall_ms = (time.perf_counter() - t0) * 1000
    assert wall_ms < FANOUT_BUDGET_MS, (
        f"fan-out {wall_ms:.1f}ms exceeded {FANOUT_BUDGET_MS}ms"
    )
    for c in clients:
        assert c.send_str.await_count == 1


@pytest.mark.asyncio
async def test_gap_hint_budget_under_full_ring():
    state = BroadcastSeqState()
    for i in range(300):
        await state.stamp({"type": "t", "i": i})
    t0 = time.perf_counter()
    for _ in range(1000):
        state.gap_hint(0)
    wall_ms = (time.perf_counter() - t0) * 1000
    assert wall_ms < 500.0, f"gap_hint loop too slow: {wall_ms:.1f}ms"
