# SPDX-License-Identifier: 0BSD
"""Oracle tests for sqlite-unavailable API middleware."""

from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.http.middleware import create_sqlite_unavailable_middleware


@pytest.mark.asyncio
async def test_sqlite_unavailable_middleware_maps_locked_db_to_503():
    app = web.Application()
    mesh_app = SimpleNamespace(database=object())

    async def boom(_request):
        raise sqlite3.OperationalError("database is locked")

    app.router.add_get("/api/v1/example", boom)
    app.middlewares.append(create_sqlite_unavailable_middleware(mesh_app))

    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        response = await client.get("/api/v1/example")
        assert response.status == 503
        body = await response.json()
        assert "unavailable" in body["error"].lower()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_sqlite_unavailable_middleware_maps_missing_db_attribute_error():
    app = web.Application()
    mesh_app = SimpleNamespace(database=None)

    async def boom(_request):
        raise AttributeError("'NoneType' object has no attribute 'contacts'")

    app.router.add_get("/api/v1/example", boom)
    app.middlewares.append(create_sqlite_unavailable_middleware(mesh_app))

    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        response = await client.get("/api/v1/example")
        assert response.status == 503
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_sqlite_unavailable_middleware_ignores_non_api_paths():
    app = web.Application()
    mesh_app = SimpleNamespace(database=None)

    async def boom(_request):
        raise sqlite3.OperationalError("database is locked")

    app.router.add_get("/static/x", boom)
    app.middlewares.append(create_sqlite_unavailable_middleware(mesh_app))

    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        response = await client.get("/static/x")
        assert response.status == 500
    finally:
        await client.close()
