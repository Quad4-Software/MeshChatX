# SPDX-License-Identifier: 0BSD

"""Active UI WebSocket session tracking and multi-session warning oracles."""

from __future__ import annotations

import json
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.active_sessions import (
    ActiveSessionTracker,
    should_warn_multi_session,
)


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns_minimal():
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
    ):
        mock_rns_instance = mock_rns.return_value
        mock_rns_instance.configpath = "/tmp/mock_config"
        mock_rns_instance.is_connected_to_shared_instance = False
        mock_rns_instance.transport_enabled.return_value = True

        mock_id = MagicMock(spec=RNS.Identity)
        mock_id.hash = b"test_hash_32_bytes_long_01234567"
        mock_id.hexhash = mock_id.hash.hex()
        mock_id.get_private_key.return_value = b"test_private_key"
        yield mock_id


def test_should_warn_multi_session_oracle_edge_cases():
    assert should_warn_multi_session(0, True) is False
    assert should_warn_multi_session(1, True) is False
    assert should_warn_multi_session(2, True) is True
    assert should_warn_multi_session(3, True) is True
    assert should_warn_multi_session(2, False) is False
    assert should_warn_multi_session(99, False) is False
    assert should_warn_multi_session("2", True) is True
    assert should_warn_multi_session("nope", True) is False
    assert should_warn_multi_session(None, True) is False


@given(
    count=st.integers(min_value=-5, max_value=50),
    enabled=st.booleans(),
)
@settings(max_examples=80, deadline=None)
def test_should_warn_multi_session_matches_count_threshold(count, enabled):
    expected = bool(enabled) and int(count) >= 2
    assert should_warn_multi_session(count, enabled) is expected


def test_tracker_add_list_remove_round_trip():
    tracker = ActiveSessionTracker()
    assert tracker.count() == 0
    assert tracker.list_sessions() == []

    first = tracker.add(ip="127.0.0.1", user_agent="Browser/A")
    second = tracker.add(ip="10.0.0.2", user_agent="Browser/B")
    assert first["id"] != second["id"]
    assert tracker.count() == 2

    rows = tracker.list_sessions()
    assert len(rows) == 2
    assert rows[0]["ip"] == "127.0.0.1"
    assert rows[0]["user_agent"] == "Browser/A"
    assert rows[1]["ip"] == "10.0.0.2"
    assert isinstance(rows[0]["connected_at"], float)

    assert tracker.remove(first["id"]) is True
    assert tracker.count() == 1
    assert tracker.remove(first["id"]) is False
    assert tracker.remove("") is False
    assert tracker.remove(None) is False

    snap = tracker.snapshot()
    assert snap["count"] == 1
    assert snap["sessions"][0]["id"] == second["id"]


def test_tracker_sanitizes_ip_and_user_agent():
    tracker = ActiveSessionTracker()
    entry = tracker.add(ip=None, user_agent="\x00\x01bad\x7f agent")
    assert entry["ip"] == "unknown"
    assert "\x00" not in entry["user_agent"]
    assert "bad" in entry["user_agent"]

    long_ua = "x" * 2000
    long_ip = "y" * 200
    entry2 = tracker.add(ip=long_ip, user_agent=long_ua)
    assert len(entry2["ip"]) <= 128
    assert len(entry2["user_agent"]) <= 512


def test_tracker_empty_user_agent_becomes_unknown():
    tracker = ActiveSessionTracker()
    entry = tracker.add(ip="192.168.1.1", user_agent="   ")
    assert entry["user_agent"] == "unknown"


@pytest.mark.asyncio
async def test_app_sessions_endpoint_smoke(mock_rns_minimal, temp_dir):
    from meshchatx.meshchat import ReticulumMeshChat

    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

    handler = None
    for route in app.get_routes():
        if route.path == "/api/v1/app/sessions" and route.method == "GET":
            handler = route.handler
            break
    assert handler is not None

    response = await handler(MagicMock())
    data = json.loads(response.body)
    assert data["count"] == 0
    assert data["sessions"] == []
    assert data["warning"] is False
    assert data["warning_enabled"] is True

    first = app.active_sessions.add(ip="127.0.0.1", user_agent="A/1")
    app.active_sessions.add(ip="10.0.0.5", user_agent="B/2")
    response = await handler(MagicMock())
    data = json.loads(response.body)
    assert data["count"] == 2
    assert data["warning"] is True
    assert {row["ip"] for row in data["sessions"]} == {"127.0.0.1", "10.0.0.5"}
    assert {row["user_agent"] for row in data["sessions"]} == {"A/1", "B/2"}
    assert any(row["id"] == first["id"] for row in data["sessions"])


