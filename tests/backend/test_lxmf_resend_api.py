# SPDX-License-Identifier: 0BSD

"""HTTP contract: POST /api/v1/lxmf-messages/{hash}/resend preserves stored fields."""

from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


def _build_aio_app(app):
    routes = web.RouteTableDef()
    bad_mw, sqlite_mw, auth_mw, mime_mw, _cache_mw, sec_mw, csrf_mw, ip_mw, demo_mw = (
        app._define_routes(routes)
    )
    aio_app = web.Application(
        middlewares=[
            bad_mw,
            sqlite_mw,
            auth_mw,
            mime_mw,
            _cache_mw,
            sec_mw,
            csrf_mw,
            ip_mw,
            demo_mw,
        ],
    )
    aio_app.add_routes(routes)
    return aio_app


def _stored_row(message_hash, fields):
    return {
        "hash": message_hash,
        "is_incoming": 0,
        "state": "failed",
        "method": "direct",
        "destination_hash": "ab" * 16,
        "title": "kept title",
        "content": "kept body",
        "reply_to_hash": "cd" * 16,
        "fields": json.dumps(fields),
        "progress": 0.0,
        "delivery_attempts": 2,
        "next_delivery_attempt_at": None,
    }


@pytest.fixture
def web_resend_app(mock_app):
    mock_app.current_context.running = True
    mock_app.config.auth_enabled.set(False)
    mock_app.demo_mode = False
    mock_app.message_router = MagicMock()
    mock_app.database.messages = MagicMock()
    mock_app.send_message = AsyncMock(return_value=MagicMock())
    mock_app.websocket_broadcast = AsyncMock()
    mock_app._is_self_lxmf_destination = MagicMock(return_value=False)
    with patch(
        "meshchatx.src.backend.http.routes.lxmf.convert_lxmf_message_to_dict",
        return_value={"hash": "new"},
    ):
        yield mock_app


@pytest.mark.asyncio
async def test_resend_preserves_title_quote_reaction_and_extensions(web_resend_app):
    message_hash = "aa" * 16
    fields = {
        "reply_quoted_content": "quoted text",
        "reaction": {"reaction_to": "ef" * 16, "reaction_content": "👍"},
        "app_extensions": {"custom": {"k": 1}},
    }
    web_resend_app.database.messages.get_lxmf_message_by_hash.return_value = (
        _stored_row(message_hash, fields)
    )
    aio_app = _build_aio_app(web_resend_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(f"/api/v1/lxmf-messages/{message_hash}/resend")
        assert response.status == 200

    kwargs = web_resend_app.send_message.call_args.kwargs
    assert kwargs["title"] == "kept title"
    assert kwargs["content"] == "kept body"
    assert kwargs["reply_to_hash"] == "cd" * 16
    assert kwargs["reply_quoted_content"] == "quoted text"
    assert kwargs["reaction_to_hash"] == "ef" * 16
    assert kwargs["reaction_emoji"] == "👍"
    assert kwargs["app_extensions"] == {"custom": {"k": 1}}
    assert kwargs["delivery_method"] == "direct"


@pytest.mark.asyncio
async def test_resend_rebuilds_telemetry_parts(web_resend_app):
    message_hash = "bb" * 16
    fields = {
        "telemetry": {
            "time": {"utc": 1720000000},
            "location": {
                "latitude": 1.5,
                "longitude": 2.5,
                "altitude": 0,
                "speed": 0,
                "bearing": 0,
                "accuracy": 0,
                "last_update": 1720000000,
            },
            "battery": {"charge_percent": 88, "charging": False},
        },
    }
    web_resend_app.database.messages.get_lxmf_message_by_hash.return_value = (
        _stored_row(message_hash, fields)
    )
    aio_app = _build_aio_app(web_resend_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(f"/api/v1/lxmf-messages/{message_hash}/resend")
        assert response.status == 200

    telemetry = web_resend_app.send_message.call_args.kwargs["telemetry_data"]
    assert telemetry is not None
    # Packed telemeter blob must decode back to the same sensors, not nest the
    # whole dict under location as the previous conversion did.
    from meshchatx.src.backend.telemetry_utils import Telemeter

    unpacked = Telemeter.from_packed(telemetry)
    assert unpacked["location"]["latitude"] == pytest.approx(1.5)
    assert unpacked["battery"]["charge_percent"] == pytest.approx(88)


@pytest.mark.asyncio
async def test_resend_rebuilds_image_attachment(web_resend_app):
    # Minimal PNG magic plus payload survives the format sniff.
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    message_hash = "cc" * 16
    fields = {
        "image": {
            "image_type": "png",
            "image_bytes": base64.b64encode(png_bytes).decode(),
        },
    }
    web_resend_app.database.messages.get_lxmf_message_by_hash.return_value = (
        _stored_row(message_hash, fields)
    )
    aio_app = _build_aio_app(web_resend_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(f"/api/v1/lxmf-messages/{message_hash}/resend")
        assert response.status == 200

    image_field = web_resend_app.send_message.call_args.kwargs["image_field"]
    assert image_field is not None
    assert image_field.image_bytes == png_bytes


@pytest.mark.asyncio
async def test_resend_broadcasts_deleted_row(web_resend_app):
    message_hash = "dd" * 16
    web_resend_app.database.messages.get_lxmf_message_by_hash.return_value = (
        _stored_row(message_hash, {})
    )
    aio_app = _build_aio_app(web_resend_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(f"/api/v1/lxmf-messages/{message_hash}/resend")
        assert response.status == 200

    web_resend_app.database.messages.delete_lxmf_message_by_hash.assert_called_once_with(
        message_hash,
    )
    broadcasted = json.loads(web_resend_app.websocket_broadcast.call_args[0][0])
    assert broadcasted == {"type": "lxmf_message_deleted", "hash": message_hash}


@pytest.mark.asyncio
async def test_resend_rejects_incoming_and_active(web_resend_app):
    incoming = _stored_row("ee" * 16, {})
    incoming["is_incoming"] = 1
    web_resend_app.database.messages.get_lxmf_message_by_hash.return_value = incoming
    aio_app = _build_aio_app(web_resend_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(f"/api/v1/lxmf-messages/{'ee' * 16}/resend")
        assert response.status == 400

    active = _stored_row("ff" * 16, {})
    active["state"] = "sending"
    web_resend_app.database.messages.get_lxmf_message_by_hash.return_value = active
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(f"/api/v1/lxmf-messages/{'ff' * 16}/resend")
        assert response.status == 409
    web_resend_app.send_message.assert_not_called()
