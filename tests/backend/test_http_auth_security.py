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
    password = b"old-password"
    h = bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8")
    mock_app.config.auth_password_hash.set(h)

    aio_app = _make_aio_app(mock_app, use_https=False)
    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)
        login = await client.post(
            "/api/v1/auth/login",
            json={"password": password.decode("utf-8")},
            headers=headers,
        )
        assert login.status == 200
        status_before_reset = await (await client.get("/api/v1/auth/status")).json()
        assert status_before_reset["authenticated"] is True

        assert mock_app.reset_password() is True
        status = await client.get("/api/v1/auth/status")
        assert status.status == 200
        body = await status.json()
        assert body["password_set"] is False
        assert body["authenticated"] is False
        assert (await client.get("/api/v1/database/backups")).status == 401


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
            "/api/v1/plugins/com.meshchatx.mcx-hello/asset/frontend/main.js",
        )
        assert plugin_js.status == 401, (
            f"expected 401 for plugin JS asset, got {plugin_js.status}"
        )

        plugin_wasm = await client.get(
            "/api/v1/plugins/com.meshchatx.mcx-hello/asset/backend/main.wasm",
        )
        assert plugin_wasm.status == 401, (
            f"expected 401 for plugin wasm asset, got {plugin_wasm.status}"
        )

        status_prefix = await client.get("/api/v1/status.json")
        assert status_prefix.status == 401, (
            f"expected 401 for status prefix disguise, got {status_prefix.status}"
        )

        # Do not GET /manifest.json here. That route uses FileResponse, which
        # calls loop.run_in_executor. mock_app patches threading.Thread so the
        # executor never runs and the client hangs until TimeoutError.
        # A missing static asset is enough: middleware must not 401 it.
        static_js = await client.get("/assets/does-not-exist.js")
        assert static_js.status != 401, (
            f"expected static non-API path to skip auth, got {static_js.status}"
        )


