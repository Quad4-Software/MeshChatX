# SPDX-License-Identifier: 0BSD
"""Oracles for LXMF outbound send, delivery proofs, and auto-resend cascades.

Guarantee: missing RNS delivery proofs leave opportunistic/direct messages in
SENT (not DELIVERED). Progress polling must not treat that as terminal. Auto
resend only claims failed rows and emits a new hash. Same-content guards do not
treat a failed-only lineage as recent success.

These tests document the no-receipt double-send cascade:
LXMF retries the same hash until MAX_DELIVERY_ATTEMPTS, then MeshChat may
auto-resend a new hash when a peer announces or a path/ping succeeds.
"""

from __future__ import annotations

import asyncio
import time
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import LXMF
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend import auto_resend_guard as guard
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema
from meshchatx.src.backend.lxmf_utils import is_lxmf_outbound_progress_terminal


def _msg(**attrs):
    defaults = {
        "state": LXMF.LXMessage.OUTBOUND,
        "method": LXMF.LXMessage.DIRECT,
        "try_propagation_on_fail": False,
    }
    defaults.update(attrs)
    return SimpleNamespace(**defaults)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "send_delivery_oracle.db")
    provider = DatabaseProvider(path)
    DatabaseSchema(provider).initialize()
    database = Database(path)
    yield database
    database.close_all()
    provider.close_all()


def _insert_row(
    db,
    *,
    msg_hash,
    peer,
    content,
    state,
    fields="{}",
    delivery_attempts=0,
    ts=None,
    next_at=None,
):
    now = ts if ts is not None else time.time()
    db.messages.upsert_lxmf_message(
        {
            "hash": msg_hash,
            "source_hash": peer,
            "destination_hash": peer,
            "peer_hash": peer,
            "state": state,
            "progress": 1 if state == "delivered" else 0,
            "is_incoming": 0,
            "method": "opportunistic",
            "delivery_attempts": delivery_attempts,
            "next_delivery_attempt_at": next_at,
            "title": "",
            "content": content,
            "fields": fields,
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
            "timestamp": now,
        },
    )


def _bind_resend_app(db):
    app = MagicMock()
    app._auto_resend_coordinator = guard.AutoResendCoordinator()
    app.websocket_broadcast = AsyncMock()
    app.send_message = AsyncMock()
    app.resend_failed_messages_for_destination = types.MethodType(
        ReticulumMeshChat.resend_failed_messages_for_destination,
        app,
    )
    ctx = MagicMock()
    ctx.identity.hash.hex.return_value = "aa" * 16
    ctx.database = db
    ctx.config.allow_auto_resending_failed_messages_with_attachments.get.return_value = True
    return app, ctx


def test_oracle_lxmf_sent_is_not_delivered_without_proof():
    """Independent LXMF contract: SENT != DELIVERED. Proofs flip to DELIVERED."""
    assert LXMF.LXMessage.SENT != LXMF.LXMessage.DELIVERED
    assert LXMF.LXMRouter.MAX_DELIVERY_ATTEMPTS >= 1
    assert LXMF.LXMRouter.DELIVERY_RETRY_WAIT > 0


@pytest.mark.parametrize(
    ("state", "method", "try_prop", "expected"),
    [
        (LXMF.LXMessage.SENT, LXMF.LXMessage.OPPORTUNISTIC, False, False),
        (LXMF.LXMessage.SENT, LXMF.LXMessage.DIRECT, False, False),
        (LXMF.LXMessage.OUTBOUND, LXMF.LXMessage.DIRECT, False, False),
        (LXMF.LXMessage.SENDING, LXMF.LXMessage.DIRECT, False, False),
        (LXMF.LXMessage.SENT, LXMF.LXMessage.PROPAGATED, False, True),
        (LXMF.LXMessage.DELIVERED, LXMF.LXMessage.OPPORTUNISTIC, False, True),
        (LXMF.LXMessage.DELIVERED, LXMF.LXMessage.PROPAGATED, False, True),
        (LXMF.LXMessage.FAILED, LXMF.LXMessage.DIRECT, False, True),
        (LXMF.LXMessage.FAILED, LXMF.LXMessage.DIRECT, True, False),
        (LXMF.LXMessage.CANCELLED, LXMF.LXMessage.DIRECT, False, True),
        (LXMF.LXMessage.REJECTED, LXMF.LXMessage.DIRECT, False, True),
    ],
)
def test_oracle_progress_terminal_matrix(state, method, try_prop, expected):
    msg = _msg(state=state, method=method, try_propagation_on_fail=try_prop)
    assert is_lxmf_outbound_progress_terminal(msg) is expected


