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
