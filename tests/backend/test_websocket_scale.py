"""Scale and concurrency tests for websocket broadcast fan-out (core architecture)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat


def _bind_real_websocket_broadcast(app):
    return ReticulumMeshChat.websocket_broadcast.__get__(app, ReticulumMeshChat)


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
    payload = '{"type":"config","config":{}}'
    await real(payload)

    for c in clients:
        assert c.send_str.await_count == 1
        assert c.send_str.await_args[0][0] == payload


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

    If another coroutine mutates ``websocket_clients`` during iteration, using
    ``list(...)`` avoids skipping entries (classic mutating-list pitfall).
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


class MagicWs:
    def __init__(self):
        self.send_str = AsyncMock(return_value=None)


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
        assert c.send_str.await_args[0][0] == payload