@given(
    method=st.sampled_from(
        [
            LXMF.LXMessage.OPPORTUNISTIC,
            LXMF.LXMessage.DIRECT,
            LXMF.LXMessage.PAPER,
        ]
    )
)
@settings(max_examples=24, deadline=None)
def test_oracle_sent_without_propagated_never_terminal(method):
    """No-receipt peers leave opportunistic/direct at SENT. Must keep polling."""
    assert not is_lxmf_outbound_progress_terminal(
        _msg(state=LXMF.LXMessage.SENT, method=method)
    )


@pytest.mark.asyncio
async def test_oracle_progress_loop_keeps_polling_opportunistic_sent(db):
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.current_context = MagicMock()
    app.current_context.database = db
    app.reticulum = None
    app.websocket_broadcast = AsyncMock()
    app._maybe_store_path_at_send_for_lxmf = MagicMock()
    app._merge_stored_path_fields_from_db = MagicMock()

    peer = "b" * 32
    msg_hash = "c" * 32
    _insert_row(db, msg_hash=msg_hash, peer=peer, content="hi", state="outbound")

    mock_msg = MagicMock()
    mock_msg.hash = bytes.fromhex(msg_hash)
    mock_msg.progress = 0.0
    mock_msg.delivery_attempts = 1
    mock_msg.state = LXMF.LXMessage.SENT
    mock_msg.method = LXMF.LXMessage.OPPORTUNISTIC
    mock_msg.try_propagation_on_fail = False
    mock_msg.next_delivery_attempt = None
    # Avoid MagicMock auto-attrs leaking into SQLite binds.
    type(mock_msg).rssi = property(lambda self: None)
    type(mock_msg).snr = property(lambda self: None)
    type(mock_msg).q = property(lambda self: None)

    sleeps = 0

    async def count_sleep(_duration):
        nonlocal sleeps
        sleeps += 1
        if sleeps >= 2:
            mock_msg.state = LXMF.LXMessage.FAILED

    with (
        patch(
            "meshchatx.meshchat.convert_lxmf_message_to_dict",
            return_value={"hash": msg_hash, "state": "sent"},
        ),
        patch("asyncio.sleep", side_effect=count_sleep),
    ):
        await ReticulumMeshChat.handle_lxmf_message_progress(
            app,
            mock_msg,
            context=app.current_context,
        )

    assert sleeps >= 2
    row = db.provider.fetchone(
        "SELECT state FROM lxmf_messages WHERE hash = ?",
        (msg_hash,),
    )
    assert row["state"] == "failed"


def test_oracle_claim_refuses_non_failed_states(db):
    peer = "d" * 32
    now = time.time()
    for state, msg_hash in (
        ("sent", "1" * 32),
        ("outbound", "2" * 32),
        ("delivered", "3" * 32),
        ("sending", "4" * 32),
    ):
        _insert_row(
            db,
            msg_hash=msg_hash,
            peer=peer,
            content="body",
            state=state,
            delivery_attempts=3,
        )
        assert not db.messages.try_claim_failed_message_for_auto_resend(
            msg_hash,
            cooldown_until=now + 120,
            now=now,
        )


