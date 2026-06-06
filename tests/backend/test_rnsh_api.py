# SPDX-License-Identifier: 0BSD

"""Tests for RNSh manager HTTP API endpoints."""

import json
from unittest.mock import MagicMock

import pytest


def _find_handler(app, path, method):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def _make_request(json_body=None, match_info=None, query=None):
    request = MagicMock()

    async def _json():
        return json_body if json_body is not None else {}

    request.json = _json
    request.match_info = match_info or {}
    request.query = query or {}
    return request


class _DummySession:
    def __init__(self, session_id="s1"):
        self.session_id = session_id

    def to_dict(self, include_output_tail=False):
        return {
            "id": self.session_id,
            "name": "test",
            "mode": "connect",
            "status": "running",
            "output_chunks": [],
            "output_text": "",
            "last_command": "rnsh deadbeef",
        }

    def start(self):
        return self.to_dict(include_output_tail=True)


class _DummyManager:
    def __init__(self):
        self.created_payload = None
        self.sent_text = None

    def list_sessions(self):
        return {"sessions": [_DummySession("s1").to_dict(include_output_tail=True)]}

    def create_session(self, payload):
        self.created_payload = payload
        return _DummySession("s2")

    def remove_session(self, session_id):
        if session_id == "missing":
            raise KeyError("missing")

    def start_session(self, session_id):
        if session_id == "missing":
            raise KeyError("missing")
        return _DummySession(session_id).to_dict(include_output_tail=True)

    def stop_session(self, session_id):
        if session_id == "missing":
            raise KeyError("missing")
        return _DummySession(session_id).to_dict(include_output_tail=True)

    def send_input(self, session_id, text):
        if session_id == "missing":
            raise KeyError("missing")
        self.sent_text = text
        return _DummySession(session_id).to_dict(include_output_tail=False)

    def resize_session(self, session_id, rows, cols):
        if session_id == "missing":
            raise KeyError("missing")
        self.resized = (rows, cols)
        return _DummySession(session_id).to_dict(include_output_tail=False)

    def output_since(self, session_id, cursor):
        if session_id == "missing":
            raise KeyError("missing")
        return {"chunks": [{"seq": 1, "text": "ok", "ts": 1.0}], "next_cursor": 1}

    def clear_output(self, session_id):
        if session_id == "missing":
            raise KeyError("missing")
        return _DummySession(session_id).to_dict(include_output_tail=True)


@pytest.mark.asyncio
async def test_rnsh_list_sessions(mock_app):
    mock_app.rnsh_manager = _DummyManager()
    handler = _find_handler(mock_app, "/api/v1/rnsh/sessions", "GET")
    assert handler is not None
    response = await handler(_make_request())
    assert response.status == 200
    data = json.loads(response.body)
    assert len(data["sessions"]) == 1


@pytest.mark.asyncio
async def test_rnsh_create_and_autostart(mock_app):
    manager = _DummyManager()
    mock_app.rnsh_manager = manager
    handler = _find_handler(mock_app, "/api/v1/rnsh/sessions", "POST")
    assert handler is not None
    response = await handler(
        _make_request(
            json_body={
                "name": "ops",
                "mode": "connect",
                "destination": "00112233445566778899aabbccddeeff",
                "autostart": True,
            },
        ),
    )
    assert response.status == 200
    data = json.loads(response.body)
    assert data["session"]["id"] == "s2"
    assert manager.created_payload["name"] == "ops"


@pytest.mark.asyncio
async def test_rnsh_send_input_appends_newline(mock_app):
    manager = _DummyManager()
    mock_app.rnsh_manager = manager
    handler = _find_handler(
        mock_app, "/api/v1/rnsh/sessions/{session_id}/input", "POST"
    )
    assert handler is not None
    response = await handler(
        _make_request(
            json_body={"text": "ls", "newline": True},
            match_info={"session_id": "s1"},
        ),
    )
    assert response.status == 200
    assert manager.sent_text == "ls\n"


@pytest.mark.asyncio
async def test_rnsh_resize_forwards_dimensions(mock_app):
    manager = _DummyManager()
    mock_app.rnsh_manager = manager
    handler = _find_handler(
        mock_app, "/api/v1/rnsh/sessions/{session_id}/resize", "POST"
    )
    assert handler is not None
    response = await handler(
        _make_request(
            json_body={"rows": 24, "cols": 80},
            match_info={"session_id": "s1"},
        ),
    )
    assert response.status == 200
    assert manager.resized == (24, 80)


def test_rnsh_listen_address_detected_from_output():
    from meshchatx.src.backend.rnsh_manager import RNSHSession

    manager = MagicMock()
    session = RNSHSession(manager, "s1", {"mode": "listen"})
    assert session.listen_address == ""
    session.append_output(
        "[Notice] rnsh listening for commands on <8d7f90d560627da94a312bb96ba5c485>\n",
    )
    assert session.listen_address == "8d7f90d560627da94a312bb96ba5c485"

    payload = session.to_dict()
    assert payload["listen_address"] == "8d7f90d560627da94a312bb96ba5c485"


def test_rnsh_resize_updates_geometry_without_process():
    from meshchatx.src.backend.rnsh_manager import RNSHSession

    manager = MagicMock()
    session = RNSHSession(manager, "s1", {"mode": "connect", "destination": "abc"})
    result = session.resize(30, 100)
    assert result["rows"] == 30
    assert result["cols"] == 100


@pytest.mark.asyncio
async def test_rnsh_session_not_found_returns_404(mock_app):
    mock_app.rnsh_manager = _DummyManager()
    handler = _find_handler(
        mock_app, "/api/v1/rnsh/sessions/{session_id}/start", "POST"
    )
    assert handler is not None
    response = await handler(_make_request(match_info={"session_id": "missing"}))
    assert response.status == 404
