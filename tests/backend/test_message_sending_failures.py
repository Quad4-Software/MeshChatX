# SPDX-License-Identifier: 0BSD

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import LXMF
import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.reticulum_pathfinding import OutboundPathOutcome


@pytest.fixture
def mock_app():
    # Use __new__ to avoid full initialization
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.current_context = MagicMock()
    app.config = MagicMock()
    app.database = MagicMock()
    app.reticulum = MagicMock()
    app.message_router = MagicMock()
    app._await_transport_path = AsyncMock(
        return_value=OutboundPathOutcome(True, "reused_valid_path", False),
    )
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
async def test_oracle_path_wait_uses_lxmf_delivery_hash_not_identity_hash(mock_app):
    """Pasting an identity hash must wait on lxmf.delivery, not the identity hash."""
    ident = RNS.Identity()
    identity_hex = ident.hash.hex()
    delivery = RNS.Destination.hash(ident, "lxmf", "delivery")
    assert ident.hash != delivery
    mock_app.recall_identity = MagicMock(return_value=ident)
    mock_app._await_transport_path = AsyncMock(
        return_value=OutboundPathOutcome(False, "new_path_requested", True),
    )
    mock_app._is_self_lxmf_destination = MagicMock(return_value=False)
    with pytest.raises(TimeoutError, match="No path to destination"):
        await mock_app.send_message(
            destination_hash=identity_hex,
            content="hi",
            delivery_method="direct",
        )
    mock_app._await_transport_path.assert_awaited_once_with(delivery)
    mock_app.message_router.handle_outbound.assert_not_called()
    print("LXMF_IDENTITY_HASH_PATH_WAIT_ORACLE_PROVED")


@pytest.mark.asyncio
async def test_oracle_path_wait_keeps_lxmf_delivery_hash(mock_app):
    ident = RNS.Identity()
    delivery = RNS.Destination.hash(ident, "lxmf", "delivery")
    mock_app.recall_identity = MagicMock(return_value=ident)
    mock_app._await_transport_path = AsyncMock(
        return_value=OutboundPathOutcome(False, "new_path_requested", True),
    )
    mock_app._is_self_lxmf_destination = MagicMock(return_value=False)
    with pytest.raises(TimeoutError, match="No path to destination"):
        await mock_app.send_message(
            destination_hash=delivery.hex(),
            content="hi",
            delivery_method="direct",
        )
    mock_app._await_transport_path.assert_awaited_once_with(delivery)


@pytest.mark.asyncio
async def test_send_message_recall_fails_before_path_wait(mock_app):
    destination_hash = "aa" * 16
    mock_app.recall_identity = MagicMock(return_value=None)
    with pytest.raises(LookupError, match="Could not recall destination identity"):
        await mock_app.send_message(
            destination_hash=destination_hash,
            content="hi",
        )
    mock_app._await_transport_path.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_message_blocks_when_path_unavailable(mock_app):
    destination_hash = "aa" * 16
    fake_identity = MagicMock()
    mock_app.recall_identity = MagicMock(return_value=fake_identity)
    mock_app._await_transport_path = AsyncMock(
        return_value=OutboundPathOutcome(False, "new_path_requested", True),
    )
    with pytest.raises(TimeoutError, match="No path to destination"):
        await mock_app.send_message(
            destination_hash=destination_hash,
            content="hi",
            delivery_method="direct",
        )
    mock_app.message_router.handle_outbound.assert_not_called()


@pytest.mark.asyncio
async def test_send_message_propagated_allows_missing_peer_path(mock_app):
    destination_hash = "aa" * 16
    fake_identity = MagicMock()
    mock_app.recall_identity = MagicMock(return_value=fake_identity)
    mock_app._await_transport_path = AsyncMock(
        return_value=OutboundPathOutcome(False, "new_path_requested", True),
    )
    mock_app.config.auto_send_failed_messages_to_propagation_node.get.return_value = (
        False
    )
    mock_app.config.include_display_name_with_message.get.return_value = False
    mock_app.config.include_icon_with_message.get.return_value = False
    mock_app.config.include_signature_with_message.get.return_value = False
    mock_msg = MagicMock()
    mock_msg.hash = b"\x01" * 16
    mock_msg.fields = {}
    with (
        patch("meshchatx.meshchat.RNS.Destination", return_value=MagicMock()),
        patch("meshchatx.meshchat.LXMF.LXMessage", return_value=mock_msg),
        patch("meshchatx.meshchat.RNS.Identity.current_ratchet_id", return_value=None),
        patch(
            "meshchatx.meshchat.convert_lxmf_message_to_dict",
            return_value={"hash": "01" * 16, "state": "outbound"},
        ),
    ):
        result = await mock_app.send_message(
            destination_hash=destination_hash,
            content="hi",
            delivery_method="propagated",
        )
    assert result is mock_msg
    mock_app.message_router.handle_outbound.assert_called_once()
    mock_app._await_transport_path.assert_not_called()


