# SPDX-License-Identifier: 0BSD

"""Scale and concurrency tests for websocket broadcast fan-out (core architecture)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.websocket_runtime import (
    BroadcastSeqState,
    WsRuntimeCounters,
)


def _bind_real_websocket_broadcast(app):
    if not hasattr(app, "ws_seq_state") or app.ws_seq_state is None:
        app.ws_seq_state = BroadcastSeqState()
    if not hasattr(app, "ws_counters") or app.ws_counters is None:
        app.ws_counters = WsRuntimeCounters()
    if not hasattr(app, "_ws_coalesce"):
        app._ws_coalesce = None
    return ReticulumMeshChat.websocket_broadcast.__get__(app, ReticulumMeshChat)


def _assert_delivered(clients, *, expect_type=None):
    for c in clients:
        assert c.send_str.await_count >= 1
        raw = c.send_str.await_args[0][0]
        assert isinstance(raw, str)
        if expect_type is not None:
            parsed = json.loads(raw)
            assert parsed["type"] == expect_type
            assert "seq" in parsed


@pytest.mark.asyncio
async def test_websocket_broadcast_fanout_many_clients(mock_app):
    mock_app.websocket_clients.clear()
    n = 400
    clients = []
    for _ in range(n):
        c = MagicWs()
        clients.append(c)
    mock_app.websocket_clients.extend(clients)

    real = _bind_real_websocket_broadcast(mock_app)
    await real('{"type":"config","config":{}}')
    _assert_delivered(clients, expect_type="config")


@pytest.mark.asyncio
async def test_websocket_broadcast_json_dumps_dict_payload(mock_app):
    mock_app.websocket_clients.clear()
    client = MagicWs()
    mock_app.websocket_clients.append(client)
    real = _bind_real_websocket_broadcast(mock_app)
    await real({"type": "startup_status", "status": "ok", "stage": "ready"})
    raw = client.send_str.await_args[0][0]
    assert isinstance(raw, str)
    parsed = json.loads(raw)
    assert parsed["type"] == "startup_status"
    assert "seq" in parsed


@pytest.mark.asyncio
async def test_websocket_broadcast_concurrent_broadcasts(mock_app):
    mock_app.websocket_clients.clear()
    clients = [MagicWs() for _ in range(120)]
    mock_app.websocket_clients.extend(clients)
    real = _bind_real_websocket_broadcast(mock_app)

    await asyncio.gather(
        real('{"type":"a"}'),
        real('{"type":"b"}'),
        real('{"type":"c"}'),
    )

    for c in clients:
        assert c.send_str.await_count == 3


@pytest.mark.asyncio
async def test_websocket_broadcast_soak_iterations(mock_app):
    mock_app.websocket_clients.clear()
    clients = [MagicWs() for _ in range(80)]
    mock_app.websocket_clients.extend(clients)
    real = _bind_real_websocket_broadcast(mock_app)

    for i in range(60):
        await real(f'{{"type":"tick","i":{i}}}')

    for c in clients:
        assert c.send_str.await_count == 60


@pytest.mark.asyncio
async def test_websocket_broadcast_iterates_snapshot_not_live_list(mock_app):
    """Broadcast must iterate a snapshot of websocket clients, not the live list.

    If another coroutine mutates websocket_clients during iteration, using
    list(...) avoids skipping entries (classic mutating-list pitfall).
    """
    mock_app.websocket_clients.clear()
    clients = [MagicWs() for _ in range(5)]
    lst = mock_app.websocket_clients
    lst.extend(clients)

    async def remove_last_client(_data):
        await asyncio.sleep(0)
        if clients[4] in lst:
            lst.remove(clients[4])

    clients[1].send_str = AsyncMock(side_effect=remove_last_client)
    real = _bind_real_websocket_broadcast(mock_app)
    await real("x")
    assert clients[4].send_str.await_count == 1
    for c in clients[:4]:
        assert c.send_str.await_count == 1


@pytest.mark.asyncio
async def test_websocket_broadcast_drops_dead_clients(mock_app):
    mock_app.websocket_clients.clear()
    bad = MagicWs()
    bad.send_str = AsyncMock(side_effect=RuntimeError("closed"))
    good = MagicWs()
    mock_app.websocket_clients.extend([bad, good])

    real = _bind_real_websocket_broadcast(mock_app)
    await real('{"type":"ping"}')

    assert bad not in mock_app.websocket_clients
    assert good in mock_app.websocket_clients
    assert good.send_str.await_count == 1


@pytest.mark.asyncio
async def test_websocket_broadcast_all_clients_dead_empties_list(mock_app):
    mock_app.websocket_clients.clear()
    clients = []
    for _ in range(80):
        c = MagicWs()
        c.send_str = AsyncMock(side_effect=ConnectionError("closed"))
        clients.append(c)
    mock_app.websocket_clients.extend(clients)

    real = _bind_real_websocket_broadcast(mock_app)
    await real("{}")

    assert mock_app.websocket_clients == []


@pytest.mark.asyncio
async def test_websocket_broadcast_fanout_large_client_pool(mock_app):
    mock_app.websocket_clients.clear()
    n = 1500
    clients = [MagicWs() for _ in range(n)]
    mock_app.websocket_clients.extend(clients)

    real = _bind_real_websocket_broadcast(mock_app)
    await real('{"type":"metrics","x":1}')
    _assert_delivered(clients, expect_type="metrics")


@pytest.mark.asyncio
async def test_websocket_broadcast_mixed_failures_still_delivers_to_healthy(mock_app):
    mock_app.websocket_clients.clear()
    failing = [MagicWs() for _ in range(40)]
    for c in failing:
        c.send_str = AsyncMock(side_effect=BrokenPipeError())
    healthy = [MagicWs() for _ in range(60)]
    mock_app.websocket_clients.extend(failing + healthy)

    real = _bind_real_websocket_broadcast(mock_app)
    await real('{"type":"ping"}')

    for c in failing:
        assert c not in mock_app.websocket_clients
    assert mock_app.websocket_clients == healthy
    for c in healthy:
        assert c.send_str.await_count == 1


@pytest.mark.asyncio
async def test_websocket_broadcast_respects_topic_subscription(mock_app):
    mock_app.websocket_clients.clear()
    all_topics = MagicWs()
    lxmf_only = MagicWs()
    lxmf_only._meshchatx_ws_topics = {"lxmf"}
    mock_app.websocket_clients.extend([all_topics, lxmf_only])
    real = _bind_real_websocket_broadcast(mock_app)
    # Use a non-coalesced type so delivery is immediate.
    await real({"type": "rrc.message", "x": 1})
    assert all_topics.send_str.await_count == 1
    assert lxmf_only.send_str.await_count == 0
    await real({"type": "lxmf.delivery", "x": 1})
    assert lxmf_only.send_str.await_count == 1


class MagicWs:
    def __init__(self):
        self.send_str = AsyncMock(return_value=None)
        self.close = AsyncMock(return_value=None)


@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=20,
    deadline=None,
)
@given(
    n=st.integers(min_value=1, max_value=128),
    payload=st.text(min_size=0, max_size=512),
)
@pytest.mark.asyncio
async def test_websocket_broadcast_fanout_property(mock_app, n, payload):
    mock_app.websocket_clients.clear()
    clients = [MagicWs() for _ in range(n)]
    mock_app.websocket_clients.extend(clients)
    real = _bind_real_websocket_broadcast(mock_app)
    await real(payload)
    for c in clients:
        assert c.send_str.await_count == 1
        raw = c.send_str.await_args[0][0]
        assert isinstance(raw, str)
        try:
            parsed = json.loads(payload)
        except (TypeError, ValueError, json.JSONDecodeError):
            assert raw == payload
            continue
        if isinstance(parsed, dict):
            out = json.loads(raw)
            assert out.get("type") == parsed.get("type")
            assert "seq" in out
        else:
            assert raw == payload
