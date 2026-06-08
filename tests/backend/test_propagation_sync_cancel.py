# SPDX-License-Identifier: 0BSD

import asyncio
import threading
from unittest.mock import MagicMock, patch

import LXMF
import pytest

from meshchatx.meshchat import ReticulumMeshChat

PR_IDLE = LXMF.LXMRouter.PR_IDLE
PR_LINK_ESTABLISHING = LXMF.LXMRouter.PR_LINK_ESTABLISHING
PR_PATH_REQUESTED = LXMF.LXMRouter.PR_PATH_REQUESTED


@pytest.mark.asyncio
async def test_request_propagation_node_messages_handles_eof_error():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    router = MagicMock()
    router.PR_IDLE = PR_IDLE
    router.propagation_transfer_state = PR_LINK_ESTABLISHING
    router.request_messages_from_propagation_node.side_effect = EOFError()
    ctx.message_router = router
    ctx.identity = MagicMock()

    with patch.object(app, "send_config_to_websocket_clients", return_value=None):
        await app._request_propagation_node_messages(context=ctx)

    assert router.propagation_transfer_state == PR_IDLE
    assert router.propagation_transfer_progress == 0.0


def test_stop_propagation_node_sync_forces_idle_when_cancel_leaves_active_state():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    router = MagicMock()
    router.PR_IDLE = PR_IDLE
    router.PR_PATH_REQUESTED = PR_PATH_REQUESTED
    router.PR_LINK_ESTABLISHING = PR_LINK_ESTABLISHING
    router.PR_LINK_ESTABLISHED = LXMF.LXMRouter.PR_LINK_ESTABLISHED
    router.PR_REQUEST_SENT = LXMF.LXMRouter.PR_REQUEST_SENT
    router.PR_RECEIVING = LXMF.LXMRouter.PR_RECEIVING
    router.PR_RESPONSE_RECEIVED = LXMF.LXMRouter.PR_RESPONSE_RECEIVED
    router.propagation_transfer_state = PR_PATH_REQUESTED
    ctx.message_router = router

    app.stop_propagation_node_sync(context=ctx)

    router.cancel_propagation_node_requests.assert_called_once()
    assert router.propagation_transfer_state == PR_IDLE
    assert router.propagation_transfer_progress == 0.0


@pytest.mark.asyncio
async def test_sync_propagation_nodes_returns_before_request_thread_finishes():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    router = MagicMock()
    router.PR_IDLE = PR_IDLE
    router.PR_COMPLETE = LXMF.LXMRouter.PR_COMPLETE
    router.propagation_transfer_state = PR_IDLE
    router.get_outbound_propagation_node.return_value = b"\x22" * 16
    router.propagation_destination = MagicMock(hash=b"\x11" * 16)
    ctx.message_router = router
    ctx.identity = MagicMock()
    ctx.config = MagicMock()
    ctx.database = MagicMock()
    ctx.database.messages.count_lxmf_messages.return_value = 0
    ctx.database.messages.count_lxmf_messages_by_state.return_value = 0

    request_started = threading.Event()
    request_finished = threading.Event()

    def slow_request(_identity):
        request_started.set()
        request_finished.wait(timeout=5.0)

    router.request_messages_from_propagation_node.side_effect = slow_request

    with (
        patch.object(app, "_begin_propagation_sync_metrics"),
        patch.object(app, "send_config_to_websocket_clients", return_value=None),
    ):
        await app.sync_propagation_nodes(context=ctx, force=False)
        await asyncio.sleep(0.05)
        assert request_started.is_set()
        assert not request_finished.is_set()

    request_finished.set()
    await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_sync_propagation_nodes_skips_without_outbound_node():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    router = MagicMock()
    router.PR_IDLE = PR_IDLE
    router.PR_COMPLETE = LXMF.LXMRouter.PR_COMPLETE
    router.propagation_transfer_state = PR_IDLE
    router.get_outbound_propagation_node.return_value = None
    ctx.message_router = router
    ctx.config = MagicMock()

    started = await app.sync_propagation_nodes(context=ctx, force=False)

    assert started is False
    ctx.config.lxmf_preferred_propagation_node_last_synced_at.set.assert_not_called()


@pytest.mark.asyncio
async def test_sync_propagation_nodes_restarts_after_complete_state():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    router = MagicMock()
    router.PR_IDLE = PR_IDLE
    router.PR_COMPLETE = LXMF.LXMRouter.PR_COMPLETE
    router.propagation_transfer_state = LXMF.LXMRouter.PR_COMPLETE
    router.get_outbound_propagation_node.return_value = b"\x22" * 16
    router.propagation_destination = MagicMock(hash=b"\x11" * 16)
    ctx.message_router = router
    ctx.identity = MagicMock()
    ctx.config = MagicMock()
    ctx.database = MagicMock()
    ctx.database.messages.count_lxmf_messages.return_value = 0
    ctx.database.messages.count_lxmf_messages_by_state.return_value = 0

    with (
        patch.object(app, "_begin_propagation_sync_metrics"),
        patch.object(app, "send_config_to_websocket_clients", return_value=None),
        patch.object(app, "_request_propagation_node_messages", return_value=None),
    ):
        started = await app.sync_propagation_nodes(context=ctx, force=False)

    assert started is True
    assert router.propagation_transfer_state == PR_IDLE


@pytest.mark.asyncio
async def test_announce_sync_propagation_nodes_clears_on_failure_state():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.running = True
    ctx = MagicMock()
    ctx.running = True
    ctx.session_id = "session-1"
    router = MagicMock()
    router.PR_IDLE = PR_IDLE
    router.PR_COMPLETE = LXMF.LXMRouter.PR_COMPLETE
    router.PR_PATH_REQUESTED = PR_PATH_REQUESTED
    router.PR_FAILED = LXMF.LXMRouter.PR_FAILED
    router.get_outbound_propagation_node.return_value = b"\x22" * 16
    router.propagation_transfer_state = LXMF.LXMRouter.PR_FAILED
    ctx.message_router = router
    ctx.config = MagicMock()
    ctx.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get.return_value = 3600
    ctx.config.lxmf_preferred_propagation_node_last_synced_at.get.return_value = 0

    loop_calls = {"count": 0}

    async def fake_sleep(_seconds):
        loop_calls["count"] += 1
        if loop_calls["count"] >= 2:
            ctx.running = False

    with (
        patch.object(app, "sync_propagation_nodes", return_value=True),
        patch.object(app, "stop_propagation_node_sync") as mock_stop,
        patch.object(app, "send_config_to_websocket_clients", return_value=None),
        patch("meshchatx.meshchat.asyncio.sleep", side_effect=fake_sleep),
        patch("meshchatx.meshchat.RNS.Transport.has_path", return_value=False),
    ):
        await app.announce_sync_propagation_nodes("session-1", context=ctx)

    mock_stop.assert_called_once_with(context=ctx)
    assert router.propagation_transfer_state == PR_IDLE
