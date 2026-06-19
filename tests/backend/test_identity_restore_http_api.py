# SPDX-License-Identifier: 0BSD

"""HTTP tests for POST /api/v1/identity/restore."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from aiohttp import FormData, web
from aiohttp.test_utils import TestClient, TestServer

pytestmark = pytest.mark.usefixtures("require_loopback_tcp")


def _build_aio_app(app):
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw = app._define_routes(routes)
    aio_app = web.Application(middlewares=[auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw])
    aio_app.add_routes(routes)
    return aio_app


@pytest.fixture
def web_identity_app(mock_app):
    mock_app.current_context.running = True
    mock_app.config.auth_enabled.set(False)
    return mock_app


@pytest.mark.asyncio
async def test_post_identity_restore_base32_passes_display_name(web_identity_app):
    web_identity_app.restore_identity_from_base32 = MagicMock(
        return_value={"hash": "abc123", "display_name": "Imported Name"}
    )
    aio_app = _build_aio_app(web_identity_app)

    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(
            "/api/v1/identity/restore",
            json={
                "base32": "AAAA",
                "display_name": "Imported Name",
            },
        )
        assert response.status == 200
        data = await response.json()

    assert data["identity"]["hash"] == "abc123"
    web_identity_app.restore_identity_from_base32.assert_called_once_with(
        "AAAA",
        display_name="Imported Name",
    )


@pytest.mark.asyncio
async def test_post_identity_restore_returns_400_when_base32_missing(web_identity_app):
    web_identity_app.restore_identity_from_base32 = MagicMock()
    aio_app = _build_aio_app(web_identity_app)

    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(
            "/api/v1/identity/restore", json={"display_name": "Any"}
        )
        assert response.status == 400
        data = await response.json()

    assert data["message"] == "base32 value is required"
    web_identity_app.restore_identity_from_base32.assert_not_called()


@pytest.mark.asyncio
async def test_post_identity_restore_multipart_file_passes_display_name(
    web_identity_app,
):
    web_identity_app.restore_identity_from_bytes = MagicMock(
        return_value={"hash": "filehash", "display_name": "From File"}
    )
    aio_app = _build_aio_app(web_identity_app)

    form = FormData()
    form.add_field(
        "file",
        b"file-bytes",
        filename="identity.key",
        content_type="application/octet-stream",
    )
    form.add_field("display_name", "From File")

    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post("/api/v1/identity/restore", data=form)
        assert response.status == 200
        data = await response.json()

    assert data["identity"]["hash"] == "filehash"
    web_identity_app.restore_identity_from_bytes.assert_called_once()
    call_args, call_kwargs = web_identity_app.restore_identity_from_bytes.call_args
    assert call_args[0] == b"file-bytes"
    assert call_kwargs["display_name"] == "From File"