@pytest.mark.asyncio
async def test_multi_session_warning_setting_in_config_and_payload(
    mock_rns_minimal,
    temp_dir,
):
    from meshchatx.meshchat import ReticulumMeshChat

    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

    assert app.config.multi_session_warning_enabled.get() is True
    assert app.get_config_dict()["multi_session_warning_enabled"] is True

    app.active_sessions.add(ip="1.1.1.1", user_agent="one")
    app.active_sessions.add(ip="2.2.2.2", user_agent="two")
    payload = app.get_active_sessions_payload()
    assert payload["warning"] is True

    app.config.multi_session_warning_enabled.set(False)
    payload = app.get_active_sessions_payload()
    assert payload["warning_enabled"] is False
    assert payload["warning"] is False

    app.config.multi_session_warning_enabled.set(True)
    with (
        patch.object(app, "send_config_to_websocket_clients", new_callable=AsyncMock),
        patch.object(
            app,
            "send_active_sessions_to_websocket_clients",
            new_callable=AsyncMock,
        ) as sessions_broadcast,
    ):
        await app.update_config({"multi_session_warning_enabled": False})
    assert app.config.multi_session_warning_enabled.get() is False
    sessions_broadcast.assert_awaited()


@pytest.mark.asyncio
async def test_detach_active_session_and_broadcast_payload(mock_rns_minimal, temp_dir):
    from meshchatx.meshchat import ReticulumMeshChat

    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

    entry = app.active_sessions.add(ip="::1", user_agent="UA")
    client = MagicMock()
    client._meshchatx_session_id = entry["id"]
    assert app._detach_active_session(client) is True
    assert app.active_sessions.count() == 0
    assert not hasattr(client, "_meshchatx_session_id")
    assert app._detach_active_session(client) is False

    sent = []

    async def capture(data):
        sent.append(json.loads(data))

    app.websocket_broadcast = capture
    app.active_sessions.add(ip="8.8.8.8", user_agent="Chrome")
    app.active_sessions.add(ip="9.9.9.9", user_agent="Firefox")
    await app.send_active_sessions_to_websocket_clients()
    assert len(sent) == 1
    assert sent[0]["type"] == "app.sessions.updated"
    assert sent[0]["count"] == 2
    assert sent[0]["warning"] is True


@pytest.mark.asyncio
async def test_websocket_broadcast_detaches_dead_session(mock_rns_minimal, temp_dir):
    from meshchatx.meshchat import ReticulumMeshChat

    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

    live = MagicMock()
    live.send_str = AsyncMock()
    live.close = AsyncMock()

    dead = MagicMock()
    dead.send_str = AsyncMock(side_effect=RuntimeError("gone"))
    dead.close = AsyncMock()
    dead_entry = app.active_sessions.add(ip="10.0.0.9", user_agent="Dead/1")
    dead._meshchatx_session_id = dead_entry["id"]
    live_entry = app.active_sessions.add(ip="10.0.0.8", user_agent="Live/1")
    live._meshchatx_session_id = live_entry["id"]

    app.websocket_clients = [live, dead]
    # Avoid recursive session broadcast while asserting detach bookkeeping.
    app.send_active_sessions_to_websocket_clients = AsyncMock()
    await app.websocket_broadcast('{"type":"ping"}')

    assert dead not in app.websocket_clients
    assert live in app.websocket_clients
    assert app.active_sessions.count() == 1
    assert app.active_sessions.list_sessions()[0]["id"] == live_entry["id"]
    app.send_active_sessions_to_websocket_clients.assert_awaited()


@pytest.mark.asyncio
async def test_connect_disconnect_session_lifecycle_unit(mock_rns_minimal, temp_dir):
    """Simulate the connect and disconnect bookkeeping without a live aiohttp WS."""
    from meshchatx.meshchat import ReticulumMeshChat

    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

    broadcasts = []

    async def capture(data):
        broadcasts.append(json.loads(data))

    app.websocket_broadcast = capture

    clients = []
    for ip, ua in (("127.0.0.1", "One"), ("127.0.0.1", "Two")):
        client = MagicMock()
        session = app.active_sessions.add(ip=ip, user_agent=ua)
        client._meshchatx_session_id = session["id"]
        app.websocket_clients.append(client)
        clients.append(client)
        await app.send_active_sessions_to_websocket_clients()

    assert app.active_sessions.count() == 2
    assert broadcasts[-1]["warning"] is True
    assert broadcasts[-1]["count"] == 2

    client = clients.pop()
    app.websocket_clients.remove(client)
    app._detach_active_session(client)
    await app.send_active_sessions_to_websocket_clients()
    assert app.active_sessions.count() == 1
    assert broadcasts[-1]["warning"] is False
    assert broadcasts[-1]["count"] == 1
