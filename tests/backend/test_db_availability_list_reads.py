# SPDX-License-Identifier: 0BSD
"""Reference tests for shared DB availability helpers and sibling list GETs."""

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
from meshchatx.src.backend.http.routes.lxmf import register_lxmf_routes


def test_require_database():
    assert require_database(SimpleNamespace(database=None)).status == 503
    assert require_database(SimpleNamespace(database=object())) is None


def test_http_for_database_exception():
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


@pytest.mark.asyncio
async def test_lxmf_conversations_returns_503_if_identity_switches_during_load(
    monkeypatch,
):
    import meshchatx.src.backend.http.routes.lxmf as lxmf_routes

    telemetry = SimpleNamespace(get_tracking_states=MagicMock())
    messages = SimpleNamespace(
        get_notification_last_viewed_at_map=MagicMock(),
        notification_viewed_covers=MagicMock(return_value=False),
    )
    database = SimpleNamespace(telemetry=telemetry, messages=messages)
    message_handler = SimpleNamespace(
        clamp_conversations_limit=lambda limit: limit,
        get_conversations=MagicMock(return_value=[]),
    )
    context = SimpleNamespace(
        database=database,
        message_handler=message_handler,
        local_lxmf_destination=SimpleNamespace(hexhash="local"),
        running=True,
    )
    app = SimpleNamespace(
        current_context=context,
        database=database,
        message_handler=message_handler,
        local_lxmf_destination=context.local_lxmf_destination,
        _require_identity_context_ready=lambda: None,
        _lxmf_sieve_hides_peer=lambda *_args, **_kwargs: False,
    )
    handlers = _capture_gets(register_lxmf_routes, app)

    async def switch_identity_during_query(function, *args, **kwargs):
        result = function(*args, **kwargs)
        app.current_context = None
        app.database = None
        app.message_handler = None
        return result

    monkeypatch.setattr(lxmf_routes.asyncio, "to_thread", switch_identity_during_query)
    request = MagicMock()
    request.query = {}

    response = await handlers["/api/v1/lxmf/conversations"](request)

    assert response.status == 503
    telemetry.get_tracking_states.assert_not_called()
