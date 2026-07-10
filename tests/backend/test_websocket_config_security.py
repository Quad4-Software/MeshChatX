# SPDX-License-Identifier: 0BSD

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meshchatx.src.backend.websocket_config_guard import (
    WEBSOCKET_MUTATOR_TYPES,
    WEBSOCKET_PUBLIC_TYPES,
    WEBSOCKET_READ_TYPES,
    websocket_type_requires_auth,
)


def _run_async_immediate(coro):
    return asyncio.create_task(coro)


def test_websocket_type_requires_auth_classifies_mutators():
    for msg_type in WEBSOCKET_MUTATOR_TYPES:
        assert websocket_type_requires_auth(msg_type) is True


def test_websocket_type_requires_auth_allows_ping_and_reads():
    for msg_type in WEBSOCKET_PUBLIC_TYPES | WEBSOCKET_READ_TYPES:
        assert websocket_type_requires_auth(msg_type) is False


@pytest.mark.asyncio
async def test_websocket_mutator_rejected_without_session_when_auth_enabled(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set("hash")
    client = MagicMock()
    client.request = MagicMock()
    client.send_str = AsyncMock()

    with (
        patch.object(mock_app, "_websocket_session_authorized", return_value=False),
        patch(
            "meshchatx.meshchat.AsyncUtils.run_async",
            side_effect=_run_async_immediate,
        ),
    ):
        await mock_app.on_websocket_data_received(
            client,
            {"type": "keyboard_shortcuts.set", "shortcuts": []},
        )
        await asyncio.sleep(0)

    client.send_str.assert_awaited_once()
    payload = client.send_str.await_args.args[0]
    assert '"Authentication required"' in payload


@pytest.mark.asyncio
async def test_websocket_session_authorized_uses_attached_request(mock_app):
    """Aiohttp WebSocketResponse has no .request; mutators must use the attached one."""
    mock_app.config.auth_enabled.set(True)
    identity_hash = "ab" * 16
    mock_app.identity = MagicMock()
    mock_app.identity.hash.hex.return_value = identity_hash

    client = MagicMock(spec=["send_str", "_meshchatx_request"])
    client._meshchatx_request = MagicMock()
    session = {"authenticated": True, "identity_hash": identity_hash}

    with patch("meshchatx.meshchat.get_session", AsyncMock(return_value=session)):
        assert await mock_app._websocket_session_authorized(client) is True


@pytest.mark.asyncio
async def test_websocket_session_authorized_false_without_attached_request(mock_app):
    mock_app.config.auth_enabled.set(True)
    client = MagicMock(spec=["send_str"])
    assert await mock_app._websocket_session_authorized(client) is False


@pytest.mark.asyncio
async def test_nomadnet_page_download_not_rejected_when_ws_request_attached(mock_app):
    mock_app.config.auth_enabled.set(True)
    identity_hash = "cd" * 16
    mock_app.identity = MagicMock()
    mock_app.identity.hash.hex.return_value = identity_hash

    client = MagicMock(spec=["send_str", "_meshchatx_request"])
    client._meshchatx_request = MagicMock()
    client.send_str = AsyncMock()
    session = {"authenticated": True, "identity_hash": identity_hash}

    with (
        patch("meshchatx.meshchat.get_session", AsyncMock(return_value=session)),
        patch(
            "meshchatx.meshchat.AsyncUtils.run_async",
            side_effect=_run_async_immediate,
        ),
    ):
        await mock_app.on_websocket_data_received(
            client,
            {
                "type": "nomadnet.page.download",
                # Intentionally incomplete payload: auth must pass before handler
                # returns early for missing nomadnet_page_download.
            },
        )
        await asyncio.sleep(0)

    for call in client.send_str.await_args_list:
        assert "Authentication required" not in call.args[0]
        assert "Rejected unauthorized" not in call.args[0]


@pytest.mark.asyncio
async def test_websocket_read_allowed_without_session_when_auth_enabled(mock_app):
    mock_app.config.auth_enabled.set(True)
    client = MagicMock()
    client.request = MagicMock()
    client.send_str = AsyncMock()

    with (
        patch.object(mock_app, "_websocket_session_authorized", return_value=False),
        patch.object(
            mock_app,
            "get_archived_page_versions",
            return_value=[],
        ),
        patch(
            "meshchatx.meshchat.AsyncUtils.run_async",
            side_effect=_run_async_immediate,
        ),
    ):
        await mock_app.on_websocket_data_received(
            client,
            {
                "type": "nomadnet.page.archives.get",
                "destination_hash": "aa" * 16,
                "page_path": "index.mu",
            },
        )
        await asyncio.sleep(0)

    client.send_str.assert_awaited()


@pytest.mark.asyncio
async def test_websocket_config_set_ignores_auth_enabled(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set("existing-hash")

    client = object()
    with patch.object(mock_app, "_websocket_session_authorized", return_value=True):
        await mock_app.on_websocket_data_received(
            client,
            {
                "type": "config.set",
                "config": {
                    "display_name": "Updated Peer",
                    "auth_enabled": False,
                    "auth_password_hash": None,
                },
            },
        )

    assert mock_app.config.auth_enabled.get() is True
    assert mock_app.config.auth_password_hash.get() == "existing-hash"
    assert mock_app.config.display_name.get() == "Updated Peer"
