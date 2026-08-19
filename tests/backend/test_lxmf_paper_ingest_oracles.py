# SPDX-License-Identifier: 0BSD

"""Oracles for paper-message and meshchatx URI ingest over the LXMF WS handlers."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.http.ws.handlers_lxmf import (
    handle_lxm_generate_paper_uri,
    handle_lxm_ingest_uri,
)
from tests.backend.lxmf_tools_support import LOCAL_LXMF, prepare_messaging_app


def _client():
    client = MagicMock()
    client.send_str = MagicMock()
    return client


def _last_payload(client) -> dict | None:
    if not client.send_str.called:
        return None
    raw = client.send_str.call_args[0][0]
    return json.loads(raw)


def test_oracle_empty_uri_is_noop(mock_app):
    app = prepare_messaging_app(mock_app)
    client = _client()
    asyncio.run(handle_lxm_ingest_uri(app, client, {}))
    client.send_str.assert_not_called()
    asyncio.run(handle_lxm_ingest_uri(app, client, {"uri": ""}))
    client.send_str.assert_not_called()


def test_oracle_map_link_accepts_numeric_lat_lon(mock_app):
    app = prepare_messaging_app(mock_app)
    client = _client()
    asyncio.run(
        handle_lxm_ingest_uri(
            app,
            client,
            {"uri": "meshchatx://map?lat=51.5&lon=-0.12&z=11&label=home"},
        ),
    )
    payload = _last_payload(client)
    assert payload["type"] == "lxm.ingest_uri.result"
    assert payload["status"] == "success"
    assert payload["ingest_type"] == "map_view"
    assert payload["map_query"]["lat"] == 51.5
    assert payload["map_query"]["lon"] == -0.12
    assert payload["map_query"]["zoom"] == 11
    assert payload["map_query"]["label"] == "home"


def test_oracle_map_link_rejects_non_numeric_coords(mock_app):
    app = prepare_messaging_app(mock_app)
    client = _client()
    asyncio.run(
        handle_lxm_ingest_uri(
            app,
            client,
            {"uri": "meshchatx://map?lat=north&lon=east"},
        ),
    )
    payload = _last_payload(client)
    assert payload["status"] == "error"
    assert "lat" in payload["message"].lower()


@pytest.mark.parametrize(
    ("zoom_raw", "expected"),
    [
        ("3", 3),
        ("99", 22),
        ("-2", 0),
        ("x", 10),
    ],
)
def test_oracle_map_zoom_clamped(mock_app, zoom_raw, expected):
    app = prepare_messaging_app(mock_app)
    client = _client()
    asyncio.run(
        handle_lxm_ingest_uri(
            app,
            client,
            {"uri": f"meshchat://map?lat=1&lon=2&z={zoom_raw}"},
        ),
    )
    payload = _last_payload(client)
    assert payload["status"] == "success"
    assert payload["map_query"]["zoom"] == expected


def test_oracle_docs_link_and_unknown_host(mock_app):
    app = prepare_messaging_app(mock_app)
    client = _client()
    asyncio.run(
        handle_lxm_ingest_uri(
            app,
            client,
            {"uri": "meshchatx://docs?path=getting-started.md"},
        ),
    )
    docs = _last_payload(client)
    assert docs["status"] == "success"
    assert docs["ingest_type"] == "docs_view"
    asyncio.run(
        handle_lxm_ingest_uri(
            app,
            client,
            {"uri": "meshchatx://not-a-host/foo"},
        ),
    )
    unknown = _last_payload(client)
    assert unknown["status"] == "error"
    assert unknown["ingest_type"] == "unknown_meshchatx"


@pytest.mark.parametrize(
    ("router_result", "status"),
    [
        (False, "error"),
        ("local_delivery_occurred", "success"),
        ("duplicate_lxm", "info"),
        ("other", "warning"),
    ],
)
def test_oracle_lxm_uri_ingest_status_matrix(mock_app, router_result, status):
    app = prepare_messaging_app(mock_app)
    app.message_router.ingest_lxm_uri.return_value = router_result
    client = _client()
    asyncio.run(handle_lxm_ingest_uri(app, client, {"uri": "lxm://deadbeef"}))
    payload = _last_payload(client)
    assert payload["type"] == "lxm.ingest_uri.result"
    assert payload["status"] == status
    app.message_router.ingest_lxm_uri.assert_called()


def test_oracle_generate_paper_uri_requires_dest_and_content(mock_app):
    app = prepare_messaging_app(mock_app)
    client = _client()
    asyncio.run(handle_lxm_generate_paper_uri(app, client, {}))
    client.send_str.assert_not_called()
    asyncio.run(
        handle_lxm_generate_paper_uri(
            app,
            client,
            {"destination_hash": LOCAL_LXMF},
        ),
    )
    client.send_str.assert_not_called()


def test_oracle_generate_paper_uri_unknown_identity_errors(mock_app):
    app = prepare_messaging_app(mock_app)
    client = _client()
    from unittest.mock import patch

    with patch("meshchatx.meshchat.RNS.Identity.recall", return_value=None):
        asyncio.run(
            handle_lxm_generate_paper_uri(
                app,
                client,
                {"destination_hash": LOCAL_LXMF, "content": "hello paper"},
            ),
        )
    payload = _last_payload(client)
    assert payload is not None
    assert payload["type"] == "lxm.generate_paper_uri.result"
    assert payload["status"] == "error"
    assert "identity" in payload["message"].lower()
