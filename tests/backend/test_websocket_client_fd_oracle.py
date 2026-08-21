# SPDX-License-Identifier: 0BSD
"""Oracle: WebsocketClientInterface reconnect closes the previous socket."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import meshchatx.src.backend.interfaces.WebsocketClientInterface as ws_mod
from meshchatx.src.backend.interfaces.WebsocketClientInterface import (
    WebsocketClientInterface,
)


class _FakeWs:
    def __init__(self, fail_iter=False):
        self.closed = False
        self._fail_iter = fail_iter

    def close(self):
        self.closed = True

    def __iter__(self):
        if self._fail_iter:
            raise ConnectionError("peer gone")
        return iter(())


def _make_client() -> WebsocketClientInterface:
    owner = MagicMock()
    config = {"name": "ws-client", "target_url": "ws://127.0.0.1:9"}
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Interfaces.Interface.Interface.get_config_obj", return_value=config),
        patch.object(ws_mod.threading, "Thread"),
    ):
        mock_rns.get_instance.return_value = MagicMock(
            _default_ic_max_held_announces=MagicMock(return_value=256),
        )
        return WebsocketClientInterface(owner, config)


def test_reconnect_closes_previous_websocket_before_opening_next():
    """Each reconnect must close the prior Connection or FDs accumulate."""
    client = _make_client()
    client.RECONNECT_DELAY_SECONDS = 0
    created: list[_FakeWs] = []

    def fake_connect(*_args, **_kwargs):
        ws = _FakeWs(fail_iter=True)
        created.append(ws)
        return ws

    sleep_calls = {"n": 0}

    def fake_sleep(_seconds):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            client.detached = True

    with (
        patch.object(ws_mod, "connect", side_effect=fake_connect),
        patch.object(ws_mod.time, "sleep", side_effect=fake_sleep),
    ):
        client.connect()

    assert len(created) >= 2
    assert all(ws.closed for ws in created)
    assert client.websocket is None


def test_close_websocket_clears_reference_and_calls_close():
    client = _make_client()
    ws = _FakeWs()
    client.websocket = ws
    client._close_websocket()
    assert client.websocket is None
    assert ws.closed is True
