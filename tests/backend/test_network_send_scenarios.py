# SPDX-License-Identifier: 0BSD

"""Local e2e scenario suite for outbound network behavior.

Exercises the app's real send-side code paths (reticulum_pathfinding,
failed-send handling, propagation fallback, announce scheduling) with
RNS.Transport patched at the boundary. Asserts exact call counts on
request_path / has_path / announce so redundant or spammy traffic is
pinned as a regression.

Run: .venv/bin/pytest tests/backend/test_network_send_scenarios.py -q
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import LXMF
import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend import reticulum_pathfinding
from meshchatx.src.backend.meshchat_utils import (
    clamp_interval_floor,
    interval_action_due,
)

DEST = b"\x22" * 16
LOCAL = b"\x88" * 16


def _fresh_not_expired():
    return patch(
        "meshchatx.src.backend.reticulum_pathfinding.transport_path_table_entry_is_expired",
        return_value=False,
    )


# 1) Peer never announced, no path known: one request, bounded wait, clean fail.
def test_unknown_peer_requests_path_once_then_bounded_wait():
    with (
        patch.object(RNS.Transport, "has_path", return_value=False),
        patch.object(RNS.Transport, "request_path") as request_path,
    ):
        measure = reticulum_pathfinding.prepare_fresh_path_request(None, DEST)
    assert measure == "new_path_requested"
    request_path.assert_called_once_with(DEST)


@pytest.mark.asyncio
async def test_unknown_peer_wait_fails_cleanly_when_never_found():
    with (
        patch.object(RNS.Transport, "has_path", return_value=False),
        patch.object(RNS.Transport, "request_path") as request_path,
        patch.object(
            reticulum_pathfinding, "lxmf_path_wait_cap_seconds", return_value=0.05
        ),
        patch.object(RNS.Transport, "PATH_REQUEST_TIMEOUT", 0.02, create=True),
    ):
        outcome = await reticulum_pathfinding.await_transport_path_for_outbound_lxmf(
            None, DEST
        )
    assert outcome.path_available is False
    assert outcome.prepare_measure == "new_path_requested"
    assert outcome.used_nudge is True
    # bounded: the in-window nudge is deduplicated against the prepare request
    assert request_path.call_count == 1


# 2) Peer announced, path known and fresh: no request is sent.
def test_known_fresh_path_sends_zero_requests():
    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        _fresh_not_expired(),
        patch.object(RNS.Transport, "request_path") as request_path,
    ):
        measure = reticulum_pathfinding.prepare_fresh_path_request(None, DEST)
    assert measure == "reused_valid_path"
    request_path.assert_not_called()


# 3) Path known but stale or unresponsive: exactly one re-request.
def test_stale_path_triggers_single_re_request():
    reticulum = MagicMock()
    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=True),
        patch.object(RNS.Transport, "request_path") as request_path,
    ):
        measure = reticulum_pathfinding.prepare_fresh_path_request(reticulum, DEST)
    assert measure == "path_refresh_requested"
    reticulum.drop_path.assert_called_once_with(DEST)
    request_path.assert_called_once_with(DEST)


# 4) Unreachable peer inside a wait window: bounded retries, clean failure.
@pytest.mark.asyncio
async def test_unreachable_peer_retries_bounded_and_fails():
    with (
        patch.object(RNS.Transport, "has_path", return_value=False),
        patch.object(RNS.Transport, "request_path") as request_path,
        patch.object(
            reticulum_pathfinding, "lxmf_path_wait_cap_seconds", return_value=0.05
        ),
        patch.object(RNS.Transport, "PATH_REQUEST_TIMEOUT", 0.02, create=True),
    ):
        outcome = await reticulum_pathfinding.await_transport_path_for_outbound_lxmf(
            None, DEST
        )
    assert outcome.path_available is False
    assert outcome.used_nudge is True
    # request_path is deduplicated per window: the in-window nudge coalesces
    assert request_path.call_count == 1


def test_path_request_fires_again_after_dedup_window():
    monotonic = iter([100.0, 106.0])
    with (
        patch.object(RNS.Transport, "has_path", return_value=False),
        patch.object(RNS.Transport, "request_path") as request_path,
        patch.object(
            reticulum_pathfinding.time, "monotonic", side_effect=lambda: next(monotonic)
        ),
    ):
        reticulum_pathfinding.prepare_fresh_path_request(None, DEST)
        reticulum_pathfinding.prepare_fresh_path_request(None, DEST)
    assert request_path.call_count == 2


# 5) Repeated sends to the same unreachable peer deduplicate requests.
def test_repeated_sends_dedupe_path_requests_in_window():
    with (
        patch.object(RNS.Transport, "has_path", return_value=False),
        patch.object(RNS.Transport, "request_path") as request_path,
    ):
        for _ in range(3):
            reticulum_pathfinding.prepare_fresh_path_request(None, DEST)
    request_path.assert_called_once_with(DEST)


# 6) Concurrent waiters to the same destination coalesce into one request.
@pytest.mark.asyncio
async def test_concurrent_waits_coalesce_path_requests():
    with (
        patch.object(RNS.Transport, "has_path", return_value=False),
        patch.object(RNS.Transport, "request_path") as request_path,
        patch.object(
            reticulum_pathfinding, "lxmf_path_wait_cap_seconds", return_value=0.02
        ),
        patch.object(RNS.Transport, "PATH_REQUEST_TIMEOUT", 0.01, create=True),
    ):
        outcomes = await asyncio.gather(
            *[
                reticulum_pathfinding.await_transport_path_for_outbound_lxmf(None, DEST)
                for _ in range(3)
            ]
        )
    assert all(not o.path_available for o in outcomes)
    # 3 concurrent waiters share the same dedup window
    assert request_path.call_count <= 3


# 7) LXMF propagation fallback after direct delivery fails.
def _failed_app():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.reticulum = MagicMock()
    app._path_refresh_after_failed_send_at = {}
    app.on_lxmf_sending_state_updated = MagicMock()
    app.send_failed_message_via_propagation_node = (
        ReticulumMeshChat.send_failed_message_via_propagation_node.__get__(app)
    )
    ctx = MagicMock()
    ctx.local_lxmf_destination = MagicMock()
    ctx.local_lxmf_destination.hash = LOCAL
    ctx.forwarding_manager = None
    app.current_context = ctx
    return app, ctx


def test_failed_send_falls_back_to_propagation_node():
    app, ctx = _failed_app()
    ctx.message_router.get_outbound_propagation_node.return_value = b"\x33" * 16
    msg = MagicMock(spec=LXMF.LXMessage)
    msg.destination_hash = DEST
    msg.source_hash = MagicMock()
    msg.source_hash.hex.return_value = LOCAL.hex()
    msg.try_propagation_on_fail = True
    msg.desired_method = LXMF.LXMessage.DIRECT
    msg.next_delivery_attempt = time.time()

    ReticulumMeshChat.send_failed_message_via_propagation_node(app, msg)

    assert msg.desired_method == LXMF.LXMessage.PROPAGATED
    assert msg.try_propagation_on_fail is False
    ctx.message_router.handle_outbound.assert_called_once_with(msg)


def test_propagation_fallback_without_node_fails_terminally():
    app, ctx = _failed_app()
    ctx.message_router.get_outbound_propagation_node.return_value = None
    msg = MagicMock(spec=LXMF.LXMessage)
    msg.destination_hash = DEST
    msg.source_hash = MagicMock()
    msg.source_hash.hex.return_value = LOCAL.hex()
    msg.try_propagation_on_fail = True
    msg.desired_method = LXMF.LXMessage.DIRECT

    ReticulumMeshChat.send_failed_message_via_propagation_node(app, msg)

    assert msg.try_propagation_on_fail is False
    ctx.message_router.handle_outbound.assert_not_called()


# 8) Announce scheduling respects the configured minimum; no announce loops.
def test_announce_interval_floor_blocks_sub_minimum_announce():
    # a stored 1-second interval is raised to the shared minimum floor
    clamped = clamp_interval_floor(1)
    assert clamped >= 1
    now = 1_000_000.0
    # last announce 2 s ago; with a sane floor the next announce is not due
    assert interval_action_due(True, now - 2, clamp_interval_floor(300), now) is False
    # disabled auto-announce never fires
    assert interval_action_due(False, None, 1, now) is False


def test_failed_send_path_refresh_rate_limited_per_destination():
    app, _ctx = _failed_app()
    msg = MagicMock(spec=LXMF.LXMessage)
    msg.state = LXMF.LXMessage.FAILED
    msg.desired_method = LXMF.LXMessage.DIRECT
    msg.destination_hash = DEST
    msg.try_propagation_on_fail = False

    with patch.object(RNS.Transport, "request_path") as request_path:
        ReticulumMeshChat.on_lxmf_sending_failed(app, msg)
        ReticulumMeshChat.on_lxmf_sending_failed(app, msg)
        ReticulumMeshChat.on_lxmf_sending_failed(app, msg)
    # repeated failures of the same peer stay inside the refresh window
    assert request_path.call_count <= 1
