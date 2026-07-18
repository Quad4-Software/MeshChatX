# SPDX-License-Identifier: 0BSD
"""AuthSurfacePack: mutating HTTP without CSRF must die; with CSRF must pass."""

from __future__ import annotations

import secrets

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import setup as setup_session

from tests.backend.conftest import extend_meshchat_middlewares, fetch_api_csrf_headers
from tests.backend.eect.asserts import assert_no_unexpected_http_500
from tests.backend.eect.harness import eect_scenario

pytestmark = [
    pytest.mark.eect,
    pytest.mark.usefixtures("require_loopback_tcp"),
]

# Curated mutating surfaces that accept empty/minimal bodies without deep state.
_MUTATING_SAMPLES = (
    ("PATCH", "/api/v1/server/security", {"web_ui_ip_allowlist": ""}),
    ("POST", "/api/v1/app/tutorial/seen", {}),
    ("POST", "/api/v1/app/changelog/seen", {"version": "999.999.999"}),
)


def _make_aio_app(mock_app, use_https: bool = False):
    mock_app.session_secret_key = secrets.token_urlsafe(32)
    mock_app.listen_host = "127.0.0.1"
    mock_app.listen_port = 8000
    mock_app.use_https = use_https
    mock_app.landlock_active = False
    routes = web.RouteTableDef()
    middlewares = mock_app._define_routes(routes)
    aio_app = web.Application()
    setup_session(aio_app, mock_app._encrypted_cookie_storage(use_https))
    extend_meshchat_middlewares(aio_app, middlewares)
    aio_app.add_routes(routes)
    return aio_app


@pytest.mark.asyncio
async def test_eect_mutating_without_csrf_rejected(mock_app, monkeypatch):
    with eect_scenario("auth.csrf.mutating_without_token") as (_s, _seed, rng):
        monkeypatch.delenv("MESHCHAT_DISABLE_CSRF", raising=False)
        aio_app = _make_aio_app(mock_app)
        samples = list(_MUTATING_SAMPLES)
        rng.shuffle(samples)
        async with TestClient(TestServer(aio_app)) as client:
            for method, path, body in samples:
                if method == "PATCH":
                    resp = await client.patch(path, json=body)
                else:
                    resp = await client.post(path, json=body)
                assert_no_unexpected_http_500(resp.status, await resp.text())
                assert resp.status == 403, (
                    f"{method} {path} expected 403 got {resp.status}"
                )


@pytest.mark.asyncio
async def test_eect_mutating_with_csrf_accepted(mock_app, monkeypatch):
    with eect_scenario("auth.csrf.mutating_with_token") as (_s, _seed, rng):
        monkeypatch.delenv("MESHCHAT_DISABLE_CSRF", raising=False)
        aio_app = _make_aio_app(mock_app)
        samples = list(_MUTATING_SAMPLES)
        rng.shuffle(samples)
        async with TestClient(TestServer(aio_app)) as client:
            headers = await fetch_api_csrf_headers(client)
            for method, path, body in samples:
                if method == "PATCH":
                    resp = await client.patch(path, json=body, headers=headers)
                else:
                    resp = await client.post(path, json=body, headers=headers)
                body_text = await resp.text()
                assert_no_unexpected_http_500(resp.status, body_text)
                assert resp.status != 403, f"{method} {path} still CSRF-blocked"
                assert resp.status < 500
