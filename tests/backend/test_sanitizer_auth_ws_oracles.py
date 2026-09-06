# SPDX-License-Identifier: 0BSD

"""Oracles for HTML sanitization, auth verification, command environments, and privacy.

Each test predicts accept or reject from the input (or from a fixed allowlist)
and checks the implementation matches.
"""

from __future__ import annotations

import json
import os
import secrets
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import setup as setup_session
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.http.middleware import (
    create_auth_middleware,
    csrf_exempt_path,
)
from meshchatx.src.backend.http.ws.dispatch import WS_HANDLERS
from meshchatx.src.backend.log_redaction import REDACTED, redact_diagnostic_text
from meshchatx.src.backend.lxmf_utils import parse_stored_lxmf_fields
from meshchatx.src.backend.map_geo_sanitizer import sanitize_geo_bytes
from meshchatx.src.backend.markdown_renderer import MarkdownRenderer, _safe_href
from meshchatx.src.backend.page_node import _build_executable_page_env
from meshchatx.src.backend.plugin_guard import PluginSecurityError, normalize_asset_path
from meshchatx.src.backend.sticker_utils import detect_image_format_from_magic
from meshchatx.src.backend.websocket_config_guard import (
    WEBSOCKET_MUTATOR_TYPES,
    WEBSOCKET_PUBLIC_TYPES,
    WEBSOCKET_READ_TYPES,
    websocket_type_requires_auth,
)
from tests.backend.conftest import extend_meshchat_middlewares, fetch_api_csrf_headers

_XSS_HREF_PAYLOADS = (
    "javascript:alert(1)",
    "JAVASCRIPT:alert(1)",
    " javascript:alert(1)",
    "\tjavascript:alert(1)",
    "vbscript:msgbox(1)",
    "data:text/html,<script>alert(1)</script>",
    "data:image/svg+xml,<svg onload=alert(1)>",
    "//evil.example/x",
    "file:///etc/passwd",
)

