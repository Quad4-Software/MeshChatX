# SPDX-License-Identifier: 0BSD
"""MissingPathPack: recoverable path outcomes for direct vs propagated send."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.reticulum_pathfinding import OutboundPathOutcome
from tests.backend.eect.asserts import assert_recoverable_missing_path
from tests.backend.eect.harness import eect_scenario

pytestmark = pytest.mark.eect


@pytest.fixture
def send_app():
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
    ctx = app.current_context
    ctx.message_router = app.message_router
    ctx.database = app.database
    ctx.config = app.config
    ctx.local_lxmf_destination = MagicMock()
    ctx.local_lxmf_destination.hexhash = "local_hash"
    ctx.forwarding_manager = None
    return app


@pytest.mark.asyncio
async def test_eect_direct_blocks_when_path_unavailable(send_app):
    with eect_scenario("path.direct.blocks_when_unavailable") as (_s, _seed, _rng):
        destination_hash = "aa" * 16
        send_app.recall_identity = MagicMock(return_value=MagicMock())
        send_app._await_transport_path = AsyncMock(
            return_value=OutboundPathOutcome(False, "new_path_requested", True),
        )
        with pytest.raises(TimeoutError) as caught:
            await send_app.send_message(
                destination_hash=destination_hash,
                content="hi",
                delivery_method="direct",
            )
        assert_recoverable_missing_path(caught.value)
        send_app.message_router.handle_outbound.assert_not_called()


@pytest.mark.asyncio
async def test_eect_propagated_skips_path_await(send_app):
    with eect_scenario("path.propagated.skips_await") as (_s, _seed, _rng):
        destination_hash = "aa" * 16
        send_app.recall_identity = MagicMock(return_value=MagicMock())
        send_app._await_transport_path = AsyncMock(
            return_value=OutboundPathOutcome(False, "new_path_requested", True),
        )
        send_app.config.auto_send_failed_messages_to_propagation_node.get.return_value = False
        send_app.config.include_display_name_with_message.get.return_value = False
        send_app.config.include_icon_with_message.get.return_value = False
        send_app.config.include_signature_with_message.get.return_value = False
        mock_msg = MagicMock()
        mock_msg.hash = b"\x01" * 16
        mock_msg.fields = {}
        with (
            patch("meshchatx.meshchat.RNS.Destination", return_value=MagicMock()),
            patch("meshchatx.meshchat.LXMF.LXMessage", return_value=mock_msg),
            patch(
                "meshchatx.meshchat.RNS.Identity.current_ratchet_id",
                return_value=None,
            ),
            patch(
                "meshchatx.meshchat.convert_lxmf_message_to_dict",
                return_value={"hash": "01" * 16, "state": "outbound"},
            ),
        ):
            result = await send_app.send_message(
                destination_hash=destination_hash,
                content="hi",
                delivery_method="propagated",
            )
        assert result is mock_msg
        send_app.message_router.handle_outbound.assert_called_once()
        send_app._await_transport_path.assert_not_called()
