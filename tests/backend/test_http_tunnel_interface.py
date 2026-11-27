# SPDX-License-Identifier: 0BSD

import threading
import time
from unittest.mock import MagicMock, patch

import RNS

from meshchatx.src.backend.data.interfaces.HTTPInterface import (
    HDLC,
    HTTPTunnelInterface,
)


def _reticulum_stub():
    inst = MagicMock()
    for name in (
        "_default_ic_max_held_announces",
        "_default_ic_burst_hold",
        "_default_ic_burst_freq_new",
        "_default_ic_burst_freq",
        "_default_ic_pr_burst_freq_new",
        "_default_ic_pr_burst_freq",
        "_default_ic_new_time",
        "_default_ic_burst_penalty",
        "_default_ic_held_release_interval",
        "_default_ec_pr_freq",
        "_default_ec_egress_control",
    ):
        getattr(inst, name).return_value = 0
    return inst


def _client_interface(poll_interval=0.1):
    cfg = {
        "name": "test-http-tunnel",
        "mode": "client",
        "server_url": "http://127.0.0.1:9/",
    }
    if poll_interval is not None:
        cfg["poll_interval"] = poll_interval
    with (
        patch.object(RNS.Reticulum, "get_instance", return_value=_reticulum_stub()),
        patch.object(HTTPTunnelInterface, "setup_client", lambda self: None),
    ):
        return HTTPTunnelInterface(MagicMock(), cfg)


def test_poll_interval_defaults_to_mesh_sane_value():
    iface = _client_interface(poll_interval=None)
    assert iface.poll_interval == HTTPTunnelInterface.DEFAULT_POLL_INTERVAL
    assert iface.poll_interval >= 2.0


def test_poll_interval_has_hard_floor_even_for_hand_edited_config():
    iface = _client_interface(poll_interval=0.1)
    assert iface.poll_interval == HTTPTunnelInterface.MIN_POLL_INTERVAL

    iface = _client_interface(poll_interval=0)
    assert iface.poll_interval == HTTPTunnelInterface.MIN_POLL_INTERVAL

    iface = _client_interface(poll_interval=2.5)
    assert iface.poll_interval == 2.5


def test_client_failure_backoff_still_grows_from_clamped_interval():
    iface = _client_interface(poll_interval=0.1)
    iface._consecutive_failures = 0
    iface._max_backoff = 30.0
    iface._client_exchange = MagicMock(side_effect=OSError("offline"))

    class StopAfterTwoWaits:
        def __init__(self):
            self.waits = []

        def is_set(self):
            return len(self.waits) >= 2

        def wait(self, delay):
            self.waits.append(delay)
            return True

    stop = StopAfterTwoWaits()
    iface._stop_event = stop
    iface.client_loop()

    assert stop.waits == [iface.poll_interval, iface.poll_interval * 2]


def test_long_poll_returns_queued_server_frame_promptly():
    iface = _client_interface(poll_interval=None)
    iface.online = True
    iface.check_user_agent = False
    iface.LONG_POLL_TIMEOUT = 0.5

    result = {}

    def call_handler():
        started = time.monotonic()
        status, content_type, body = iface._handle_tunnel_exchange(
            "POST",
            "/",
            {},
            b"",
        )
        result.update(
            status=status,
            content_type=content_type,
            body=body,
            elapsed=time.monotonic() - started,
        )

    worker = threading.Thread(target=call_handler, daemon=True)
    worker.start()
    time.sleep(0.03)
    iface.process_outgoing(b"abc")
    worker.join(timeout=1.0)

    assert not worker.is_alive()
    assert result["status"] == 200
    assert result["content_type"] == "application/octet-stream"
    assert result["body"] == HDLC.frame(b"abc")
    assert result["elapsed"] < 0.4


def _server_interface():
    cfg = {
        "name": "test-http-tunnel-server",
        "mode": "server",
        "listen_host": "127.0.0.1",
        "listen_port": 0,
    }
    with patch.object(RNS.Reticulum, "get_instance", return_value=_reticulum_stub()):
        iface = HTTPTunnelInterface(MagicMock(), cfg)
    deadline = time.monotonic() + 5
    while getattr(iface, "_http_server", None) is None:
        assert time.monotonic() < deadline, "HTTP/1.1 server did not start"
        time.sleep(0.01)
    return iface


def _raw_post(port, header_lines):
    import socket as _socket

    with _socket.create_connection(("127.0.0.1", port), timeout=5) as conn:
        request = (
            "POST / HTTP/1.1\r\nHost: 127.0.0.1\r\n"
            + header_lines
            + "Connection: close\r\n\r\n"
        )
        conn.sendall(request.encode("latin1"))
        chunks = []
        while True:
            data = conn.recv(65536)
            if not data:
                break
            chunks.append(data)
    return b"".join(chunks).decode("latin1")


def test_do_post_rejects_invalid_content_length():
    iface = _server_interface()
    try:
        port = iface._http_server.server_address[1]
        response = _raw_post(port, "Content-Length: not-a-number\r\n")
        status_line = response.split("\r\n", 1)[0]
        assert " 400 " in status_line
    finally:
        iface.detach()


def test_do_post_rejects_oversized_content_length_without_reading_body():
    iface = _server_interface()
    try:
        iface._handle_tunnel_exchange = MagicMock(
            return_value=(200, "application/octet-stream", b""),
        )
        port = iface._http_server.server_address[1]
        over = HTTPTunnelInterface.MAX_HTTP_BODY_BYTES + 1
        response = _raw_post(port, f"Content-Length: {over}\r\n")
        status_line = response.split("\r\n", 1)[0]
        assert " 413 " in status_line
        iface._handle_tunnel_exchange.assert_not_called()
    finally:
        iface.detach()


def test_asgi_app_rejects_oversized_body():
    import asyncio

    iface = _client_interface()
    app = iface._build_asgi_app()
    iface._handle_tunnel_exchange = MagicMock(
        return_value=(200, "application/octet-stream", b""),
    )

    messages = [
        {
            "type": "http.request",
            "body": b"x" * (HTTPTunnelInterface.MAX_HTTP_BODY_BYTES + 1),
            "more_body": False,
        },
    ]
    sent = []

    async def receive():
        return messages.pop(0)

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": "POST", "path": "/", "headers": []}
    asyncio.run(app(scope, receive, send))

    assert sent[0]["status"] == 413
    iface._handle_tunnel_exchange.assert_not_called()


def test_detach_with_closed_asgi_loop_does_not_raise():
    import asyncio

    iface = _client_interface()
    iface.mode = "server"
    iface.http_version = 2
    loop = asyncio.new_event_loop()
    loop.close()
    iface._asgi_loop = loop
    iface._asgi_shutdown = asyncio.Event()
    iface._server_thread = None
    iface.detach()


def test_asgi_app_returns_early_on_disconnect():
    import asyncio

    iface = _client_interface()
    app = iface._build_asgi_app()
    iface._handle_tunnel_exchange = MagicMock(
        return_value=(200, "application/octet-stream", b""),
    )

    messages = [
        {"type": "http.request", "body": b"partial", "more_body": True},
        {"type": "http.disconnect"},
    ]
    sent = []

    async def receive():
        return messages.pop(0)

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": "POST", "path": "/", "headers": []}
    asyncio.run(app(scope, receive, send))

    assert sent == []
    iface._handle_tunnel_exchange.assert_not_called()
