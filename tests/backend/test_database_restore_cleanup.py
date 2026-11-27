# SPDX-License-Identifier: 0BSD

"""Temp-file cleanup for failed /api/v1/database/restore uploads."""

from __future__ import annotations

import os
import tempfile

import pytest
from aiohttp import FormData, web
from aiohttp.test_utils import TestClient, TestServer

import meshchatx.src.backend.http.routes.database as database_routes
from meshchatx.src.backend.http.uploads import PayloadTooLargeError

pytestmark = pytest.mark.usefixtures("require_loopback_tcp")


def _build_aio_app(app):
    routes = web.RouteTableDef()
    middlewares = app._define_routes(routes)
    aio_app = web.Application(middlewares=list(middlewares))
    aio_app.add_routes(routes)
    return aio_app


@pytest.mark.asyncio
async def test_restore_multipart_temp_file_removed_on_payload_too_large(
    mock_app, monkeypatch
):
    mock_app.current_context.running = True
    mock_app.config.auth_enabled.set(False)

    created = []
    real_ntf = tempfile.NamedTemporaryFile

    class _SpyNamedTemporaryFile:
        def __init__(self, *args, **kwargs):
            self._cm = real_ntf(*args, **kwargs)

        def __enter__(self):
            handle = self._cm.__enter__()
            created.append(handle.name)
            return handle

        def __exit__(self, *args):
            return self._cm.__exit__(*args)

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", _SpyNamedTemporaryFile)

    async def fail_write(field, path, max_bytes, **kwargs):
        raise PayloadTooLargeError("Upload exceeds size limit")

    monkeypatch.setattr(database_routes, "write_field_to_path", fail_write)

    aio_app = _build_aio_app(mock_app)
    form = FormData()
    form.add_field(
        "file",
        b"x" * 64,
        filename="backup.zip",
        content_type="application/zip",
    )

    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post("/api/v1/database/restore", data=form)
        assert response.status == 413

    assert created, "route never staged a temp file"
    for path in created:
        assert not os.path.exists(path)
