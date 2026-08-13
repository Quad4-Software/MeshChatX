# SPDX-License-Identifier: 0BSD

import asyncio
import secrets
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import setup as setup_session
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.config_manager import ConfigManager
from meshchatx.src.backend.http.middleware import create_auth_middleware
from tests.backend.conftest import extend_meshchat_middlewares, fetch_api_csrf_headers


def _make_aio_app(mock_app, use_https: bool):
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


def test_config_password_hash_roundtrip(mock_app):
    mock_app.config.auth_password_hash.set("roundtrip-test-hash")
    assert mock_app.config.auth_password_hash.get() == "roundtrip-test-hash"


def test_config_bcrypt_hash_roundtrip(mock_app):
    mock_app.config.auth_enabled.set(True)
    h = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8")
    mock_app.config.auth_password_hash.set(h)
    assert mock_app.config.auth_password_hash.get() == h


def test_encrypted_cookie_storage_https_flags(mock_app):
    mock_app.session_secret_key = secrets.token_urlsafe(32)
    storage = mock_app._encrypted_cookie_storage(True)
    assert storage.cookie_params["secure"] is True
    assert storage.cookie_params["httponly"] is True
    assert storage.cookie_params["samesite"] == "Lax"


def test_encrypted_cookie_storage_http_flags(mock_app):
    mock_app.session_secret_key = secrets.token_urlsafe(32)
    storage = mock_app._encrypted_cookie_storage(False)
    assert storage.cookie_params["secure"] is False


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_login_sets_cookie_and_allows_protected_api(mock_app):
    mock_app.config.auth_enabled.set(True)
    pw = b"integration-test-password-ok"
    stored_hash = bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")
    mock_app.config.auth_password_hash.set(stored_hash)
    assert isinstance(mock_app.current_context.config, ConfigManager)
    assert mock_app.config.auth_password_hash.get() == stored_hash
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)
        login = await client.post(
            "/api/v1/auth/login",
            json={"password": pw.decode("utf-8")},
            headers=headers,
        )
        assert login.status == 200
        set_cookie = login.headers.get("Set-Cookie", "")
        assert "HttpOnly" in set_cookie
        assert "SameSite=Lax" in set_cookie
        assert "Secure" not in set_cookie

        backups = await client.get("/api/v1/database/backups")
        assert backups.status == 200
        body = await backups.json()
        assert "backups" in body


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_ws_returns_401_without_session_when_auth_enabled(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(b"x", bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        r = await client.get("/ws")
        assert r.status == 401


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_logout_clears_session_for_protected_api(mock_app):
    mock_app.config.auth_enabled.set(True)
    pw = b"logout-test-password-ok"
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)
        await client.post(
            "/api/v1/auth/login",
            json={"password": pw.decode("utf-8")},
            headers=headers,
        )
        assert (await client.get("/api/v1/database/backups")).status == 200

        headers = await fetch_api_csrf_headers(client)
        out = await client.post("/api/v1/auth/logout", headers=headers)
        assert out.status == 200

        assert (await client.get("/api/v1/database/backups")).status == 401


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_auth_login_invalid_json_returns_400(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(b"x", bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)
        r = await client.post(
            "/api/v1/auth/login",
            data="{not-json",
            headers={**headers, "Content-Type": "application/json"},
        )
        assert r.status == 400
        body = await r.json()
        assert "error" in body


@settings(
    max_examples=40,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(body=st.binary(min_size=0, max_size=12000))
@pytest.mark.usefixtures("require_loopback_tcp")
def test_auth_login_fuzz_never_500(mock_app, body):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(b"fixed", bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async def run():
        async with TestClient(TestServer(aio_app)) as client:
            headers = await fetch_api_csrf_headers(client)
            r = await client.post(
                "/api/v1/auth/login",
                data=body,
                headers={**headers, "Content-Type": "application/json"},
            )
            assert r.status != 500

    asyncio.run(run())


def test_reset_password_clears_hash_when_set(mock_app):
    mock_app.config.auth_enabled.set(True)
    h = bcrypt.hashpw(b"old-password", bcrypt.gensalt()).decode("utf-8")
    mock_app.config.auth_password_hash.set(h)
    assert mock_app.reset_password() is True
    assert mock_app.config.auth_password_hash.get() is None


def test_reset_password_no_op_when_no_hash(mock_app):
    mock_app.config.auth_password_hash.set(None)
    assert mock_app.reset_password() is False
    assert mock_app.config.auth_password_hash.get() is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_reset_password_exposes_setup_screen(mock_app):
    mock_app.config.auth_enabled.set(True)
    h = bcrypt.hashpw(b"old-password", bcrypt.gensalt()).decode("utf-8")
    mock_app.config.auth_password_hash.set(h)
    assert mock_app.reset_password() is True

    aio_app = _make_aio_app(mock_app, use_https=False)
    async with TestClient(TestServer(aio_app)) as client:
        status = await client.get("/api/v1/auth/status")
        assert status.status == 200
        body = await status.json()
        assert body["password_set"] is False


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_auth_rejects_api_paths_that_end_with_static_extensions(mock_app):
    """Unauthenticated /api/v1 paths must 401 even when the URL looks like a static file.

    Plugin assets are /api/v1/plugins/{id}/asset/{path} and commonly end in
    .js/.json/.wasm. Those suffixes are public only for non-API static files.
    """
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(b"x", bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        config = await client.get("/api/v1/config")
        assert config.status == 401

        disguised = await client.get("/api/v1/config.json")
        assert disguised.status == 401, (
            f"expected 401 for disguised API path, got {disguised.status}"
        )

        plugin_js = await client.get(
            "/api/v1/plugins/com.meshchatx.mcx-bugs/asset/frontend/main.js",
        )
        assert plugin_js.status == 401, (
            f"expected 401 for plugin JS asset, got {plugin_js.status}"
        )

        plugin_wasm = await client.get(
            "/api/v1/plugins/com.meshchatx.mcx-bugs/asset/backend/main.wasm",
        )
        assert plugin_wasm.status == 401, (
            f"expected 401 for plugin wasm asset, got {plugin_wasm.status}"
        )

        status_prefix = await client.get("/api/v1/status.json")
        assert status_prefix.status == 401, (
            f"expected 401 for status prefix disguise, got {status_prefix.status}"
        )

        manifest = await client.get("/manifest.json")
        assert manifest.status == 200


@pytest.mark.asyncio
async def test_auth_middleware_does_not_treat_api_static_suffixes_as_public():
    """Oracle: password auth still applies when an API path ends in .js/.json/.wasm."""
    app = MagicMock()
    app.auth_enabled = True
    app.current_context = MagicMock(running=True)
    app.identity.hash.hex.return_value = "aa" * 16
    app._startup_stage = "ok"

    handler = AsyncMock(return_value=web.Response(status=200, text="ok"))
    mw = create_auth_middleware(app)
    empty_session = AsyncMock(return_value={})

    async def call(path):
        request = MagicMock()
        request.path = path
        with patch(
            "meshchatx.src.backend.http.middleware.get_session",
            empty_session,
        ):
            return await mw(request, handler)

    for path in (
        "/api/v1/config.json",
        "/api/v1/status.json",
        "/api/v1/plugins/com.meshchatx.mcx-bugs/asset/frontend/main.js",
        "/api/v1/plugins/com.meshchatx.mcx-bugs/asset/backend/main.wasm",
    ):
        handler.reset_mock()
        resp = await call(path)
        assert resp.status == 401, f"{path} expected 401, got {resp.status}"
        handler.assert_not_awaited()

    handler.reset_mock()
    public = await call("/manifest.json")
    assert public.status == 200
    handler.assert_awaited_once()