def test_oracle_failed_only_lineage_does_not_count_as_recent_success(db):
    """After no-proof FAILED, only the failed row remains. Auto-resend may fire."""
    peer = "e" * 32
    now = time.time()
    _insert_row(
        db,
        msg_hash="5" * 32,
        peer=peer,
        content="same body",
        state="failed",
        delivery_attempts=LXMF.LXMRouter.MAX_DELIVERY_ATTEMPTS,
        ts=now - 10,
    )
    assert not db.messages.has_recent_outbound_with_content(
        peer,
        "same body",
        within_seconds=300,
        now=now,
    )


def test_oracle_in_flight_sent_blocks_same_content_resend(db):
    """While LXMF still holds SENT (retrying proofs), do not treat as free to resend."""
    peer = "f" * 32
    now = time.time()
    _insert_row(
        db,
        msg_hash="6" * 32,
        peer=peer,
        content="in flight",
        state="sent",
        delivery_attempts=2,
        ts=now - 5,
    )
    assert db.messages.has_recent_outbound_with_content(
        peer,
        "in flight",
        within_seconds=300,
        now=now,
    )


@pytest.mark.asyncio
async def test_oracle_auto_resend_skips_sent_rows_and_only_claims_failed(db):
    peer = "7" * 32
    _insert_row(db, msg_hash="8" * 32, peer=peer, content="alive", state="sent")
    _insert_row(db, msg_hash="9" * 32, peer=peer, content="dead", state="failed")
    app, ctx = _bind_resend_app(db)

    new_hash = bytes.fromhex("a" * 32)

    async def send_ok(*args, **kwargs):
        m = MagicMock()
        m.hash = new_hash
        _insert_row(
            db,
            msg_hash=new_hash.hex(),
            peer=peer,
            content="dead",
            state="outbound",
        )
        return m

    app.send_message.side_effect = send_ok
    await app.resend_failed_messages_for_destination(peer, context=ctx)
    assert app.send_message.await_count == 1
    assert (
        db.provider.fetchone(
            "SELECT state FROM lxmf_messages WHERE hash = ?",
            ("8" * 32,),
        )["state"]
        == "sent"
    )
    assert (
        db.provider.fetchone(
            "SELECT 1 FROM lxmf_messages WHERE hash = ?",
            ("9" * 32,),
        )
        is None
    )


@pytest.mark.asyncio
async def test_oracle_auto_resend_emits_new_hash_not_same_hash(db):
    peer = "b" * 32
    old_hash = "c" * 32
    new_hash = bytes.fromhex("d" * 32)
    _insert_row(db, msg_hash=old_hash, peer=peer, content="retry", state="failed")
    app, ctx = _bind_resend_app(db)

    async def send_ok(*args, **kwargs):
        m = MagicMock()
        m.hash = new_hash
        _insert_row(
            db,
            msg_hash=new_hash.hex(),
            peer=peer,
            content="retry",
            state="outbound",
        )
        return m

    app.send_message.side_effect = send_ok
    await app.resend_failed_messages_for_destination(peer, context=ctx)
    assert new_hash.hex() != old_hash
    assert app.send_message.await_count == 1
    assert (
        guard.read_auto_resend_count(
            db.provider.fetchone(
                "SELECT fields FROM lxmf_messages WHERE hash = ?",
                (new_hash.hex(),),
            )["fields"]
        )
        == 1
    )


