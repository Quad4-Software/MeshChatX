# SPDX-License-Identifier: 0BSD

"""Regression tests for the LXMF delivery ping HTTP endpoint."""

import json
from unittest.mock import MagicMock

import pytest


def _find_handler(app, path, method):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def _make_request(match_info=None, query=None):
    request = MagicMock()
    request.match_info = match_info or {}
    request.query = query or {}
    return request


@pytest.mark.asyncio
async def test_ping_rejects_invalid_destination_hash(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/ping/{destination_hash}/lxmf.delivery",
        "GET",
    )
    assert handler is not None
    response = await handler(
        _make_request(
            match_info={"destination_hash": "not-hex"},
            query={"timeout": "5"},
        ),
    )
    assert response.status == 400
    data = json.loads(response.body)
    assert "Invalid destination hash" in data["message"]


@pytest.mark.asyncio
async def test_ping_rejects_non_integer_timeout(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/ping/{destination_hash}/lxmf.delivery",
        "GET",
    )
    assert handler is not None
    response = await handler(
        _make_request(
            match_info={"destination_hash": "ab" * 16},
            query={"timeout": "abc"},
        ),
    )
    assert response.status == 400
    data = json.loads(response.body)
    assert "Timeout" in data["message"]


@pytest.mark.asyncio
async def test_ping_rejects_zero_timeout(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/ping/{destination_hash}/lxmf.delivery",
        "GET",
    )
    assert handler is not None
    response = await handler(
        _make_request(
            match_info={"destination_hash": "ab" * 16},
            query={"timeout": "0"},
        ),
    )
    assert response.status == 400
