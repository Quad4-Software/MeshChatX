# SPDX-License-Identifier: 0BSD

"""config.set WebSocket ack / error oracles."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from meshchatx.src.backend.http.ws.handlers_core import handle_config_set


@pytest.mark.asyncio
async def test_config_set_sends_success_ack():
    app = MagicMock()
    app.update_config = AsyncMock(return_value=None)
    app.send_config_to_websocket_clients = AsyncMock(return_value=None)
    client = MagicMock()
    client.send_str = AsyncMock(return_value=None)

    await handle_config_set(
        app,
        client,
        {"type": "config.set", "config": {"theme": "dark"}, "request_id": "abc"},
    )

    client.send_str.assert_awaited()
    payload = json.loads(client.send_str.await_args[0][0])
    assert payload["type"] == "config.set"
    assert payload["status"] == "success"
    assert payload["request_id"] == "abc"


@pytest.mark.asyncio
async def test_config_set_sends_error_on_failure():
    app = MagicMock()
    app.update_config = AsyncMock(side_effect=RuntimeError("boom"))
    client = MagicMock()
    client.send_str = AsyncMock(return_value=None)

    await handle_config_set(
        app,
        client,
        {"type": "config.set", "config": {"theme": "dark"}, "request_id": "xyz"},
    )

    client.send_str.assert_awaited()
    payload = json.loads(client.send_str.await_args[0][0])
    assert payload["type"] == "error"
    assert payload["code"] == "config_set_failed"
    assert payload["request_id"] == "xyz"
