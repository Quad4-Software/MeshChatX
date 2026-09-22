# SPDX-License-Identifier: 0BSD

"""Cross-event-loop forwarding for ReticulumMeshChat.websocket_broadcast.

Per-identity background loops run asyncio.run on daemon threads, so a
broadcast awaited from them lands on a foreign loop. The send must be
re-dispatched onto AsyncUtils.main_loop where the aiohttp transports live.
"""

from __future__ import annotations

import asyncio
import json
import threading
from unittest.mock import patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.async_utils import AsyncUtils as RealAsyncUtils


class _FakeWs:
    """Plain object so attribute probes behave like a real ws client."""


def _bare_app():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.websocket_clients = []
    app.ws_seq_state = None
    app.ws_counters = None
    app._ws_coalesce = None
    app._websocket_broadcast_lock = asyncio.Lock()
    return app


@pytest.fixture
def foreign_main_loop():
    # The autouse global_mocks fixture replaces meshchatx.meshchat.AsyncUtils
    # with a MagicMock, so swap the real class back for these tests.
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    old = RealAsyncUtils.main_loop
    RealAsyncUtils.main_loop = loop
    try:
        with patch("meshchatx.meshchat.AsyncUtils", RealAsyncUtils):
            yield loop
    finally:
        RealAsyncUtils.main_loop = old
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)
        loop.close()


async def test_broadcast_from_foreign_loop_sends_on_main_loop(foreign_main_loop):
    app = _bare_app()
    seen = {}
    client = _FakeWs()

    async def send_str(data):
        seen["on_main_loop"] = asyncio.get_running_loop() is foreign_main_loop
        seen["payload"] = json.loads(data)

    client.send_str = send_str
    app.websocket_clients = [client]

    # This coroutine runs on the pytest loop while AsyncUtils.main_loop
    # points at a different running loop, matching the daemon-thread case.
    await app.websocket_broadcast(json.dumps({"type": "test.event"}))

    assert seen["on_main_loop"] is True
    assert seen["payload"]["type"] == "test.event"


async def test_broadcast_on_main_loop_sends_inline():
    app = _bare_app()
    seen = {}
    client = _FakeWs()

    async def send_str(data):
        seen["loop"] = asyncio.get_running_loop()

    client.send_str = send_str
    app.websocket_clients = [client]

    old = RealAsyncUtils.main_loop
    RealAsyncUtils.main_loop = asyncio.get_running_loop()
    try:
        with patch("meshchatx.meshchat.AsyncUtils", RealAsyncUtils):
            await app.websocket_broadcast(json.dumps({"type": "test.event"}))
    finally:
        RealAsyncUtils.main_loop = old

    assert seen["loop"] is asyncio.get_running_loop()
