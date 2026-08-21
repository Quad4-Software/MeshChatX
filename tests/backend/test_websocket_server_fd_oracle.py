# SPDX-License-Identifier: 0BSD
"""Oracle: WebsocketServerInterface drops Transport refs after client disconnect."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from meshchatx.src.backend.interfaces.WebsocketServerInterface import (
    WebsocketServerInterface,
)


def test_server_client_disconnect_removes_transport_interface():
    owner = MagicMock()
    config = {
        "name": "ws-server",
        "listen_ip": "127.0.0.1",
        "listen_port": "9",
    }
    fake_ws = MagicMock()
    fake_ws.remote_address = ("127.0.0.1", 12345)

    transport_interfaces: list = []

    class _Child:
        def __init__(self, *_args, **_kwargs):
            self.IN = False
            self.OUT = False
            self.HW_MTU = 0
            self.bitrate = 0
            self.mode = None
            self.parent_interface = None
            self.online = False
            self.announce_rate_target = None
            self.announce_rate_grace = None
            self.announce_rate_penalty = None
            self.detached = False
            self.read_loop_calls = 0
            self.detach_calls = 0

        def __str__(self):
            return "Child"

        def read_loop(self):
            self.read_loop_calls += 1

        def detach(self):
            self.detach_calls += 1
            self.detached = True

    reticulum = MagicMock()
    reticulum._default_ic_max_held_announces.return_value = 256

    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Interfaces.Interface.Interface.get_config_obj", return_value=config),
        patch(
            "meshchatx.src.backend.interfaces.WebsocketServerInterface.threading.Thread",
        ),
        patch("RNS.Transport") as mock_transport,
    ):
        mock_rns.get_instance.return_value = reticulum
        mock_transport.interfaces = transport_interfaces
        server = WebsocketServerInterface(owner, config)

        with patch(
            "meshchatx.src.backend.interfaces.WebsocketServerInterface.WebsocketClientInterface",
            side_effect=lambda *a, **k: _Child(),
        ):
            captured = {}

            def fake_serve(handler, *_args, **_kwargs):
                captured["handler"] = handler

                class _Ctx:
                    def __enter__(self_inner):
                        return MagicMock(serve_forever=MagicMock())

                    def __exit__(self_inner, *_exc):
                        return False

                return _Ctx()

            with patch(
                "meshchatx.src.backend.interfaces.WebsocketServerInterface.serve",
                side_effect=fake_serve,
            ):
                server.detached = False

                def stop_after_one(*_a, **_k):
                    server.detached = True

                with patch("time.sleep", side_effect=stop_after_one):
                    server.serve()

            assert "handler" in captured
            before = len(mock_transport.interfaces)
            captured["handler"](fake_ws)
            assert len(mock_transport.interfaces) == before
            assert server.spawned_interfaces == []