_PROTECTED_WHEN_AUTH = (
    "GET /api/v1/config",
    "GET /api/v1/map/data/status",
    "GET /api/v1/map/data/published",
    "GET /api/v1/identities",
    "GET /api/v1/lxmf-messages/attachment/aa/image",
    "POST /api/v1/map/data/publish",
    "POST /api/v1/map/data/announce",
    "PATCH /api/v1/map/data/config",
    "DELETE /api/v1/map/data/published/aaaaaaaaaaaaaaaa",
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


def _enable_password_auth(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(b"adversarial-pass-ok", bcrypt.gensalt()).decode("utf-8"),
    )


def _href_is_executable(url: str) -> bool:
    u = (url or "").strip().lower()
    return u.startswith(("javascript:", "vbscript:", "data:", "file:")) or u.startswith(
        "//",
    )


def test_oracle_safe_href_rejects_executable_schemes():
    for payload in _XSS_HREF_PAYLOADS:
        out = _safe_href(payload)
        assert out == "#", payload
        assert not _href_is_executable(out)


def test_oracle_markdown_render_never_emits_executable_href():
    for payload in _XSS_HREF_PAYLOADS:
        html = MarkdownRenderer.render(f"[x]({payload})")
        assert "<script" not in html.lower()
        assert "javascript:" not in html.lower()
        assert "vbscript:" not in html.lower()
        assert 'href="data:' not in html.lower()


def test_oracle_markdown_img_src_rejects_svg_and_html_data():
    html = MarkdownRenderer.render("![x](data:image/svg+xml,<svg onload=alert(1)>)")
    assert "data:image/svg" not in html.lower()
    html = MarkdownRenderer.render("![x](javascript:alert(1))")
    assert "javascript:" not in html.lower()


def test_oracle_kml_description_child_html_is_flattened():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <Placemark><name>P</name>
        <description><script>alert(1)</script><a href="javascript:alert(1)">x</a></description>
        <Point><coordinates>1,2,0</coordinates></Point>
      </Placemark>
    </Document></kml>"""
    result = sanitize_geo_bytes(kml)
    assert result.feature_count == 1
    lower = result.data.lower()
    assert b"<script" not in lower
    assert b"<a " not in lower
    assert b"<a href" not in lower
    assert "html_description" in result.stripped


def test_oracle_geojson_strips_data_html_and_vbscript_icon_keys():
    payload = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "name": "A",
                        "href": "vbscript:msgbox(1)",
                        "icon": "data:text/html,<script>alert(1)</script>",
                        "note": "keep me",
                    },
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                },
            ],
        },
    ).encode()
    result = sanitize_geo_bytes(payload)
    obj = json.loads(result.data)
    props = obj["features"][0]["properties"]
    assert "href" not in props
    assert "icon" not in props
    assert props["note"] == "keep me"
    assert "remote_href" in result.stripped


def test_oracle_image_magic_rejects_html_svg_and_empty():
    assert detect_image_format_from_magic(b"<html><script>alert(1)</script>") is None
    assert detect_image_format_from_magic(b"<svg onload=alert(1)>") is None
    assert detect_image_format_from_magic(b"GIF") is None
    assert detect_image_format_from_magic(b"") is None
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde"
    )
    assert detect_image_format_from_magic(png) == "png"


def test_oracle_executable_page_env_cannot_clobber_path_or_inject_loader():
    env = _build_executable_page_env(
        {
            "PATH": "/evil/bin",
            "SYSTEMROOT": r"C:\evil",
            "LD_PRELOAD": "/evil.so",
            "PYTHONPATH": "/evil/py",
            "field_name": "ok",
            "var_x": "1",
            "field_PATH": "/from-peer",
            "field_LD_PRELOAD": "/from-peer.so",
        },
        link_id=None,
        remote_identity=None,
    )
    assert env.get("PATH") == os.environ.get("PATH")
    assert env.get("SYSTEMROOT") == os.environ.get("SYSTEMROOT")
    if "SYSTEMROOT" not in os.environ:
        assert "SYSTEMROOT" not in env
    assert "LD_PRELOAD" not in env
    assert "PYTHONPATH" not in env
    assert env["field_name"] == "ok"
    assert env["var_x"] == "1"
    assert env["field_PATH"] == "/from-peer"
    assert env["field_LD_PRELOAD"] == "/from-peer.so"


def test_oracle_plugin_asset_path_rejects_traversal():
    for bad in (
        "../etc/passwd",
        "/etc/passwd",
        "foo/../../etc/passwd",
        "C:/Windows/system.ini",
        "foo\x00/bar",
        "",
        ".",
        "..",
    ):
        with pytest.raises(PluginSecurityError):
            normalize_asset_path(bad)
    assert normalize_asset_path("frontend/main.js") == "frontend/main.js"


def test_oracle_ws_handlers_are_classified():
    from meshchatx.src.backend.websocket_config_guard import (
        WEBSOCKET_RUNTIME_CONTROL_TYPES,
    )

    classified = WEBSOCKET_PUBLIC_TYPES | WEBSOCKET_READ_TYPES | WEBSOCKET_MUTATOR_TYPES
    missing = set(WS_HANDLERS) - classified
    extra = classified - set(WS_HANDLERS) - WEBSOCKET_RUNTIME_CONTROL_TYPES
    assert not missing, f"unclassified WS handlers: {sorted(missing)}"
    assert not extra, f"guard lists types with no handler: {sorted(extra)}"
    for msg_type in WEBSOCKET_MUTATOR_TYPES:
        assert websocket_type_requires_auth(msg_type) is True
    for msg_type in WEBSOCKET_PUBLIC_TYPES:
        assert websocket_type_requires_auth(msg_type) is False
    for msg_type in WEBSOCKET_READ_TYPES:
        assert websocket_type_requires_auth(msg_type) is True


def test_oracle_config_dict_omits_secrets(mock_app):
    mock_app.config.auth_password_hash.set("should-never-leak")
    mock_app.identity.get_public_key = MagicMock(return_value=b"\x01" * 64)
    cfg = mock_app.get_config_dict()
    assert "auth_password_hash" not in cfg
    assert "private_key" not in cfg

    def walk(obj):
        if isinstance(obj, dict):
            assert "auth_password_hash" not in obj
            assert "private_key" not in obj
            for value in obj.values():
                walk(value)
        elif isinstance(obj, str):
            assert "should-never-leak" not in obj
            assert "test_private_key" not in obj

    walk(cfg)


def test_oracle_startup_status_omits_identity_material(mock_app):
    payload = mock_app._startup_status_payload()
    blob = json.dumps(payload)
    assert "identity_hash" not in payload
    assert "identity_public_key" not in payload
    assert "auth_password_hash" not in blob
    assert "private_key" not in blob


def test_oracle_csrf_exempt_is_exact_path_only():
    assert csrf_exempt_path("/api/v1/auth/csrf") is True
    assert csrf_exempt_path("/api/v1/auth/csrf/") is False
    assert csrf_exempt_path("/api/v1/auth/csrf/extra") is False
    assert csrf_exempt_path("/api/v1/auth/login") is False
    assert csrf_exempt_path("/api/v1/map/data/publish") is False


def test_oracle_parse_stored_lxmf_fields_fail_closed():
    assert parse_stored_lxmf_fields('{"ok": true}') == {"ok": True}
    for bad in (None, "", "[]", "null", "1", b"not-json", object()):
        assert parse_stored_lxmf_fields(bad) is None


def test_oracle_redact_diagnostic_strips_keys_paths_hashes():
    raw = (
        "password=supersecret "
        "private_key=aabb "
        "alias_identity_private_key=deadbeef "
        "/home/user1/meshchatx/database.db "
        "hash=" + ("ab" * 32)
    )
    out = redact_diagnostic_text(raw)
    assert "supersecret" not in out
    assert "deadbeef" not in out
    assert "/home/user1" not in out
    assert ("ab" * 32) not in out
    assert REDACTED in out


@pytest.mark.asyncio
async def test_oracle_auth_middleware_status_prefix_is_not_public():
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

    public = await call("/api/v1/status")
    assert public.status == 200
    handler.assert_awaited()

    handler.reset_mock()
    for path in (
        "/api/v1/status.json",
        "/api/v1/status/extra",
        "/api/v1/config",
        "/api/v1/map/data/status",
        "/ws",
    ):
        handler.reset_mock()
        resp = await call(path)
        assert resp.status == 401, f"{path} expected 401 got {resp.status}"
        handler.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oracle_protected_routes_401_when_auth_enabled(mock_app):
    _enable_password_auth(mock_app)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        for spec in _PROTECTED_WHEN_AUTH:
            method, path = spec.split(" ", 1)
            if method == "GET":
                resp = await client.get(path)
            elif method == "POST":
                resp = await client.post(path, json={})
            elif method == "PATCH":
                resp = await client.patch(path, json={})
            else:
                resp = await client.delete(path)
            assert resp.status in (401, 403), (
                f"{spec} expected 401/403 got {resp.status}"
            )


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oracle_auth_setup_rejected_once_password_exists(mock_app):
    _enable_password_auth(mock_app)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)
        resp = await client.post(
            "/api/v1/auth/setup",
            json={"password": "new-password-ok"},
            headers=headers,
        )
        assert resp.status == 403
        body = await resp.json()
        assert "already" in body.get("error", "").lower()


@settings(
    deadline=None,
    max_examples=40,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(raw=st.text(max_size=200))
def test_oracle_safe_href_never_returns_executable_scheme(raw):
    out = _safe_href(raw)
    assert isinstance(out, str)
    assert not _href_is_executable(out) or out == "#"
    if _href_is_executable(raw):
        assert out == "#"
