# SPDX-License-Identifier: 0BSD
"""Write-reduction guarantees for the outbound LXMF progress loop.

The 1 Hz loop in handle_lxmf_message_progress must keep broadcasting every
tick (UI progress bars depend on it) while only persisting to SQLite when
something material changed: first iteration, state/method/delivery-attempt
changes, whole-percent progress movement, or a terminal state.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import LXMF
import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "progress_dirty_check.db")
    provider = DatabaseProvider(path)
    DatabaseSchema(provider).initialize()
    database = Database(path)
    yield database
    database.close_all()
    provider.close_all()


def _insert_row(db, *, msg_hash, peer, state):
    db.messages.upsert_lxmf_message(
        {
            "hash": msg_hash,
            "source_hash": peer,
            "destination_hash": peer,
            "peer_hash": peer,
            "state": state,
            "progress": 0,
            "is_incoming": 0,
            "method": "direct",
            "delivery_attempts": 1,
            "next_delivery_attempt_at": None,
            "title": "",
            "content": "hi",
            "fields": "{}",
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
            "timestamp": 1700000000,
        },
    )


def _build_app(db):
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.current_context = MagicMock()
    app.current_context.database = db
    app.current_context.running = True
    app.reticulum = None
    app.websocket_broadcast = AsyncMock()
    app._maybe_store_path_at_send_for_lxmf = MagicMock()
    app._merge_stored_path_fields_from_db = MagicMock()

    real_update = db.messages.update_lxmf_message_state
    writes = []

    def counting_update(*args, **kwargs):
        writes.append(kwargs)
        return real_update(*args, **kwargs)

    db.messages.update_lxmf_message_state = counting_update
    return app, writes


def _build_msg(msg_hash):
    mock_msg = MagicMock()
    mock_msg.hash = bytes.fromhex(msg_hash)
    mock_msg.progress = 0.1
    mock_msg.delivery_attempts = 1
    mock_msg.state = LXMF.LXMessage.OUTBOUND
    mock_msg.method = LXMF.LXMessage.DIRECT
    mock_msg.try_propagation_on_fail = False
    mock_msg.next_delivery_attempt = None
    return mock_msg


def _dict_patch(msg_hash):
    return patch(
        "meshchatx.meshchat.convert_lxmf_message_to_dict",
        side_effect=lambda m, **k: {
            "hash": msg_hash,
            "progress": round(m.progress * 100, 2),
        },
    )


@pytest.mark.asyncio
async def test_unchanged_progress_and_state_persist_only_first_write(db):
    """N ticks with no material change produce exactly one write: the first."""
    peer = "a" * 32
    msg_hash = "b" * 32
    _insert_row(db, msg_hash=msg_hash, peer=peer, state="outbound")
    app, writes = _build_app(db)
    mock_msg = _build_msg(msg_hash)

    sleeps = 0

    async def creeping_sleep(_duration):
        nonlocal sleeps
        sleeps += 1
        # Sub-percent movement inside the same whole-percent bucket:
        # broadcast-only, never a persist trigger.
        mock_msg.progress += 0.001
        if sleeps >= 5:
            app.current_context.running = False

    with _dict_patch(msg_hash), patch("asyncio.sleep", side_effect=creeping_sleep):
        await ReticulumMeshChat.handle_lxmf_message_progress(
            app,
            mock_msg,
            context=app.current_context,
        )

    assert sleeps >= 5
    assert len(writes) == 1
    # Broadcasts and the path-at-send probe still run every tick.
    assert app.websocket_broadcast.await_count == sleeps
    assert app._maybe_store_path_at_send_for_lxmf.call_count == sleeps


@pytest.mark.asyncio
async def test_whole_percent_progress_jump_persists(db):
    """A >= 1 whole-percent progress move since last persist must write."""
    peer = "c" * 32
    msg_hash = "d" * 32
    _insert_row(db, msg_hash=msg_hash, peer=peer, state="outbound")
    app, writes = _build_app(db)
    mock_msg = _build_msg(msg_hash)

    sleeps = 0

    async def jumping_sleep(_duration):
        nonlocal sleeps
        sleeps += 1
        if sleeps == 1:
            mock_msg.progress = 0.115  # 10.0% -> 11.5%: crosses int() boundary
        if sleeps >= 2:
            app.current_context.running = False

    with _dict_patch(msg_hash), patch("asyncio.sleep", side_effect=jumping_sleep):
        await ReticulumMeshChat.handle_lxmf_message_progress(
            app,
            mock_msg,
            context=app.current_context,
        )

    assert len(writes) == 2
    assert writes[0]["progress"] == 10.0
    assert writes[1]["progress"] == 11.5


@pytest.mark.asyncio
async def test_state_transition_persists_with_tiny_progress_change(db):
    """State changes always persist, even with sub-percent progress movement."""
    peer = "e" * 32
    msg_hash = "f" * 32
    _insert_row(db, msg_hash=msg_hash, peer=peer, state="outbound")
    app, writes = _build_app(db)
    mock_msg = _build_msg(msg_hash)

    sleeps = 0

    async def state_flip_sleep(_duration):
        nonlocal sleeps
        sleeps += 1
        if sleeps == 1:
            mock_msg.state = LXMF.LXMessage.SENDING
            mock_msg.progress = 0.101  # same whole-percent bucket as 0.1
        if sleeps >= 2:
            app.current_context.running = False

    with _dict_patch(msg_hash), patch("asyncio.sleep", side_effect=state_flip_sleep):
        await ReticulumMeshChat.handle_lxmf_message_progress(
            app,
            mock_msg,
            context=app.current_context,
        )

    assert len(writes) == 2
    assert writes[0]["state"] == "outbound"
    assert writes[1]["state"] == "sending"


@pytest.mark.asyncio
async def test_terminal_state_persists_even_when_key_unchanged(db):
    """Terminal transition with unchanged persist key must still write.

    FAILED with try_propagation_on_fail flipping false is terminal while
    state string, method, and progress all stay the same.
    """
    peer = "1" * 32
    msg_hash = "2" * 32
    _insert_row(db, msg_hash=msg_hash, peer=peer, state="outbound")
    app, writes = _build_app(db)
    mock_msg = _build_msg(msg_hash)
    mock_msg.state = LXMF.LXMessage.FAILED
    mock_msg.try_propagation_on_fail = True

    sleeps = 0

    async def terminal_flip_sleep(_duration):
        nonlocal sleeps
        sleeps += 1
        if sleeps == 1:
            # Same state string, same method, same progress: only the
            # terminal flag changes. Nothing else in the persist key moves.
            mock_msg.try_propagation_on_fail = False

    with (
        _dict_patch(msg_hash),
        patch("asyncio.sleep", side_effect=terminal_flip_sleep),
    ):
        await ReticulumMeshChat.handle_lxmf_message_progress(
            app,
            mock_msg,
            context=app.current_context,
        )

    # First write (initial iteration) plus the forced terminal write.
    assert len(writes) == 2
    assert writes[0]["state"] == "failed"
    assert writes[1]["state"] == "failed"

    row = db.provider.fetchone(
        "SELECT state FROM lxmf_messages WHERE hash = ?",
        (msg_hash,),
    )
    assert row["state"] == "failed"


@pytest.mark.asyncio
async def test_mid_iteration_terminal_transition_still_persists(db):
    """Mid-iteration terminal transition persists before loop exit.

    A state going terminal after the top-of-loop check must persist via
    one extra immediate iteration without sleeping.
    """
    peer = "3" * 32
    msg_hash = "4" * 32
    _insert_row(db, msg_hash=msg_hash, peer=peer, state="outbound")
    app, writes = _build_app(db)
    mock_msg = _build_msg(msg_hash)

    sleeps = 0

    async def counting_sleep(_duration):
        nonlocal sleeps
        sleeps += 1

    converted = 0

    def flipping_convert(m, **kwargs):
        nonlocal converted
        converted += 1
        if converted == 1:
            # Terminal transition lands mid-iteration, after the loop top
            # already evaluated this tick as non-terminal.
            m.state = LXMF.LXMessage.DELIVERED
            m.progress = 1.0
        return {"hash": msg_hash}

    with (
        patch(
            "meshchatx.meshchat.convert_lxmf_message_to_dict",
            side_effect=flipping_convert,
        ),
        patch("asyncio.sleep", side_effect=counting_sleep),
    ):
        await ReticulumMeshChat.handle_lxmf_message_progress(
            app,
            mock_msg,
            context=app.current_context,
        )

    assert sleeps == 0  # no sleep needed for the forced final iteration
    assert len(writes) == 2
    assert writes[-1]["state"] == "delivered"
    row = db.provider.fetchone(
        "SELECT state FROM lxmf_messages WHERE hash = ?",
        (msg_hash,),
    )
    assert row["state"] == "delivered"


@pytest.mark.asyncio
async def test_delivery_attempts_change_persists(db):
    """delivery_attempts increments are material changes and always persist."""
    peer = "5" * 32
    msg_hash = "6" * 32
    _insert_row(db, msg_hash=msg_hash, peer=peer, state="outbound")
    app, writes = _build_app(db)
    mock_msg = _build_msg(msg_hash)

    sleeps = 0

    async def attempt_bump_sleep(_duration):
        nonlocal sleeps
        sleeps += 1
        if sleeps == 1:
            mock_msg.delivery_attempts = 2
        if sleeps >= 2:
            app.current_context.running = False

    with (
        _dict_patch(msg_hash),
        patch("asyncio.sleep", side_effect=attempt_bump_sleep),
    ):
        await ReticulumMeshChat.handle_lxmf_message_progress(
            app,
            mock_msg,
            context=app.current_context,
        )

    assert len(writes) == 2
    assert writes[1]["delivery_attempts"] == 2
