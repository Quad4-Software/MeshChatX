# SPDX-License-Identifier: 0BSD

"""HTTP integration tests for the RNode firmware proxy endpoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

pytestmark = pytest.mark.usefixtures("require_loopback_tcp")


def _build_aio_app(app):
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw = app._define_routes(routes)
    aio_app = web.Application(middlewares=[auth_mw, mime_mw, sec_mw])
    aio_app.add_routes(routes)
    return aio_app


@pytest.fixture
def web_app(mock_app):
    mock_app.current_context.running = True
    mock_app.config.auth_enabled.set(False)
    return mock_app


class _FakeResponse:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body

    async def read(self):
        return self._body


class _FakeSession:
    def __init__(self, status: int, body: bytes):
        self._status = status
        self._body = body
        self.requested_urls: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, allow_redirects=True):
        self.requested_urls.append(url)
        status = self._status
        body = self._body

        @asynccontextmanager
        async def _cm():
            yield _FakeResponse(status, body)

        return _cm()


@pytest.mark.asyncio
async def test_download_firmware_requires_url(web_app):
    aio_app = _build_aio_app(web_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.get("/api/v1/tools/rnode/download_firmware")
        assert r.status == 400
        body = await r.json()
        assert "URL" in body["error"]


@pytest.mark.asyncio
async def test_download_firmware_rejects_disallowed_url(web_app):
    aio_app = _build_aio_app(web_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.get(
            "/api/v1/tools/rnode/download_firmware",
            params={"url": "https://evil.example.com/firmware.zip"},
        )
        assert r.status == 403
        body = await r.json()
        assert "Invalid" in body["error"]


@pytest.mark.asyncio
async def test_download_firmware_returns_zip_for_allowed_url(web_app):
    aio_app = _build_aio_app(web_app)
    fake_zip = b"PK\x03\x04fake-zip-bytes"
    fake_session = _FakeSession(200, fake_zip)

    with patch(
        "aiohttp.ClientSession",
        MagicMock(return_value=fake_session),
    ):
        async with TestClient(TestServer(aio_app)) as client:
            r = await client.get(
                "/api/v1/tools/rnode/download_firmware",
                params={"url": "https://github.com/owner/repo/releases/download/v1/firmware.zip"},
            )
            assert r.status == 200
            assert r.headers.get("Content-Type", "").startswith("application/zip")
            assert r.headers.get("Content-Disposition", "").endswith('"firmware.zip"')
            data = await r.read()
            assert data == fake_zip
            assert fake_session.requested_urls == [
                "https://github.com/owner/repo/releases/download/v1/firmware.zip",
            ]


@pytest.mark.asyncio
async def test_download_firmware_propagates_upstream_error_status(web_app):
    aio_app = _build_aio_app(web_app)
    fake_session = _FakeSession(404, b"")

    with patch(
        "aiohttp.ClientSession",
        MagicMock(return_value=fake_session),
    ):
        async with TestClient(TestServer(aio_app)) as client:
            r = await client.get(
                "/api/v1/tools/rnode/download_firmware",
                params={"url": "https://git.quad4.io/Reticulum/RNode_Firmware/releases/download/v1/firmware.zip"},
            )
            assert r.status == 404
            body = await r.json()
            assert "Failed to download" in body["error"]


@pytest.mark.asyncio
async def test_download_firmware_returns_500_on_exception(web_app):
    aio_app = _build_aio_app(web_app)

    with patch(
        "aiohttp.ClientSession",
        MagicMock(side_effect=RuntimeError("network down")),
    ):
        async with TestClient(TestServer(aio_app)) as client:
            r = await client.get(
                "/api/v1/tools/rnode/download_firmware",
                params={"url": "https://github.com/owner/repo/releases/download/v1/firmware.zip"},
            )
            assert r.status == 500
            body = await r.json()
            assert "network down" in body["error"]


class _FakeJsonResponse:
    def __init__(self, status: int, payload):
        self.status = status
        self._payload = payload

    async def json(self, content_type=None):
        return self._payload

    async def read(self):
        import json

        return json.dumps(self._payload).encode("utf-8")


class _FakeJsonSession:
    def __init__(self, status: int, payload):
        self._status = status
        self._payload = payload
        self.requested_urls: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, allow_redirects=True):
        self.requested_urls.append(url)
        status = self._status
        payload = self._payload

        @asynccontextmanager
        async def _cm():
            yield _FakeJsonResponse(status, payload)

        return _cm()


@pytest.mark.asyncio
async def test_latest_release_returns_proxied_payload(web_app):
    aio_app = _build_aio_app(web_app)
    payload = {
        "tag_name": "v1.83",
        "assets": [{"name": "rnode_firmware_heltec32v3.zip", "browser_download_url": "https://x/rnode.zip"}],
    }
    fake_session = _FakeJsonSession(200, payload)

    with patch(
        "aiohttp.ClientSession",
        MagicMock(return_value=fake_session),
    ):
        async with TestClient(TestServer(aio_app)) as client:
            r = await client.get("/api/v1/tools/rnode/latest_release")
            assert r.status == 200
            body = await r.json()
            assert body == payload
            assert fake_session.requested_urls[0].endswith(
                "/api/v1/repos/Reticulum/RNode_Firmware/releases/latest"
            )


@pytest.mark.asyncio
async def test_latest_release_uses_repo_query_param(web_app):
    aio_app = _build_aio_app(web_app)
    fake_session = _FakeJsonSession(200, {"tag_name": "v0"})

    with patch(
        "aiohttp.ClientSession",
        MagicMock(return_value=fake_session),
    ):
        async with TestClient(TestServer(aio_app)) as client:
            r = await client.get(
                "/api/v1/tools/rnode/latest_release",
                params={"repo": "Some/Other_Repo"},
            )
            assert r.status == 200
            assert fake_session.requested_urls[0].endswith(
                "/api/v1/repos/Some/Other_Repo/releases/latest"
            )


@pytest.mark.asyncio
async def test_latest_release_rejects_invalid_repo(web_app):
    aio_app = _build_aio_app(web_app)
    async with TestClient(TestServer(aio_app)) as client:
        for repo in ("no-slash", "../etc/passwd", "evil repo/x", "bad?repo/x"):
            r = await client.get(
                "/api/v1/tools/rnode/latest_release",
                params={"repo": repo},
            )
            assert r.status == 400, f"expected 400 for repo={repo!r}"


@pytest.mark.asyncio
async def test_latest_release_propagates_upstream_status(web_app):
    aio_app = _build_aio_app(web_app)
    fake_session = _FakeJsonSession(404, {})

    with patch(
        "aiohttp.ClientSession",
        MagicMock(return_value=fake_session),
    ):
        async with TestClient(TestServer(aio_app)) as client:
            r = await client.get("/api/v1/tools/rnode/latest_release")
            assert r.status == 404
            body = await r.json()
            assert "Failed to fetch release" in body["error"]


@pytest.mark.asyncio
async def test_latest_release_returns_500_on_exception(web_app):
    aio_app = _build_aio_app(web_app)
    with patch(
        "aiohttp.ClientSession",
        MagicMock(side_effect=RuntimeError("dns down")),
    ):
        async with TestClient(TestServer(aio_app)) as client:
            r = await client.get("/api/v1/tools/rnode/latest_release")
            assert r.status == 500
            body = await r.json()
            assert "dns down" in body["error"]
