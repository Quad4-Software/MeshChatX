# SPDX-License-Identifier: 0BSD

"""HTTP tests for POST /api/v1/identities/switch (hotswap response shape, guards)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

pytestmark = pytest.mark.usefixtures("require_loopback_tcp")


def _build_aio_app(app):
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw, demo_mw = app._define_routes(routes)
    aio_app = web.Application(
        middlewares=[auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw, demo_mw]
    )
    aio_app.add_routes(routes)
    return aio_app


@pytest.fixture
def web_identity_app(mock_app):
    mock_app.current_context.running = True
    mock_app.config.auth_enabled.set(False)
    return mock_app


@pytest.mark.asyncio
async def test_post_identities_switch_hotswap_response_includes_hash_and_display_name(
    web_identity_app,
):
    web_identity_app.hotswap_identity = AsyncMock(return_value=True)
    expected_display = web_identity_app.config.display_name.get()
    identity_hash = "ab" * 16

    aio_app = _build_aio_app(web_identity_app)
    body = {"identity_hash": identity_hash, "keep_alive": False}
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post("/api/v1/identities/switch", json=body)
        assert r.status == 200
        data = await r.json()
    assert data["hotswapped"] is True
    assert data["identity_hash"] == identity_hash
    assert data["display_name"] == expected_display
    assert "message" in data
    web_identity_app.hotswap_identity.assert_awaited_once_with(
        identity_hash,
        keep_alive=False,
    )


@pytest.mark.asyncio
async def test_post_identities_switch_rejects_non_hex_hash(web_identity_app):
    web_identity_app.hotswap_identity = AsyncMock(return_value=True)
    aio_app = _build_aio_app(web_identity_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post(
            "/api/v1/identities/switch",
            json={"identity_hash": "../../tmp/evil", "keep_alive": False},
        )
        assert r.status == 400
        body = await r.json()
    assert "Invalid identity hash" in (body.get("message") or "")
    web_identity_app.hotswap_identity.assert_not_called()


@pytest.mark.asyncio
async def test_post_identities_switch_passes_keep_alive(web_identity_app):
    web_identity_app.hotswap_identity = AsyncMock(return_value=True)
    identity_hash = "cd" * 16
    aio_app = _build_aio_app(web_identity_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post(
            "/api/v1/identities/switch",
            json={"identity_hash": identity_hash, "keep_alive": True},
        )
        assert r.status == 200
    web_identity_app.hotswap_identity.assert_awaited_once_with(
        identity_hash,
        keep_alive=True,
    )


@pytest.mark.asyncio
async def test_post_identities_switch_503_when_not_running(web_identity_app):
    web_identity_app.current_context.running = False
    web_identity_app.hotswap_identity = AsyncMock(return_value=True)
    aio_app = _build_aio_app(web_identity_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post(
            "/api/v1/identities/switch",
            json={"identity_hash": "ef" * 16},
        )
        assert r.status == 503
    web_identity_app.hotswap_identity.assert_not_called()


@pytest.mark.asyncio
async def test_post_identities_switch_hotswap_false_missing_identity_returns_500(
    web_identity_app,
):
    web_identity_app.hotswap_identity = AsyncMock(return_value=False)
    aio_app = _build_aio_app(web_identity_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post(
            "/api/v1/identities/switch",
            json={"identity_hash": "11" * 16},
        )
        assert r.status == 500
        body = await r.json()
    assert "Failed to switch identity" in (body.get("message") or "")


@pytest.mark.asyncio
async def test_post_identities_switch_concurrent_posts_each_invoke_hotswap(
    web_identity_app,
):
    """Two overlapping switch requests should both complete (no dropped handler)."""
    calls = {"n": 0}

    async def slow_hotswap(identity_hash, keep_alive=False):
        calls["n"] += 1
        await asyncio.sleep(0.02)
        return True

    web_identity_app.hotswap_identity = slow_hotswap
    aio_app = _build_aio_app(web_identity_app)
    hash_a = "22" * 16
    hash_b = "33" * 16

    async with TestClient(TestServer(aio_app)) as client:
        results = await asyncio.gather(
            client.post(
                "/api/v1/identities/switch",
                json={"identity_hash": hash_a},
            ),
            client.post(
                "/api/v1/identities/switch",
                json={"identity_hash": hash_b},
            ),
        )
        assert all(resp.status == 200 for resp in results)
        bodies = [await resp.json() for resp in results]
    assert all(b.get("hotswapped") is True for b in bodies)
    hashes = {b.get("identity_hash") for b in bodies}
    assert hashes == {hash_a, hash_b}
    assert calls["n"] == 2
