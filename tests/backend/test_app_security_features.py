# SPDX-License-Identifier: 0BSD

import secrets

import bcrypt
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import setup as setup_session

from meshchatx.src.backend.app_security_settings import save_app_security_settings
from meshchatx.src.backend.ip_allowlist import (
    client_ip_allowed,
    parse_allowlist_networks,
)
from meshchatx.src.backend.privacy_mode import (
    OutboundHttpBlockedError,
    privacy_mode_enabled,
)
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


def test_ip_allowlist_parsing():
    nets = parse_allowlist_networks("127.0.0.1/32, 192.168.1.0/24")
    assert len(nets) == 2
    assert client_ip_allowed("127.0.0.1", "127.0.0.1/32")
    assert not client_ip_allowed("10.0.0.5", "127.0.0.1/32")
    assert client_ip_allowed("192.168.1.50", "192.168.1.0/24")


def test_ip_allowlist_empty_allows_all():
    assert client_ip_allowed("203.0.113.1", "")


def test_app_security_settings_roundtrip(tmp_path):
    saved = save_app_security_settings(
        str(tmp_path),
        {"web_ui_ip_allowlist": "127.0.0.1/32, ::1/128"},
    )
    assert saved["web_ui_ip_allowlist"] == "127.0.0.1/32, ::1/128"


def test_privacy_mode_default_off(mock_app):
    assert privacy_mode_enabled(mock_app.config) is False


def test_privacy_mode_blocks_outbound(mock_app):
    mock_app.config.privacy_mode_enabled.set(True)
    with pytest.raises(OutboundHttpBlockedError):
        mock_app._require_outbound_http("test")


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_ip_allowlist_middleware_blocks_api(mock_app):
    save_app_security_settings(
        mock_app.storage_dir,
        {"web_ui_ip_allowlist": "192.168.50.0/24"},
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        r = await client.get("/api/v1/config")
        assert r.status == 403


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_csrf_required_for_config_patch(mock_app, monkeypatch):
    monkeypatch.delenv("MESHCHAT_DISABLE_CSRF", raising=False)
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        blocked = await client.patch(
            "/api/v1/server/security", json={"web_ui_ip_allowlist": ""}
        )
        assert blocked.status == 403
        headers = await fetch_api_csrf_headers(client)
        ok = await client.patch(
            "/api/v1/server/security",
            json={"web_ui_ip_allowlist": ""},
            headers=headers,
        )
        assert ok.status == 200


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_login_requires_csrf(mock_app, monkeypatch):
    monkeypatch.delenv("MESHCHAT_DISABLE_CSRF", raising=False)
    mock_app.config.auth_enabled.set(True)
    pw = b"csrf-login-password"
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        denied = await client.post(
            "/api/v1/auth/login", json={"password": pw.decode("utf-8")}
        )
        assert denied.status == 403
        headers = await fetch_api_csrf_headers(client)
        login = await client.post(
            "/api/v1/auth/login",
            json={"password": pw.decode("utf-8")},
            headers=headers,
        )
        assert login.status == 200


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_server_security_endpoint(mock_app):
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        r = await client.get("/api/v1/server/security")
        assert r.status == 200
        body = await r.json()
        assert body["listen_host"] == "127.0.0.1"
        assert body["is_loopback_bind"] is True


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_privacy_mode_blocks_map_export(mock_app):
    mock_app.config.privacy_mode_enabled.set(True)
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)
        r = await client.post(
            "/api/v1/map/export",
            json={"bbox": [0, 0, 1, 1], "min_zoom": 0, "max_zoom": 1},
            headers=headers,
        )
        assert r.status == 403
