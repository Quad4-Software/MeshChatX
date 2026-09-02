# SPDX-License-Identifier: 0BSD

"""HTTP oracles for LXMF stamp-info destination route."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.http.routes.messages import register_messages_routes


@pytest.fixture
def stamp_app(mock_app):
    mock_app.message_router = MagicMock()
    mock_app.message_router.get_outbound_ticket_expiry.return_value = None
    return mock_app


async def _get_json(app, path: str):
    routes = web.RouteTableDef()
    register_messages_routes(routes, app)
    aio = web.Application()
    aio.add_routes(routes)
    async with TestClient(TestServer(aio)) as client:
        resp = await client.get(path)
        body = await resp.json()
        return resp.status, body


@pytest.mark.asyncio
async def test_lxmf_stamp_info_rejects_non_hex(stamp_app):
    status, body = await _get_json(
        stamp_app,
        "/api/v1/destination/not-hex/lxmf-stamp-info",
    )
    assert status == 400
    assert "invalid" in body.get("message", "").lower()


@pytest.mark.asyncio
async def test_lxmf_stamp_info_accepts_hex(stamp_app):
    dest = "ab" * 16
    with patch.object(
        stamp_app.database.announces,
        "get_announce_by_hash",
        return_value=None,
    ):
        status, body = await _get_json(
            stamp_app,
            f"/api/v1/destination/{dest}/lxmf-stamp-info",
        )
    assert status == 200
    assert body["lxmf_stamp_info"]["stamp_cost"] is None
    stamp_app.message_router.get_outbound_ticket_expiry.assert_called_once()
