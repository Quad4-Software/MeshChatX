# SPDX-License-Identifier: 0BSD

import asyncio
import secrets

import bcrypt
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import setup as setup_session
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.config_manager import ConfigManager


def _make_aio_app(mock_app, use_https: bool):
    mock_app.session_secret_key = secrets.token_urlsafe(32)
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw = mock_app._define_routes(routes)
    aio_app = web.Application()
    setup_session(aio_app, mock_app._encrypted_cookie_storage(use_https))
    aio_app.middlewares.extend([auth_mw, mime_mw, sec_mw])
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
async def test_login_sets_cookie_and_allows_protected_api(mock_app):
    mock_app.config.auth_enabled.set(True)
    pw = b"integration-test-password-ok"
    stored_hash = bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")
    mock_app.config.auth_password_hash.set(stored_hash)
    assert isinstance(mock_app.current_context.config, ConfigManager)
    assert mock_app.config.auth_password_hash.get() == stored_hash
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"password": pw.decode("utf-8")},
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
async def test_logout_clears_session_for_protected_api(mock_app):
    mock_app.config.auth_enabled.set(True)
    pw = b"logout-test-password-ok"
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        await client.post("/api/v1/auth/login", json={"password": pw.decode("utf-8")})
        assert (await client.get("/api/v1/database/backups")).status == 200

        out = await client.post("/api/v1/auth/logout")
        assert out.status == 200

        assert (await client.get("/api/v1/database/backups")).status == 401


@pytest.mark.asyncio
async def test_auth_login_invalid_json_returns_400(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(b"x", bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        r = await client.post(
            "/api/v1/auth/login",
            data="{not-json",
            headers={"Content-Type": "application/json"},
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
def test_auth_login_fuzz_never_500(mock_app, body):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(b"fixed", bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async def run():
        async with TestClient(TestServer(aio_app)) as client:
            r = await client.post(
                "/api/v1/auth/login",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            assert r.status != 500

    asyncio.run(run())
