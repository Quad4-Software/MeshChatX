# SPDX-License-Identifier: 0BSD

"""Security oracles for cross-origin WebSocket access and the FileSync sync-root jail.

Invariants under test:

1. A WebSocket upgrade whose Origin is not the local backend origin must be
   rejected, regardless of whether HTTP auth is enabled.
2. A cross-origin WebSocket client with no session must not mutate server state.
3. The FileSync sync directory must never resolve to a sensitive identity-tree
   directory such as ssl (TLS key material), while ordinary subdirectories
   remain selectable.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import WSMsgType, WSServerHandshakeError
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.rns_filesync_handler import RnsFilesyncHandler
from tests.backend.test_http_auth_security import _make_aio_app

EVIL_ORIGIN = "https://evil.example"


def _patch_ws_broadcasts(mock_app):
    mock_app.send_config_to_websocket_clients = AsyncMock()
    mock_app.send_active_sessions_to_websocket_clients = AsyncMock()


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_ws_upgrade_rejects_cross_site_origin(mock_app):
    """Invariant 1: hostile Origin must not complete the /ws upgrade."""
    _patch_ws_broadcasts(mock_app)
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        with pytest.raises(WSServerHandshakeError):
            await client.ws_connect("/ws", origin=EVIL_ORIGIN)


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_telephone_audio_ws_rejects_cross_site_origin(mock_app):
    """Invariant 1 also covers /ws/telephone/audio."""
    _patch_ws_broadcasts(mock_app)
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        with pytest.raises(WSServerHandshakeError):
            await client.ws_connect("/ws/telephone/audio", origin=EVIL_ORIGIN)


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_cross_origin_ws_mutator_does_not_change_state(mock_app):
    """Invariant 2: no session and hostile Origin means no state mutation."""
    _patch_ws_broadcasts(mock_app)
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        try:
            ws = await client.ws_connect("/ws", origin=EVIL_ORIGIN)
        except Exception:
            return

        probe_action = "oracle_cross_origin_probe"
        await ws.send_str(
            json.dumps(
                {
                    "type": "keyboard_shortcuts.set",
                    "action": probe_action,
                    "keys": ["ctrl+alt+9"],
                },
            ),
        )
        try:
            while True:
                msg = await ws.receive(timeout=2)
                if msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                    break
                if msg.type == WSMsgType.TEXT and "keyboard_shortcuts" in msg.data:
                    break
        except TimeoutError:
            pass

        stored = mock_app.database.misc.get_keyboard_shortcuts(
            mock_app.identity.hash.hex(),
        )
        assert all(s["action"] != probe_action for s in stored)


def _make_filesync_handler(tmp_path):
    storage = tmp_path / "identity-storage"
    storage.mkdir()
    return RnsFilesyncHandler(
        reticulum_instance=MagicMock(),
        identity=MagicMock(),
        storage_dir=str(storage),
    ), storage


def test_filesync_sync_dir_rejects_identity_ssl_dir(tmp_path):
    """Invariant 3: ssl holds the identity TLS key and must not be syncable."""
    handler, storage = _make_filesync_handler(tmp_path)
    target = os.path.join(str(storage), "ssl")
    os.makedirs(target, exist_ok=True)
    assert handler._resolve_sync_directory(target) is None


def test_filesync_sync_dir_rejects_identity_root_and_escape(tmp_path):
    """Controls: identity root and sibling escape stay rejected today."""
    handler, storage = _make_filesync_handler(tmp_path)
    assert handler._resolve_sync_directory(str(storage)) is None
    sibling = os.path.join(str(storage), "..", "other-identity")
    assert handler._resolve_sync_directory(sibling) is None


def test_filesync_sync_dir_allows_plain_subdirectory(tmp_path):
    """Control: an ordinary identity-storage subdirectory stays selectable."""
    handler, storage = _make_filesync_handler(tmp_path)
    target = os.path.join(str(storage), "shared-docs")
    os.makedirs(target, exist_ok=True)
    assert handler._resolve_sync_directory(target) is not None
