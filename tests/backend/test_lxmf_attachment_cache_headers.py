# SPDX-License-Identifier: 0BSD

"""LXMF attachment responses are content-addressed and must be cacheable forever."""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.http.routes.lxmf import register_lxmf_routes

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_OPUS = b"OggS" + b"\x00" * 32


def _attachment_app(fields: dict):
    mesh_app = MagicMock()
    mesh_app.database.messages.get_lxmf_message_by_hash.return_value = {
        "fields": json.dumps(fields),
    }
    routes = web.RouteTableDef()
    register_lxmf_routes(routes, mesh_app)
    aio_app = web.Application()
    aio_app.add_routes(routes)
    return aio_app


@pytest.mark.asyncio
async def test_image_attachment_sends_immutable_cache_header():
    fields = {
        "image": {"image_bytes": base64.b64encode(_PNG).decode(), "image_type": "png"}
    }
    async with TestClient(TestServer(_attachment_app(fields))) as client:
        response = await client.get("/api/v1/lxmf-messages/attachment/ab/image")
        assert response.status == 200
        assert response.headers["Content-Type"] == "image/png"
        cache_control = response.headers["Cache-Control"]
        assert "immutable" in cache_control
        assert "private" in cache_control
        assert (await response.read()) == _PNG


@pytest.mark.asyncio
async def test_audio_attachment_sends_immutable_cache_header():
    fields = {
        "audio": {"audio_bytes": base64.b64encode(_OPUS).decode(), "audio_mode": "opus"}
    }
    async with TestClient(TestServer(_attachment_app(fields))) as client:
        response = await client.get("/api/v1/lxmf-messages/attachment/ab/audio")
        assert response.status == 200
        assert "immutable" in response.headers["Cache-Control"]


@pytest.mark.asyncio
async def test_attachment_error_responses_have_no_cache_header():
    async with TestClient(
        TestServer(_attachment_app({"image": {"image_type": "png"}}))
    ) as client:
        response = await client.get("/api/v1/lxmf-messages/attachment/ab/image")
        assert response.status == 400
        assert "immutable" not in response.headers.get("Cache-Control", "")
