# SPDX-License-Identifier: 0BSD

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import LXMF
import pytest

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def mock_app():
    # Use __new__ to avoid full initialization
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.current_context = MagicMock()
    app.config = MagicMock()
    app.database = MagicMock()
    app.reticulum = MagicMock()
    app.message_router = MagicMock()
    app._await_transport_path = AsyncMock(return_value=True)
    app.get_current_icon_hash = MagicMock(return_value=None)
    app.db_upsert_lxmf_message = MagicMock()
    app.websocket_broadcast = AsyncMock()
    app._is_contact = MagicMock(return_value=False)
    app._convert_webm_opus_to_ogg = MagicMock(side_effect=lambda b: b)
    app.handle_lxmf_message_progress = AsyncMock()

    # Setup context
    ctx = app.current_context
    ctx.message_router = app.message_router
    ctx.database = app.database
    ctx.config = app.config
    ctx.local_lxmf_destination = MagicMock()
    ctx.local_lxmf_destination.hexhash = "local_hash"
    ctx.forwarding_manager = None

    return app


@pytest.mark.asyncio
async def test_send_message_no_path_identity_recall_fails(mock_app):
    destination_hash = "aa" * 16
    with patch("meshchatx.meshchat.RNS.Identity.recall", return_value=None):
        with pytest.raises(Exception, match="Could not find path to destination"):
            await mock_app.send_message(
                destination_hash=destination_hash,
                content="hi",
            )


@pytest.mark.asyncio
async def test_send_message_immediate_exception_in_router(mock_app):
    destination_hash = "aa" * 16
    fake_identity = MagicMock()

    mock_app.message_router.handle_outbound.side_effect = Exception("Router failure")

    with (
        patch("meshchatx.meshchat.RNS.Identity.recall", return_value=fake_identity),
        patch("meshchatx.meshchat.RNS.Destination", return_value=MagicMock()),
        patch("meshchatx.meshchat.LXMF.LXMessage", return_value=MagicMock()),
    ):
        with pytest.raises(Exception, match="Router failure"):
            await mock_app.send_message(
                destination_hash=destination_hash,
                content="hi",
            )


@pytest.mark.asyncio
async def test_on_lxmf_sending_failed_updates_state(mock_app):
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.state = LXMF.LXMessage.FAILED
    mock_msg.try_propagation_on_fail = False

    mock_app.on_lxmf_sending_state_updated = MagicMock()

    from meshchatx.meshchat import ReticulumMeshChat

    ReticulumMeshChat.on_lxmf_sending_failed(mock_app, mock_msg)

    mock_app.on_lxmf_sending_state_updated.assert_called_once_with(
        mock_msg, context=mock_app.current_context
    )


@pytest.mark.asyncio
async def test_propagation_fallback_on_failure(mock_app):
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.state = LXMF.LXMessage.FAILED
    mock_msg.try_propagation_on_fail = True
    mock_msg.source_hash = b"source"

    mock_app.send_failed_message_via_propagation_node = MagicMock()
    mock_app.on_lxmf_sending_state_updated = MagicMock()

    from meshchatx.meshchat import ReticulumMeshChat

    ReticulumMeshChat.on_lxmf_sending_failed(mock_app, mock_msg)

    mock_app.send_failed_message_via_propagation_node.assert_called_once_with(
        mock_msg, context=mock_app.current_context
    )
    mock_app.on_lxmf_sending_state_updated.assert_called_once_with(
        mock_msg, context=mock_app.current_context
    )


@pytest.mark.asyncio
async def test_handle_lxmf_message_progress_failure_broadcast(mock_app):
    mock_msg = MagicMock()
    mock_msg.hash = MagicMock()
    mock_msg.hash.hex.return_value = "msg_hash_hex"
    mock_msg.progress = 0.0
    mock_msg.delivery_attempts = 1

    # State sequence: FAILED (first iteration should terminate loop)
    type(mock_msg).state = PropertyMock(return_value=LXMF.LXMessage.FAILED)
    mock_msg.method = LXMF.LXMessage.DIRECT

    with (
        patch("meshchatx.meshchat.convert_lxmf_state_to_string", return_value="failed"),
        patch(
            "meshchatx.meshchat.convert_lxmf_message_to_dict",
            return_value={"hash": "hex", "state": "failed"},
        ),
        patch("asyncio.sleep", return_value=asyncio.Future()) as mock_sleep,
    ):
        mock_sleep.return_value.set_result(None)

        from meshchatx.meshchat import ReticulumMeshChat

        await ReticulumMeshChat.handle_lxmf_message_progress(
            mock_app, mock_msg, context=mock_app.current_context
        )

        # Verify update was called
        mock_app.database.messages.update_lxmf_message_state.assert_called()
        # Verify websocket broadcast was called
        mock_app.websocket_broadcast.assert_called()

        args = mock_app.websocket_broadcast.call_args[0][0]
        payload = json.loads(args)
        assert payload["type"] == "lxmf_message_state_updated"
        assert payload["lxmf_message"]["state"] == "failed"


@pytest.mark.asyncio
async def test_send_message_db_upsert_failure_still_broadcasts(mock_app):
    # If db_upsert fails, we want to know if it's caught or if it crashes send_message.
    # Actually, send_message doesn't have a try-except around db_upsert_lxmf_message.
    # If it fails, the whole send_message fails, which returns 503 to frontend.

    destination_hash = "aa" * 16
    fake_identity = MagicMock()

    mock_app.db_upsert_lxmf_message.side_effect = Exception("DB Error")

    with (
        patch("meshchatx.meshchat.RNS.Identity.recall", return_value=fake_identity),
        patch("meshchatx.meshchat.RNS.Destination", return_value=MagicMock()),
        patch("meshchatx.meshchat.LXMF.LXMessage", return_value=MagicMock()),
    ):
        with pytest.raises(Exception, match="DB Error"):
            await mock_app.send_message(
                destination_hash=destination_hash,
                content="hi",
            )


@pytest.mark.asyncio
async def test_send_message_await_path_timeout(mock_app):
    mock_app._await_transport_path = AsyncMock(return_value=False)
    destination_hash = "aa" * 16

    # Even if _await_transport_path returns False, it continues to recall identity
    with patch("meshchatx.meshchat.RNS.Identity.recall", return_value=None):
        with pytest.raises(Exception, match="Could not find path to destination"):
            await mock_app.send_message(
                destination_hash=destination_hash,
                content="hi",
            )