@pytest.mark.asyncio
async def test_oracle_propagation_fallback_clears_packed_and_requeues_same_object():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    ctx.forwarding_manager = None
    ctx.message_router = MagicMock()
    app.current_context = ctx

    original_id = object()
    lxmf_message = MagicMock()
    lxmf_message.__id = original_id
    lxmf_message.packed = b"stale-packet"
    lxmf_message.delivery_attempts = 5
    lxmf_message.next_delivery_attempt = time.time() + 10
    lxmf_message.source_hash = bytes.fromhex("11" * 16)
    lxmf_message.message_id = b"mid" * 5 + b"xx"

    ReticulumMeshChat.send_failed_message_via_propagation_node(
        app,
        lxmf_message,
        context=ctx,
    )

    assert lxmf_message.packed is None
    assert lxmf_message.delivery_attempts == 0
    assert lxmf_message.desired_method == LXMF.LXMessage.PROPAGATED
    assert lxmf_message.try_propagation_on_fail is False
    assert not hasattr(lxmf_message, "next_delivery_attempt")
    ctx.message_router.handle_outbound.assert_called_once_with(lxmf_message)


@pytest.mark.asyncio
async def test_oracle_concurrent_resend_claims_send_once(db):
    peer = "e" * 32
    old_hash = "f" * 32
    _insert_row(db, msg_hash=old_hash, peer=peer, content="race", state="failed")
    app, ctx = _bind_resend_app(db)

    async def slow_send(*args, **kwargs):
        await asyncio.sleep(0.05)
        m = MagicMock()
        m.hash = bytes.fromhex("1" * 32)
        _insert_row(
            db,
            msg_hash=m.hash.hex(),
            peer=peer,
            content="race",
            state="outbound",
        )
        return m

    app.send_message.side_effect = slow_send
    await asyncio.gather(
        app.resend_failed_messages_for_destination(peer, context=ctx),
        app.resend_failed_messages_for_destination(peer, context=ctx),
        app.resend_failed_messages_for_destination(peer, context=ctx),
    )
    assert app.send_message.await_count == 1


def test_oracle_no_receipt_cascade_contract_documented():
    """Closed contract for peers that never return delivery proofs."""
    from pathlib import Path

    # 1) Proof required for DELIVERED
    assert LXMF.LXMessage.SENT != LXMF.LXMessage.DELIVERED
    # 2) Library retries same outbound object
    assert LXMF.LXMRouter.MAX_DELIVERY_ATTEMPTS == 5
    # 3) Progress must keep polling SENT opportunistic
    assert not is_lxmf_outbound_progress_terminal(
        _msg(
            state=LXMF.LXMessage.SENT,
            method=LXMF.LXMessage.OPPORTUNISTIC,
        )
    )
    # 4) Only FAILED is auto-resend eligible (claim SQL requires state=failed)
    messages_src = (
        Path(__file__).resolve().parents[2]
        / "meshchatx"
        / "src"
        / "backend"
        / "database"
        / "messages.py"
    ).read_text(encoding="utf-8")
    assert "state = 'failed'" in messages_src
    assert "try_claim_failed_message_for_auto_resend" in messages_src
    # 5) Auto-resend budget caps replacement floods
    assert guard.MAX_AUTO_RESEND_ATTEMPTS == 3
    assert guard.AUTO_RESEND_COOLDOWN_SECONDS == 120
    assert guard.RECENT_SAME_CONTENT_SECONDS == 300


def test_lxmf_send_delivery_oracle_proved():
    pairs = 0
    for state, method, expected in (
        (LXMF.LXMessage.SENT, LXMF.LXMessage.OPPORTUNISTIC, False),
        (LXMF.LXMessage.SENT, LXMF.LXMessage.DIRECT, False),
        (LXMF.LXMessage.SENT, LXMF.LXMessage.PROPAGATED, True),
        (LXMF.LXMessage.DELIVERED, LXMF.LXMessage.DIRECT, True),
        (LXMF.LXMessage.FAILED, LXMF.LXMessage.DIRECT, True),
        (LXMF.LXMessage.CANCELLED, LXMF.LXMessage.DIRECT, True),
    ):
        assert (
            is_lxmf_outbound_progress_terminal(_msg(state=state, method=method))
            is expected
        )
        pairs += 1
    assert pairs == 6
    print("LXMF_SEND_DELIVERY_ORACLE_PROVED")
