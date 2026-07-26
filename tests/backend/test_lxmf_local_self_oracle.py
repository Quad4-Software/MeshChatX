# SPDX-License-Identifier: 0BSD
"""Oracles and adversarial cases for local (self) LXMF messaging.

Invariant: destination equal to local LXMF, identity, or resolving to local LXMF
must persist as delivered/local without LXMF router outbound. Any other
destination must use the mesh path when send succeeds.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend import reticulum_pathfinding
from tests.backend.lxmf_local_self_support import (
    LOCAL_LXMF,
    REMOTE_PEER,
    fake_lxmf_message,
    lxmf_message_factory,
)


@pytest.mark.parametrize(
    ("dest", "expected"),
    [
        (LOCAL_LXMF, True),
        (LOCAL_LXMF.upper(), True),
        (REMOTE_PEER, False),
        ("", False),
    ],
)
def test_is_self_lxmf_param_oracle(local_self_app, dest, expected):
    app = local_self_app
    assert app._is_self_lxmf_destination(dest) is expected


def test_is_self_lxmf_identity_hash_oracle(local_self_app):
    app = local_self_app
    identity_hex = app.current_context.identity.hash.hex()
    assert app._is_self_lxmf_destination(identity_hex) is True


@pytest.mark.parametrize(
    "dest",
    [
        REMOTE_PEER,
        "f0" * 16,
        "deadbeef" * 4,
        "0123456789abcdef0123456789abcdef",
    ],
)
def test_is_self_false_for_unrelated_peers(local_self_app, dest):
    app = local_self_app
    identity = app.current_context.identity.hash.hex().lower()
    assert dest.lower() not in {LOCAL_LXMF.lower(), identity}
    app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=None)
    assert app._is_self_lxmf_destination(dest) is False


@pytest.mark.asyncio
async def test_local_self_sqlite_row_delivered_local(local_self_app):
    """End-to-end persist: real db_upsert, not a mock."""
    app = local_self_app
    fake_destination = MagicMock()
    fake_destination.hash = bytes.fromhex(LOCAL_LXMF)

    with (
        patch("meshchatx.meshchat.RNS.Destination", return_value=fake_destination),
        patch("meshchatx.meshchat.LXMF.LXMessage", side_effect=lxmf_message_factory),
        patch(
            "meshchatx.src.backend.lxmf_utils.lxmf_message_solving_stamps",
            return_value=False,
        ),
        patch("meshchatx.meshchat.AsyncUtils.run_async") as run_async,
    ):
        await app.send_message(destination_hash=LOCAL_LXMF, content="oracle persist")

    run_async.assert_not_called()
    row = app.database.provider.fetchone(
        "SELECT state, method, peer_hash, content FROM lxmf_messages WHERE content = ?",
        ("oracle persist",),
    )
    assert row is not None
    assert row["state"] == "delivered"
    assert row["method"] == "local"
    assert row["peer_hash"] == LOCAL_LXMF


@pytest.mark.asyncio
async def test_local_self_conversation_summary_updated(local_self_app):
    app = local_self_app
    fake_destination = MagicMock()
    fake_destination.hash = bytes.fromhex(LOCAL_LXMF)

    with (
        patch("meshchatx.meshchat.RNS.Destination", return_value=fake_destination),
        patch("meshchatx.meshchat.LXMF.LXMessage", side_effect=lxmf_message_factory),
        patch(
            "meshchatx.src.backend.lxmf_utils.lxmf_message_solving_stamps",
            return_value=False,
        ),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        await app.send_message(destination_hash=LOCAL_LXMF, content="summary row")

    summary = app.database.provider.fetchone(
        "SELECT state, content_preview FROM lxmf_conversation_summaries WHERE peer_hash = ?",
        (LOCAL_LXMF,),
    )
    assert summary is not None
    assert summary["state"] == "delivered"
    assert "summary row" in (summary["content_preview"] or "")


@pytest.mark.asyncio
async def test_remote_peer_still_invokes_mesh_outbound(local_self_app):
    app = local_self_app
    fake_destination = MagicMock()
    fake_destination.hash = bytes.fromhex(REMOTE_PEER)

    app._await_transport_path = AsyncMock(
        return_value=reticulum_pathfinding.OutboundPathOutcome(
            True,
            "reused_valid_path",
            False,
        ),
    )
    app.db_upsert_lxmf_message = MagicMock()
    progress = AsyncMock()
    app.handle_lxmf_message_progress = progress

    with (
        patch("meshchatx.meshchat.RNS.Destination", return_value=fake_destination),
        patch("meshchatx.meshchat.LXMF.LXMessage", side_effect=lxmf_message_factory),
        patch(
            "meshchatx.src.backend.lxmf_utils.lxmf_message_solving_stamps",
            return_value=False,
        ),
        patch("meshchatx.meshchat.AsyncUtils.run_async") as run_async,
    ):
        await app.send_message(destination_hash=REMOTE_PEER, content="to peer")

    app._await_transport_path.assert_awaited()
    app.current_context.message_router.handle_outbound.assert_called_once()
    run_async.assert_called_once()
    upsert_kw = app.db_upsert_lxmf_message.call_args.kwargs
    assert upsert_kw.get("method_override") is None
    assert upsert_kw.get("state_override") is None


def test_db_upsert_override_writes_local_method(local_self_app):
    app = local_self_app
    msg = fake_lxmf_message()
    msg.content = b"stored"
    ReticulumMeshChat.db_upsert_lxmf_message(
        app,
        msg,
        state_override="delivered",
        method_override="local",
    )
    row = app.database.provider.fetchone(
        "SELECT state, method FROM lxmf_messages WHERE hash = ?",
        ("d4" * 16,),
    )
    assert row is not None
    assert row["state"] == "delivered"
    assert row["method"] == "local"


@pytest.mark.asyncio
async def test_local_self_websocket_payload_is_delivered_local(local_self_app):
    app = local_self_app
    fake_destination = MagicMock()
    fake_destination.hash = bytes.fromhex(LOCAL_LXMF)

    with (
        patch("meshchatx.meshchat.RNS.Destination", return_value=fake_destination),
        patch("meshchatx.meshchat.LXMF.LXMessage", side_effect=lxmf_message_factory),
        patch(
            "meshchatx.src.backend.lxmf_utils.lxmf_message_solving_stamps",
            return_value=False,
        ),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        await app.send_message(destination_hash=LOCAL_LXMF, content="ws")

    raw = app.websocket_broadcast.await_args[0][0]
    payload = json.loads(raw)
    assert payload["type"] == "lxmf_message_created"
    lm = payload["lxmf_message"]
    assert lm["state"] == "delivered"
    assert lm["method"] == "local"
    assert lm["content"] == "ws"


@pytest.mark.asyncio
async def test_identity_resolved_to_other_lxmf_is_not_self(local_self_app):
    app = local_self_app
    other_lxmf = REMOTE_PEER
    identity_hex = app.current_context.identity.hash.hex()
    app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=other_lxmf)
    assert app._is_self_lxmf_destination(identity_hex) is True
    stranger = "f0" * 16
    app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=other_lxmf)
    assert app._is_self_lxmf_destination(stranger) is False


def test_oracle_rejects_if_implementation_always_returns_true(local_self_app):
    """Guard: mutating oracle expectation must fail (documents test strength)."""
    app = local_self_app
    assert app._is_self_lxmf_destination(REMOTE_PEER) is False
