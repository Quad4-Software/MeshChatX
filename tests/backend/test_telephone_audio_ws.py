# SPDX-License-Identifier: 0BSD

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

pytestmark = pytest.mark.usefixtures("require_loopback_tcp")


def _build_aio_app(app):
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw = app._define_routes(routes)
    aio_app = web.Application(middlewares=[auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw])
    aio_app.add_routes(routes)
    return aio_app


@pytest.fixture
def web_audio_app(mock_app):
    app = mock_app
    app.current_context.running = True
    app.config.auth_enabled.set(False)
    return app


def _bridge_with_clients(*, config_enabled=True, attach_ok=True, send_ready=None):
    """Build a bridge mock whose clients set matches real attach/detach semantics."""
    clients = set()

    def attach_client(ws):
        if not attach_ok:
            return False
        clients.add(ws)
        return True

    def detach_client(ws):
        clients.discard(ws)

    bridge = MagicMock()
    bridge.clients = clients
    bridge.config_enabled.return_value = config_enabled
    bridge.send_status = (
        AsyncMock(side_effect=send_ready) if send_ready else AsyncMock()
    )
    bridge.attach_client.side_effect = attach_client
    bridge.detach_client.side_effect = detach_client
    bridge.push_client_frame = MagicMock()
    return bridge


@pytest.mark.asyncio
async def test_telephone_audio_ws_disabled_config_returns_error(
    web_audio_app,
    monkeypatch,
):
    monkeypatch.setattr(web_audio_app, "web_audio_required", lambda: False)

    bridge = _bridge_with_clients(config_enabled=False, attach_ok=False)
    web_audio_app.web_audio_bridge = bridge

    aio_app = _build_aio_app(web_audio_app)
    async with TestClient(TestServer(aio_app)) as client:
        ws = await client.ws_connect("/ws/telephone/audio")
        msg = await ws.receive_json()
        await ws.close()

    assert msg["type"] == "error"
    assert "disabled" in msg["message"].lower()
    bridge.send_status.assert_not_called()
    # Early close: never attached, so detach is not required.
    bridge.detach_client.assert_not_called()


@pytest.mark.asyncio
async def test_telephone_audio_ws_allowed_on_chaquopy_when_config_disabled(
    web_audio_app,
    monkeypatch,
):
    monkeypatch.setattr("meshchatx.meshchat._is_chaquopy_android", lambda: True)

    async def send_ready(ws):
        await ws.send_str(json.dumps({"type": "web_audio.ready", "frame_ms": 60}))

    bridge = _bridge_with_clients(
        config_enabled=False,
        attach_ok=False,
        send_ready=send_ready,
    )
    web_audio_app.web_audio_bridge = bridge

    aio_app = _build_aio_app(web_audio_app)
    async with TestClient(TestServer(aio_app)) as client:
        ws = await client.ws_connect("/ws/telephone/audio")
        msg1 = await ws.receive_json()
        msg2 = await ws.receive_json()
        await ws.close()

    assert msg1["type"] == "web_audio.ready"
    assert msg2["type"] == "error"
    assert "disabled" not in msg2.get("message", "").lower()
    bridge.send_status.assert_called_once()
    bridge.detach_client.assert_called_once()


@pytest.mark.asyncio
async def test_telephone_audio_ws_no_active_call_reports_attach_error(web_audio_app):
    async def send_ready(ws):
        await ws.send_str(json.dumps({"type": "web_audio.ready", "frame_ms": 60}))

    bridge = _bridge_with_clients(attach_ok=False, send_ready=send_ready)
    web_audio_app.web_audio_bridge = bridge

    aio_app = _build_aio_app(web_audio_app)
    async with TestClient(TestServer(aio_app)) as client:
        ws = await client.ws_connect("/ws/telephone/audio")
        msg1 = await ws.receive_json()
        msg2 = await ws.receive_json()
        await ws.send_bytes(b"\x01\x02\x03")
        await ws.close()

    assert msg1["type"] == "web_audio.ready"
    assert msg2["type"] == "error"
    assert "no active call" in msg2["message"].lower()
    bridge.attach_client.assert_called_once()
    bridge.detach_client.assert_called_once()
    bridge.push_client_frame.assert_not_called()


@pytest.mark.asyncio
async def test_telephone_audio_ws_ping_and_attach_messages(web_audio_app):
    async def send_ready(ws):
        await ws.send_str(json.dumps({"type": "web_audio.ready", "frame_ms": 60}))

    bridge = _bridge_with_clients(send_ready=send_ready)
    web_audio_app.web_audio_bridge = bridge

    aio_app = _build_aio_app(web_audio_app)
    async with TestClient(TestServer(aio_app)) as client:
        ws = await client.ws_connect("/ws/telephone/audio")
        _ready = await ws.receive_json()
        await ws.send_json({"type": "attach"})
        await ws.send_json({"type": "ping"})
        pong = await ws.receive_json()
        await ws.close()

    assert pong["type"] == "pong"
    # One attach during open + one on explicit attach message
    assert bridge.attach_client.call_count == 2
    bridge.detach_client.assert_called_once()


@pytest.mark.asyncio
async def test_telephone_audio_ws_binary_messages_forward_frames(web_audio_app):
    async def send_ready(ws):
        await ws.send_str(json.dumps({"type": "web_audio.ready", "frame_ms": 60}))

    bridge = _bridge_with_clients(send_ready=send_ready)
    web_audio_app.web_audio_bridge = bridge

    aio_app = _build_aio_app(web_audio_app)
    async with TestClient(TestServer(aio_app)) as client:
        ws = await client.ws_connect("/ws/telephone/audio")
        _ready = await ws.receive_json()
        await ws.send_bytes(b"\x01\x02\x03")
        await ws.close()

    bridge.push_client_frame.assert_called_once_with(b"\x01\x02\x03")
    bridge.detach_client.assert_called_once()


@pytest.mark.asyncio
async def test_telephone_audio_ws_bad_json_does_not_crash_handler(web_audio_app):
    async def send_ready(ws):
        await ws.send_str(json.dumps({"type": "web_audio.ready", "frame_ms": 60}))

    bridge = _bridge_with_clients(send_ready=send_ready)
    web_audio_app.web_audio_bridge = bridge

    aio_app = _build_aio_app(web_audio_app)
    async with TestClient(TestServer(aio_app)) as client:
        ws = await client.ws_connect("/ws/telephone/audio")
        _ready = await ws.receive_json()
        await ws.send_str("{not-valid-json")
        await ws.send_json({"type": "ping"})
        pong = await ws.receive_json()
        await ws.close()

    assert pong["type"] == "pong"
    bridge.detach_client.assert_called_once()
