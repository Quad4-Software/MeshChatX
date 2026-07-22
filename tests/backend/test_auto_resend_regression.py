# SPDX-License-Identifier: 0BSD

"""Regression tests for auto-resend flooding guards and duplicate cleanup."""

from __future__ import annotations

import asyncio
import json
import time
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend import auto_resend_guard as guard
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "resend_reg.db")
    provider = DatabaseProvider(path)
    DatabaseSchema(provider).initialize()
    database = Database(path)
    yield database
    database.close_all()
    provider.close_all()


def _insert_failed(db, *, msg_hash, peer, content, fields="{}", ts=None, next_at=None):
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


def _insert_outbound(db, *, msg_hash, peer, content, state="delivered", ts=None):
    now = ts if ts is not None else time.time()
    db.messages.upsert_lxmf_message(
        {
            "hash": msg_hash,
            "source_hash": peer,
            "destination_hash": peer,
            "peer_hash": peer,
            "state": state,
            "progress": 1,
            "is_incoming": 0,
            "method": "direct",
            "delivery_attempts": 1,
            "next_delivery_attempt_at": None,
            "title": "",
            "content": content,
            "fields": "{}",
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


def test_fields_have_attachments_and_invalid_json():
    assert not guard.fields_have_attachments("{}")
    assert not guard.fields_have_attachments("not-json")
    assert guard.fields_have_attachments('{"image":{"image_type":"png"}}')
    assert guard.fields_have_attachments('{"file_attachments":[{"file_name":"a"}]}')
    assert guard.parse_fields_dict("not-json") == {}
    assert guard.should_skip_for_budget(
        '{"_mcx_auto_resend_count": 3}',
        max_attempts=3,
    )


@pytest.mark.asyncio
async def test_resend_skips_when_budget_exhausted(db):
    peer = "b" * 32
    msg = "c" * 32
    _insert_failed(
        db,
        msg_hash=msg,
        peer=peer,
        content="help",
        fields=json.dumps({"_mcx_auto_resend_count": 3}),
    )
    app, ctx = _bind_resend_app(db)
    await app.resend_failed_messages_for_destination(peer, context=ctx)
    app.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_resend_skips_when_recent_same_content_exists(db):
    peer = "d" * 32
    now = time.time()
    _insert_outbound(
        db,
        msg_hash="1" * 32,
        peer=peer,
        content="help text",
        ts=now - 30,
    )
    _insert_failed(
        db,
        msg_hash="2" * 32,
        peer=peer,
        content="help text",
        ts=now - 5,
    )
    app, ctx = _bind_resend_app(db)
    await app.resend_failed_messages_for_destination(peer, context=ctx)
    app.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_resend_skips_attachments_before_claim(db):
    peer = "e" * 32
    msg = "f" * 32
    fields = json.dumps(
        {
            "image": {
                "image_type": "png",
                "image_bytes": "aa",
            },
        },
    )
    _insert_failed(db, msg_hash=msg, peer=peer, content="pic", fields=fields)
    app, ctx = _bind_resend_app(db)
    ctx.config.allow_auto_resending_failed_messages_with_attachments.get.return_value = False
    await app.resend_failed_messages_for_destination(peer, context=ctx)
    app.send_message.assert_not_called()
    row = db.provider.fetchone(
        "SELECT next_delivery_attempt_at FROM lxmf_messages WHERE hash = ?",
        (msg,),
    )
    # Must not burn cooldown when attachments are disallowed.
    assert row["next_delivery_attempt_at"] is None


@pytest.mark.asyncio
async def test_resend_claims_once_and_deletes_old_on_success(db):
    peer = "1" * 32
    old_hash = "2" * 32
    new_hash_bytes = bytes.fromhex("3" * 32)
    _insert_failed(db, msg_hash=old_hash, peer=peer, content="retry me")
    app, ctx = _bind_resend_app(db)

    async def send_and_materialize(*args, **kwargs):
        new_msg = MagicMock()
        new_msg.hash = new_hash_bytes
        _insert_outbound(
            db,
            msg_hash=new_hash_bytes.hex(),
            peer=peer,
            content="retry me",
            state="outbound",
        )
        return new_msg

    app.send_message.side_effect = send_and_materialize

    await app.resend_failed_messages_for_destination(peer, context=ctx)
    assert app.send_message.await_count == 1
    assert (
        db.provider.fetchone(
            "SELECT 1 FROM lxmf_messages WHERE hash = ?",
            (old_hash,),
        )
        is None
    )
    new_row = db.provider.fetchone(
        "SELECT fields FROM lxmf_messages WHERE hash = ?",
        (new_hash_bytes.hex(),),
    )
    assert guard.read_auto_resend_count(new_row["fields"]) == 1
    app.websocket_broadcast.assert_awaited()


@pytest.mark.asyncio
async def test_resend_concurrent_calls_send_only_once(db):
    peer = "4" * 32
    old_hash = "5" * 32
    _insert_failed(db, msg_hash=old_hash, peer=peer, content="race")
    app, ctx = _bind_resend_app(db)

    async def slow_send(*args, **kwargs):
        await asyncio.sleep(0.05)
        m = MagicMock()
        m.hash = bytes.fromhex("6" * 32)
        _insert_outbound(
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
    )
    assert app.send_message.await_count == 1


@pytest.mark.asyncio
async def test_resend_does_not_delete_old_when_send_returns_none(db):
    peer = "7" * 32
    old_hash = "8" * 32
    _insert_failed(db, msg_hash=old_hash, peer=peer, content="keep")
    app, ctx = _bind_resend_app(db)
    app.send_message.return_value = None
    await app.resend_failed_messages_for_destination(peer, context=ctx)
    assert (
        db.provider.fetchone(
            "SELECT state FROM lxmf_messages WHERE hash = ?",
            (old_hash,),
        )["state"]
        == "failed"
    )
    # Cooldown claimed, attempt counted.
    row = db.provider.fetchone(
        "SELECT fields, next_delivery_attempt_at FROM lxmf_messages WHERE hash = ?",
        (old_hash,),
    )
    assert guard.read_auto_resend_count(row["fields"]) == 1
    assert row["next_delivery_attempt_at"] is not None


def test_duplicate_cleanup_keeps_oldest_by_timestamp(db):
    peer = "9" * 32
    base = time.time()
    # Later insert id can still be oldest by timestamp.
    _insert_outbound(db, msg_hash="a" * 32, peer=peer, content="dup", ts=base - 5)
    _insert_outbound(db, msg_hash="b" * 32, peer=peer, content="dup", ts=base - 50)
    _insert_outbound(db, msg_hash="c" * 32, peer=peer, content="dup", ts=base - 1)
    deleted = db.messages.delete_duplicate_lxmf_messages_by_content()
    assert deleted == 2
    left = db.provider.fetchone(
        "SELECT hash FROM lxmf_messages WHERE content = 'dup'",
    )
    assert left["hash"] == "b" * 32


def test_source_keeps_auto_resend_and_duplicate_guards():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    sources = [root / "meshchatx" / "meshchat.py"]
    routes_dir = root / "meshchatx" / "src" / "backend" / "http" / "routes"
    if routes_dir.is_dir():
        sources.extend(sorted(routes_dir.glob("*.py")))
    blob = "\n".join(p.read_text(encoding="utf-8") for p in sources if p.is_file())
    guard_src = (
        root / "meshchatx" / "src" / "backend" / "auto_resend_guard.py"
    ).read_text(encoding="utf-8")
    messages = (
        root / "meshchatx" / "src" / "backend" / "database" / "messages.py"
    ).read_text(encoding="utf-8")
    settings = (
        root
        / "meshchatx"
        / "src"
        / "frontend"
        / "components"
        / "settings"
        / "SettingsPage.vue"
    ).read_text(encoding="utf-8")

    assert "AutoResendCoordinator" in blob
    assert "try_claim_failed_message_for_auto_resend" in blob
    assert "fields_have_attachments" in blob
    assert "has_path(destination_hash)" in blob
    assert "MAX_AUTO_RESEND_ATTEMPTS" in guard_src
    assert "delete_duplicate_lxmf_messages_by_content" in messages
    assert "clearDuplicateMessages" in settings
    assert "/api/v1/maintenance/messages/duplicates" in blob


def test_claim_reopens_after_cooldown_expires(db):
    peer = "0" * 32
    msg = "a" * 32
    now = 1_000_000.0
    _insert_failed(db, msg_hash=msg, peer=peer, content="x", next_at=now - 1)
    assert db.messages.try_claim_failed_message_for_auto_resend(
        msg,
        cooldown_until=now + 120,
        now=now,
    )
    assert not db.messages.try_claim_failed_message_for_auto_resend(
        msg,
        cooldown_until=now + 240,
        now=now + 10,
    )
    assert db.messages.try_claim_failed_message_for_auto_resend(
        msg,
        cooldown_until=now + 360,
        now=now + 121,
    )