@pytest.mark.asyncio
async def test_send_message_immediate_exception_in_router(mock_app):
    destination_hash = "aa" * 16
    fake_identity = MagicMock()

    mock_app.message_router.handle_outbound.side_effect = Exception("Router failure")

    mock_app.recall_identity = MagicMock(return_value=fake_identity)
    with (
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
        mock_msg,
        context=mock_app.current_context,
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
        mock_msg,
        context=mock_app.current_context,
    )
    mock_app.on_lxmf_sending_state_updated.assert_called_once_with(
        mock_msg,
        context=mock_app.current_context,
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
            "meshchatx.meshchat.convert_lxmf_method_to_string",
            return_value="direct",
        ),
        patch(
            "meshchatx.meshchat.convert_lxmf_message_to_dict",
            return_value={"hash": "hex", "state": "failed"},
        ),
        patch("asyncio.sleep", return_value=asyncio.Future()) as mock_sleep,
    ):
        mock_sleep.return_value.set_result(None)

        from meshchatx.meshchat import ReticulumMeshChat

        await ReticulumMeshChat.handle_lxmf_message_progress(
            mock_app,
            mock_msg,
            context=mock_app.current_context,
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
async def test_handle_lxmf_message_progress_continues_while_propagation_fallback_pending(
    mock_app,
):
    mock_msg = MagicMock()
    mock_msg.hash = MagicMock()
    mock_msg.hash.hex.return_value = "msg_hash_hex"
    mock_msg.progress = 0.0
    mock_msg.delivery_attempts = 1
    mock_msg.try_propagation_on_fail = True
    mock_msg.state = LXMF.LXMessage.FAILED
    mock_msg.method = LXMF.LXMessage.DIRECT

    iteration = 0

    async def counting_sleep(_duration):
        nonlocal iteration
        iteration += 1
        if iteration == 2:
            mock_msg.try_propagation_on_fail = False
            mock_msg.state = LXMF.LXMessage.SENT
            mock_msg.method = LXMF.LXMessage.PROPAGATED

    def state_to_str(msg):
        if msg.state == LXMF.LXMessage.FAILED:
            return "failed"
        if msg.state == LXMF.LXMessage.SENT:
            return "sent"
        return "unknown"

    with (
        patch(
            "meshchatx.meshchat.convert_lxmf_state_to_string",
            side_effect=state_to_str,
        ),
        patch(
            "meshchatx.meshchat.convert_lxmf_method_to_string",
            side_effect=lambda m: (
                "propagated" if m.method == LXMF.LXMessage.PROPAGATED else "direct"
            ),
        ),
        patch(
            "meshchatx.meshchat.convert_lxmf_message_to_dict",
            side_effect=lambda *a, **k: {
                "hash": "hex",
                "state": "failed" if a[0].state == LXMF.LXMessage.FAILED else "sent",
            },
        ),
        patch("asyncio.sleep", side_effect=counting_sleep),
    ):
        from meshchatx.meshchat import ReticulumMeshChat

        await ReticulumMeshChat.handle_lxmf_message_progress(
            mock_app,
            mock_msg,
            context=mock_app.current_context,
        )

    assert iteration == 2
    # Initial failed update, one more while propagation fallback is still pending,
    # then the final propagated update after the second sleep.
    assert mock_app.database.messages.update_lxmf_message_state.call_count == 3


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
    mock_app._await_transport_path = AsyncMock(
        return_value=OutboundPathOutcome(False, "new_path_requested", True),
    )
    destination_hash = "aa" * 16
    fake_identity = MagicMock()
    mock_app.recall_identity = MagicMock(return_value=fake_identity)

    with pytest.raises(TimeoutError, match="No path to destination"):
        await mock_app.send_message(
            destination_hash=destination_hash,
            content="hi",
        )
