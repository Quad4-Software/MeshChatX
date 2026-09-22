# SPDX-License-Identifier: 0BSD

"""HTTP contract: POST /api/v1/lxmf-messages/{hash}/cancel must call router cancel."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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
        "meshchatx.src.backend.http.routes.lxmf.convert_db_lxmf_message_to_dict",
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
        message_hash,
    )


@pytest.mark.asyncio
async def test_lxmf_cancel_rejects_invalid_hash(web_cancel_app):
    aio_app = _build_aio_app(web_cancel_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post("/api/v1/lxmf-messages/not-hex!/cancel")
        assert response.status == 400
    web_cancel_app.message_router.cancel_outbound.assert_not_called()


@pytest.mark.asyncio
async def test_lxmf_cancel_reconciles_db_after_restart(web_cancel_app):
    # The router holds no live object after a restart, so a "sending" row
    # would otherwise return 200 while staying stuck forever.
    message_hash = "cc" * 16
    web_cancel_app.database.messages.get_lxmf_message_by_hash.return_value = {
        "hash": message_hash,
        "state": "sending",
        "progress": 12.0,
        "delivery_attempts": 1,
        "next_delivery_attempt_at": None,
    }
    aio_app = _build_aio_app(web_cancel_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(f"/api/v1/lxmf-messages/{message_hash}/cancel")
        assert response.status == 200

    web_cancel_app.database.messages.update_lxmf_message_state.assert_called_once_with(
        message_hash,
        "cancelled",
        12.0,
        1,
        None,
    )


@pytest.mark.asyncio
async def test_lxmf_cancel_attempts_forwarding_routers(web_cancel_app):
    # Forwarded sends queue on per-alias routers, not the main router.
    message_hash = "dd" * 16
    alias_router = MagicMock()
    web_cancel_app.forwarding_manager.forwarding_routers = {
        "alias": alias_router,
    }
    aio_app = _build_aio_app(web_cancel_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(f"/api/v1/lxmf-messages/{message_hash}/cancel")
        assert response.status == 200

    alias_router.cancel_outbound.assert_called_once_with(bytes.fromhex(message_hash))


@pytest.mark.asyncio
async def test_lxmf_cancel_inbound_all_endpoint(web_cancel_app):
    web_cancel_app.message_router.cancel_all_inbound.return_value = 3
    web_cancel_app.message_router.inbound_resources.return_value = []
    aio_app = _build_aio_app(web_cancel_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(
            "/api/v1/lxmf/propagation-node/cancel-inbound",
            json={},
        )
        assert response.status == 200
        body = await response.json()
        assert body["cancelled"] == 3
        assert body["inbound_delivery_count"] == 0

    web_cancel_app.message_router.cancel_all_inbound.assert_called_once_with()


@pytest.mark.asyncio
async def test_lxmf_cancel_inbound_one_endpoint(web_cancel_app):
    resource_hash = "ee" * 16
    web_cancel_app.message_router.cancel_inbound.return_value = True
    web_cancel_app.message_router.inbound_resources.return_value = []
    aio_app = _build_aio_app(web_cancel_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(
            "/api/v1/lxmf/propagation-node/cancel-inbound",
            json={"resource_hash": resource_hash},
        )
        assert response.status == 200
        body = await response.json()
        assert body["cancelled"] == 1
        assert body["resource_hash"] == resource_hash

    web_cancel_app.message_router.cancel_inbound.assert_called_once_with(
        bytes.fromhex(resource_hash),
    )