@pytest.mark.asyncio
async def test_auth_middleware_does_not_treat_api_static_suffixes_as_public():
    """Reference: password auth still applies when an API path ends in .js/.json/.wasm."""
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
        "/api/v1/plugins/com.meshchatx.mcx-hello/asset/frontend/main.js",
        "/api/v1/plugins/com.meshchatx.mcx-hello/asset/backend/main.wasm",
    ):
        handler.reset_mock()
        resp = await call(path)
        assert resp.status == 401, f"{path} expected 401, got {resp.status}"
        handler.assert_not_awaited()

    handler.reset_mock()
    public = await call("/manifest.json")
    assert public.status == 200
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_auth_middleware_gates_docs_routes_when_enabled():
    """Docs routes serve user-uploaded content and must require auth."""
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
        "/reticulum-docs/guide.html",
        "/reticulum-docs/logo.png",
        "/meshchatx-docs/manual.md",
        "/meshchatx-docs/style.css",
    ):
        handler.reset_mock()
        resp = await call(path)
        assert resp.status == 401, f"{path} expected 401, got {resp.status}"
        handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_auth_middleware_docs_routes_public_when_auth_disabled():
    app = MagicMock()
    app.auth_enabled = False
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

    for path in ("/reticulum-docs/guide.html", "/meshchatx-docs/manual.md"):
        handler.reset_mock()
        resp = await call(path)
        assert resp.status == 200, f"{path} expected 200, got {resp.status}"
        handler.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_auth_login_rejects_non_string_password(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(b"x", bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)
        r = await client.post(
            "/api/v1/auth/login",
            json={"password": 12345},
            headers=headers,
        )
        assert r.status == 400


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_auth_login_rejects_password_over_bcrypt_limit(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(b"x", bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)
        r = await client.post(
            "/api/v1/auth/login",
            json={"password": "a" * 100},
            headers=headers,
        )
        assert r.status == 400


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_auth_setup_rejects_non_string_password(mock_app):
    mock_app.config.auth_enabled.set(True)
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)
        r = await client.post(
            "/api/v1/auth/setup",
            json={"password": 12345},
            headers=headers,
        )
        assert r.status == 400
        r = await client.post(
            "/api/v1/auth/setup",
            json={"password": "a" * 100},
            headers=headers,
        )
        assert r.status == 400


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_logout_bumps_auth_session_epoch(mock_app):
    mock_app.config.auth_enabled.set(True)
    pw = b"epoch-test-password-ok"
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
        epoch_before = mock_app._current_auth_session_epoch()

        headers = await fetch_api_csrf_headers(client)
        out = await client.post("/api/v1/auth/logout", headers=headers)
        assert out.status == 200

        assert mock_app._current_auth_session_epoch() == epoch_before + 1


@pytest.mark.asyncio
async def test_auth_middleware_returns_503_when_identity_is_none():
    app = MagicMock()
    app.auth_enabled = True
    app.current_context = MagicMock(running=True)
    app.identity = None
    app._startup_stage = "identity-swap"

    handler = AsyncMock(return_value=web.Response(status=200, text="ok"))
    mw = create_auth_middleware(app)
    authed_session = AsyncMock(
        return_value={"authenticated": True, "identity_hash": "aa" * 16},
    )

    request = MagicMock()
    request.path = "/api/v1/config"
    with patch(
        "meshchatx.src.backend.http.middleware.get_session",
        authed_session,
    ):
        resp = await mw(request, handler)

    assert resp.status == 503
    handler.assert_not_awaited()


def test_insecure_remote_access_flag(tmp_path, monkeypatch):
    from meshchatx.src.backend.http.routes.app_info import insecure_remote_access

    monkeypatch.delenv("MESHCHAT_TRUSTED_PROXIES", raising=False)
    app = MagicMock()
    app.auth_enabled = False
    app.storage_dir = str(tmp_path)

    def req(remote, xff=None):
        r = MagicMock()
        r.remote = remote
        r.headers = {"X-Forwarded-For": xff} if xff else {}
        return r

    assert insecure_remote_access(app, req("127.0.0.1")) is False
    assert insecure_remote_access(app, req("127.0.0.2")) is False
    assert insecure_remote_access(app, req("::1")) is False
    assert insecure_remote_access(app, req("192.168.1.20")) is True
    assert insecure_remote_access(app, req("10.0.0.5")) is True

    app.auth_enabled = True
    assert insecure_remote_access(app, req("192.168.1.20")) is False
    app.auth_enabled = False

    # X-Forwarded-For is ignored unless the immediate peer is a trusted proxy.
    assert insecure_remote_access(app, req("127.0.0.1", "8.8.8.8")) is False

    monkeypatch.setenv("MESHCHAT_TRUSTED_PROXIES", "127.0.0.1")
    assert insecure_remote_access(app, req("127.0.0.1", "8.8.8.8")) is True
    # A multi-hop chain resolves to the rightmost untrusted entry.
    assert (
        insecure_remote_access(app, req("127.0.0.1", "203.0.113.9, 127.0.0.1")) is True
    )
    # A chain of only trusted hops collapses back to the loopback peer.
    assert insecure_remote_access(app, req("127.0.0.1", "127.0.0.1")) is False


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_unauthenticated_logout_does_not_bump_session_epoch(mock_app):
    mock_app.config.auth_enabled.set(True)
    pw = b"epoch-guard-password-ok"
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    server = TestServer(aio_app)
    async with TestClient(server) as client_a:
        headers = await fetch_api_csrf_headers(client_a)
        login = await client_a.post(
            "/api/v1/auth/login",
            json={"password": pw.decode("utf-8")},
            headers=headers,
        )
        assert login.status == 200

        async with TestClient(server) as client_b:
            headers_b = await fetch_api_csrf_headers(client_b)
            epoch_before = mock_app._current_auth_session_epoch()
            out = await client_b.post("/api/v1/auth/logout", headers=headers_b)
            assert out.status == 200
            assert mock_app._current_auth_session_epoch() == epoch_before

            assert (await client_a.get("/api/v1/database/backups")).status == 200


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_translation_packs_requires_auth_when_enabled(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(b"x", bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        r = await client.get("/translation-packs/registry.json")
        assert r.status == 401
