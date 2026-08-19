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
    ("POST", "/api/v1/filesync/start", {}),
    ("POST", "/api/v1/filesync/stop", {}),
    ("POST", "/api/v1/filesync/announce", {}),
    ("POST", "/api/v1/filesync/connect", {"identity_hash": "aa" * 16}),
    ("POST", "/api/v1/filesync/disconnect", {"peer_id": "bb" * 16}),
    ("POST", "/api/v1/filesync/browse", {"peer_id": "bb" * 16}),
    ("POST", "/api/v1/filesync/download", {"peer_id": "bb" * 16, "path": "a.txt"}),
    ("POST", "/api/v1/filesync/acl", {"enforce": False}),
    ("PATCH", "/api/v1/filesync/settings", {"monitor": True}),
    ("POST", "/api/v1/filesync/mkdir", {"path": "folder"}),
    ("DELETE", "/api/v1/filesync/entry", {"path": "a.txt"}),
    ("POST", "/api/v1/lxmf/propagation-node/cancel-inbound", {}),
    ("PUT", "/api/v1/lxmf/sieve-filters", {"filters": []}),
    (
        "PUT",
        "/api/v1/lxmf/message-blocklist",
        {"blocklist": {"entries": []}},
    ),
    ("POST", "/api/v1/map/data/announce", {}),
    ("POST", "/api/v1/map/data/catalog", {"destination_hash": "aa" * 16}),
    ("POST", "/api/v1/map/data/publish", {"name": "x", "data_b64": "e30="}),
    (
        "POST",
        "/api/v1/map/data/fetch",
        {"destination_hash": "aa" * 16, "map_id": "a" * 16},
    ),
    (
        "POST",
        "/api/v1/map/data/add-overlay",
        {"destination_hash": "aa" * 16, "map_id": "a" * 16},
    ),
    ("PATCH", "/api/v1/map/data/config", {"announce_enabled": False}),
    ("DELETE", "/api/v1/map/data/published/aaaaaaaaaaaaaaaa", None),
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


def _stub_filesync_handler(mock_app):
    handler = mock_app.rns_filesync_handler
    if handler is None:
        return
    handler.reticulum = object()
    handler.start.return_value = {"ok": True, "running": True}
    handler.stop.return_value = {"ok": True, "running": False}
    handler.announce_now.return_value = {"ok": True}
    handler.connect_peer.return_value = {"ok": True, "peer_id": "aa" * 16}
    handler.disconnect_peer.return_value = {"ok": True, "peer_id": "bb" * 16}
    handler.browse_peer.return_value = {"ok": True, "files": []}
    handler.download_file.return_value = {"ok": True, "path": "a.txt"}
    handler.update_acl.return_value = {"ok": True, "enforce": False, "rules": {}}
    handler.update_settings.return_value = {
        "ok": True,
        "sync_directory": "/tmp",
        "monitor": True,
        "announce_interval": 300,
        "running": False,
    }
    handler.manager_mkdir.return_value = {"ok": True, "path": "folder"}
    handler.manager_delete.return_value = {"ok": True, "path": "a.txt"}
    handler.manager_upload.return_value = {"ok": True, "path": "a.txt", "size": 1}
    handler.list_tree.return_value = {
        "ok": True,
        "current": "",
        "parent": None,
        "entries": [],
    }
    handler.manager_content.return_value = {
        "ok": False,
        "error": "path not allowed",
    }


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
                elif method == "PUT":
                    resp = await client.put(path, json=body)
                elif method == "DELETE":
                    resp = await client.delete(path)
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
        _stub_filesync_handler(mock_app)
        aio_app = _make_aio_app(mock_app)
        samples = list(_MUTATING_SAMPLES)
        rng.shuffle(samples)
        async with TestClient(TestServer(aio_app)) as client:
            headers = await fetch_api_csrf_headers(client)
            for method, path, body in samples:
                if method == "PATCH":
                    resp = await client.patch(path, json=body, headers=headers)
                elif method == "PUT":
                    resp = await client.put(path, json=body, headers=headers)
                elif method == "DELETE":
                    resp = await client.delete(path, headers=headers)
                else:
                    resp = await client.post(path, json=body, headers=headers)
                body_text = await resp.text()
                assert_no_unexpected_http_500(resp.status, body_text)
                assert resp.status != 403, f"{method} {path} still CSRF-blocked"
                assert resp.status < 500
