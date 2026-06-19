# SPDX-License-Identifier: 0BSD

"""HTTP contract: POST /api/v1/lxmf-messages/{hash}/cancel must call router cancel."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


def _build_aio_app(app):
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw = app._define_routes(routes)
    aio_app = web.Application(middlewares=[auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw])
    aio_app.add_routes(routes)
    return aio_app


@pytest.fixture
def web_cancel_app(mock_app):
    mock_app.current_context.running = True
    mock_app.config.auth_enabled.set(False)
    mock_app.message_router = MagicMock()
    mock_app.database.messages = MagicMock()
    mock_app.database.messages.get_lxmf_message_by_hash.return_value = {
        "hash": "aa" * 16,
        "state": "cancelled",
    }
    with patch(
        "meshchatx.meshchat.convert_db_lxmf_message_to_dict",
        side_effect=lambda row: row,
    ):
        yield mock_app


@pytest.mark.asyncio
async def test_lxmf_cancel_endpoint_calls_message_router(web_cancel_app):
    message_hash = "aa" * 16
    aio_app = _build_aio_app(web_cancel_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(f"/api/v1/lxmf-messages/{message_hash}/cancel")
        assert response.status == 200
        body = await response.json()
        assert body["message"] == "ok"
        assert body["lxmf_message"] is not None

    web_cancel_app.message_router.cancel_outbound.assert_called_once()
    called_hash = web_cancel_app.message_router.cancel_outbound.call_args[0][0]
    assert called_hash == bytes.fromhex(message_hash)


@pytest.mark.asyncio
async def test_lxmf_cancel_endpoint_loads_updated_message_from_database(web_cancel_app):
    message_hash = "bb" * 16
    web_cancel_app.database.messages.get_lxmf_message_by_hash.return_value = {
        "hash": message_hash,
        "state": "cancelled",
        "content": "stopped",
    }
    aio_app = _build_aio_app(web_cancel_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(f"/api/v1/lxmf-messages/{message_hash}/cancel")
        assert response.status == 200
        body = await response.json()
        assert body["lxmf_message"]["state"] == "cancelled"

    web_cancel_app.database.messages.get_lxmf_message_by_hash.assert_called_with(
        message_hash
    )
