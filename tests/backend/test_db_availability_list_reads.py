# SPDX-License-Identifier: 0BSD
"""Oracle tests for shared DB availability helpers and sibling list GETs."""

from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.http.db_availability import (
    DB_TEMPORARILY_UNAVAILABLE,
    http_for_database_exception,
    require_database,
)
from meshchatx.src.backend.http.routes.blocklist import register_blocklist_routes
from meshchatx.src.backend.http.routes.favourites import register_favourites_routes


def test_require_database_oracle():
    assert require_database(SimpleNamespace(database=None)).status == 503
    assert require_database(SimpleNamespace(database=object())) is None


def test_http_for_database_exception_oracle():
    locked = http_for_database_exception(sqlite3.OperationalError("database is locked"))
    assert locked.status == 503
    body = json.loads(locked.body)
    assert body["error"] == DB_TEMPORARILY_UNAVAILABLE

    boom = http_for_database_exception(RuntimeError("other"), unexpected_message="x")
    assert boom.status == 500
    assert json.loads(boom.body)["error"] == "x"


def _capture_gets(register_fn, app):
    routes = MagicMock()
    captured = {}

    def _get(path):
        def decorator(fn):
            captured[path] = fn
            return fn

        return decorator

    routes.get = _get
    routes.post = MagicMock(side_effect=lambda path: lambda fn: fn)
    routes.put = MagicMock(side_effect=lambda path: lambda fn: fn)
    routes.delete = MagicMock(side_effect=lambda path: lambda fn: fn)
    routes.patch = MagicMock(side_effect=lambda path: lambda fn: fn)
    register_fn(routes, app)
    return captured


@pytest.mark.asyncio
async def test_favourites_get_returns_503_when_database_missing():
    handlers = _capture_gets(register_favourites_routes, SimpleNamespace(database=None))
    request = MagicMock()
    request.query = {}
    response = await handlers["/api/v1/favourites"](request)
    assert response.status == 503


@pytest.mark.asyncio
async def test_favourites_get_returns_503_on_locked_database():
    announces = MagicMock()
    announces.get_favourites.side_effect = sqlite3.OperationalError(
        "database is locked"
    )
    app = SimpleNamespace(database=SimpleNamespace(announces=announces))
    handlers = _capture_gets(register_favourites_routes, app)
    request = MagicMock()
    request.query = {}
    response = await handlers["/api/v1/favourites"](request)
    assert response.status == 503


@pytest.mark.asyncio
async def test_blocked_destinations_get_returns_503_when_database_missing():
    handlers = _capture_gets(register_blocklist_routes, SimpleNamespace(database=None))
    response = await handlers["/api/v1/blocked-destinations"](MagicMock())
    assert response.status == 503
