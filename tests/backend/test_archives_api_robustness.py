# SPDX-License-Identifier: 0BSD

"""Robustness tests for REST handlers (archives, bundled docs, lxmf send) and related WS paths."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


def _handler(app, method: str, path: str):
    for route in app.get_routes():
        if route.method == method and route.path == path:
            return route.handler
    return None


@pytest.mark.asyncio
async def test_get_archives_returns_json_for_edge_case_queries(mock_app):
    handler = _handler(mock_app, "GET", "/api/v1/nomadnet/archives")
    assert handler is not None

    edge_queries = [
        {},
        {"q": "", "page": "1", "limit": "100"},
        {"q": "%00%3Cscript%3E", "page": "not-a-number", "limit": "not-a-number"},
        {"page": "-5", "limit": "0"},
        {"limit": "99999"},
    ]
    for query in edge_queries:
        request = MagicMock()
        request.query = query
        response = await handler(request)
        assert response.status == 200
        payload = json.loads(response.body)
        assert isinstance(payload.get("archives"), list)
        assert "pagination" in payload


@settings(
    max_examples=60,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(
    q=st.text(max_size=800),
    page=st.one_of(
        st.integers(min_value=-1000, max_value=10**9),
        st.text(max_size=40),
    ),
    limit=st.one_of(
        st.integers(min_value=-1000, max_value=10**9),
        st.text(max_size=40),
    ),
)
@pytest.mark.asyncio
async def test_get_archives_query_fuzz(mock_app, q, page, limit):
    handler = _handler(mock_app, "GET", "/api/v1/nomadnet/archives")
    assert handler is not None

    request = MagicMock()
    request.query = {
        "q": q,
        "page": str(page),
        "limit": str(limit),
    }
    response = await handler(request)
    assert response.status == 200
    payload = json.loads(response.body)
    assert isinstance(payload.get("archives"), list)
    assert "pagination" in payload


@pytest.mark.asyncio
async def test_delete_archives_requires_nonempty_ids(mock_app):
    handler = _handler(mock_app, "DELETE", "/api/v1/nomadnet/archives")
    assert handler is not None

    request = MagicMock()
    request.json = AsyncMock(return_value={"ids": []})
    response = await handler(request)
    assert response.status == 400


@pytest.mark.asyncio
async def test_meshchatx_docs_content_requires_path(mock_app):
    handler = _handler(mock_app, "GET", "/api/v1/meshchatx-docs/content")
    assert handler is not None
    request = MagicMock()
    request.query = {}
    response = await handler(request)
    assert response.status == 400


@settings(
    max_examples=40,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(path=st.text(min_size=1, max_size=600))
@pytest.mark.asyncio
async def test_meshchatx_docs_content_path_fuzz(mock_app, path):
    handler = _handler(mock_app, "GET", "/api/v1/meshchatx-docs/content")
    assert handler is not None
    request = MagicMock()
    request.query = {"path": path}
    response = await handler(request)
    assert response.status in (200, 404)
    json.loads(response.body)


@pytest.mark.asyncio
async def test_lxmf_messages_send_requires_lxmf_message(mock_app):
    handler = _handler(mock_app, "POST", "/api/v1/lxmf-messages/send")
    assert handler is not None
    request = MagicMock()
    request.json = AsyncMock(return_value={})
    response = await handler(request)
    assert response.status == 400


@pytest.mark.asyncio
async def test_lxmf_messages_send_requires_destination_and_content(mock_app):
    handler = _handler(mock_app, "POST", "/api/v1/lxmf-messages/send")
    assert handler is not None
    request = MagicMock()
    request.json = AsyncMock(
        return_value={"lxmf_message": {"fields": {}}},
    )
    response = await handler(request)
    assert response.status == 400


@pytest.mark.asyncio
async def test_lxmf_messages_send_rejects_bad_image_field(mock_app):
    handler = _handler(mock_app, "POST", "/api/v1/lxmf-messages/send")
    assert handler is not None
    request = MagicMock()
    request.json = AsyncMock(
        return_value={
            "lxmf_message": {
                "destination_hash": "aa",
                "content": "x",
                "fields": {
                    "image": {"image_type": "png", "image_bytes": "@@@not-base64@@@"},
                },
            },
        },
    )
    response = await handler(request)
    assert response.status == 400


@pytest.mark.asyncio
async def test_nomadnet_file_download_invalid_hex_does_not_raise(mock_app):
    await mock_app.on_websocket_data_received(
        MagicMock(),
        {
            "type": "nomadnet.file.download",
            "nomadnet_file_download": {
                "destination_hash": "gg",
                "file_path": "/file/x.txt",
            },
        },
    )
