# SPDX-License-Identifier: 0BSD

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

pytestmark = pytest.mark.usefixtures("require_loopback_tcp")


def _build_aio_app(app):
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw = app._define_routes(routes)
    aio_app = web.Application(middlewares=[auth_mw, mime_mw, sec_mw])
    aio_app.add_routes(routes)
    return aio_app


@pytest.fixture
def web_audio_app(mock_app):
    app = mock_app
    app.current_context.running = True
    app.config.auth_enabled.set(False)
    return app


@pytest.mark.asyncio
async def test_telephone_audio_ws_disabled_config_returns_error(web_audio_app):
    bridge = MagicMock()
    bridge.config_enabled.return_value = False
    bridge.send_status = AsyncMock()
    bridge.attach_client.return_value = False
    bridge.detach_client = MagicMock()
    bridge.push_client_frame = MagicMock()
    web_audio_app.web_audio_bridge = bridge

    aio_app = _build_aio_app(web_audio_app)
    async with TestClient(TestServer(aio_app)) as client:
        ws = await client.ws_connect("/ws/telephone/audio")
        msg = await ws.receive_json()
        await ws.close()

    assert msg["type"] == "error"
    assert "disabled" in msg["message"].lower()
    bridge.send_status.assert_not_called()
    bridge.detach_client.assert_called_once()


@pytest.mark.asyncio
async def test_telephone_audio_ws_no_active_call_reports_attach_error(web_audio_app):
    async def send_ready(ws):
        await ws.send_str(json.dumps({"type": "web_audio.ready", "frame_ms": 60}))

    bridge = MagicMock()
    bridge.config_enabled.return_value = True
    bridge.send_status = AsyncMock(side_effect=send_ready)
    bridge.attach_client.return_value = False
    bridge.detach_client = MagicMock()
    bridge.push_client_frame = MagicMock()
    web_audio_app.web_audio_bridge = bridge

    aio_app = _build_aio_app(web_audio_app)
    async with TestClient(TestServer(aio_app)) as client:
        ws = await client.ws_connect("/ws/telephone/audio")
        msg1 = await ws.receive_json()
        msg2 = await ws.receive_json()
        await ws.close()

    assert msg1["type"] == "web_audio.ready"
    assert msg2["type"] == "error"
    assert "no active call" in msg2["message"].lower()
    bridge.attach_client.assert_called_once()
    bridge.detach_client.assert_called_once()


@pytest.mark.asyncio
async def test_telephone_audio_ws_ping_and_attach_messages(web_audio_app):
    async def send_ready(ws):
        await ws.send_str(json.dumps({"type": "web_audio.ready", "frame_ms": 60}))

    bridge = MagicMock()
    bridge.config_enabled.return_value = True
    bridge.send_status = AsyncMock(side_effect=send_ready)
    bridge.attach_client.return_value = True
    bridge.detach_client = MagicMock()
    bridge.push_client_frame = MagicMock()
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

    bridge = MagicMock()
    bridge.config_enabled.return_value = True
    bridge.send_status = AsyncMock(side_effect=send_ready)
    bridge.attach_client.return_value = True
    bridge.detach_client = MagicMock()
    bridge.push_client_frame = MagicMock()
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

    bridge = MagicMock()
    bridge.config_enabled.return_value = True
    bridge.send_status = AsyncMock(side_effect=send_ready)
    bridge.attach_client.return_value = True
    bridge.detach_client = MagicMock()
    bridge.push_client_frame = MagicMock()
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
