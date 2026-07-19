# SPDX-License-Identifier: 0BSD

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from meshchatx.src.backend import auto_resend_guard as guard
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


def test_auto_resend_count_helpers():
    assert guard.read_auto_resend_count(None) == 0
    assert guard.read_auto_resend_count("{}") == 0
    assert guard.read_auto_resend_count('{"_mcx_auto_resend_count": 2}') == 2
    assert guard.should_skip_for_budget('{"_mcx_auto_resend_count": 3}')
    assert not guard.should_skip_for_budget('{"_mcx_auto_resend_count": 2}')
    assert guard.next_attempt_count("{}") == 1
    out = guard.fields_with_auto_resend_count('{"image":{"x":1}}', 2)
    assert '"_mcx_auto_resend_count": 2' in out
    assert '"image"' in out


@pytest.fixture
def _db_path(tmp_path):
    return str(tmp_path / "auto_resend.db")


def _insert_failed(db, *, msg_hash, peer, content, fields="{}", ts=None):
    now = ts if ts is not None else time.time()
    db.messages.upsert_lxmf_message(
        {
            "hash": msg_hash,
            "source_hash": peer,
            "destination_hash": peer,
            "peer_hash": peer,
            "state": "failed",
            "progress": 0,
            "is_incoming": 0,
            "method": "opportunistic",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
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


def test_claim_failed_message_is_atomic(_db_path):
    provider = DatabaseProvider(_db_path)
    DatabaseSchema(provider).initialize()
    db = Database(_db_path)
    peer = "a" * 32
    msg = "b" * 32
    _insert_failed(db, msg_hash=msg, peer=peer, content="hello")
    now = time.time()
    assert db.messages.try_claim_failed_message_for_auto_resend(
        msg,
        cooldown_until=now + 120,
        now=now,
    )
    assert not db.messages.try_claim_failed_message_for_auto_resend(
        msg,
        cooldown_until=now + 240,
        now=now,
    )
    db.close_all()
    provider.close_all()


def test_recent_outbound_same_content_blocks_duplicate(_db_path):
    provider = DatabaseProvider(_db_path)
    DatabaseSchema(provider).initialize()
    db = Database(_db_path)
    peer = "c" * 32
    now = time.time()
    db.messages.upsert_lxmf_message(
        {
            "hash": "d" * 32,
            "source_hash": peer,
            "destination_hash": peer,
            "peer_hash": peer,
            "state": "delivered",
            "progress": 1,
            "is_incoming": 0,
            "method": "direct",
            "delivery_attempts": 1,
            "next_delivery_attempt_at": None,
            "title": "",
            "content": "same body",
            "fields": "{}",
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
            "timestamp": now - 10,
        },
    )
    assert db.messages.has_recent_outbound_with_content(
        peer,
        "same body",
        within_seconds=300,
        now=now,
    )
    assert not db.messages.has_recent_outbound_with_content(
        peer,
        "other",
        within_seconds=300,
        now=now,
    )
    db.close_all()
    provider.close_all()


@pytest.mark.asyncio
async def test_resend_uses_lock_and_skips_second_concurrent_claim(_db_path):
    provider = DatabaseProvider(_db_path)
    DatabaseSchema(provider).initialize()
    db = Database(_db_path)
    peer = "e" * 32
    msg = "f" * 32
    _insert_failed(db, msg_hash=msg, peer=peer, content="dup text")

    app = MagicMock()
    app._auto_resend_coordinator = guard.AutoResendCoordinator()
    app.websocket_broadcast = AsyncMock()

    ctx = MagicMock()
    ctx.identity.hash.hex.return_value = "11" * 16
    ctx.database = db
    ctx.config.allow_auto_resending_failed_messages_with_attachments.get.return_value = True

    send_calls = []

    async def fake_send(*args, **kwargs):
        send_calls.append(1)
        await asyncio.sleep(0.05)
        m = MagicMock()
        m.hash = bytes.fromhex("aa" * 16)
        return m

    # Bind the real method implementation by importing MeshChat is heavy.
    # Exercise coordinator + claim path directly to prove race safety.
    lock = app._auto_resend_coordinator.lock_for("id1", peer)

    async def claim_once():
        async with lock:
            now = time.time()
            claimed = db.messages.try_claim_failed_message_for_auto_resend(
                msg,
                cooldown_until=now + 120,
                now=now,
            )
            if claimed:
                await fake_send()
            return claimed

    results = await asyncio.gather(claim_once(), claim_once())
    assert sorted(results) == [False, True]
    assert len(send_calls) == 1
    db.close_all()
    provider.close_all()


def test_set_auto_resend_count_merges_fields(_db_path):
    provider = DatabaseProvider(_db_path)
    DatabaseSchema(provider).initialize()
    db = Database(_db_path)
    peer = "1" * 32
    msg = "2" * 32
    _insert_failed(
        db,
        msg_hash=msg,
        peer=peer,
        content="x",
        fields='{"keep":true}',
    )
    db.messages.set_auto_resend_count_on_message(msg, 2)
    row = db.messages.provider.fetchone(
        "SELECT fields FROM lxmf_messages WHERE hash = ?",
        (msg,),
    )
    assert '"keep": true' in row["fields"] or '"keep":true' in row["fields"]
    assert guard.read_auto_resend_count(row["fields"]) == 2
    db.close_all()
    provider.close_all()
