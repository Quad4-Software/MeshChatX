# SPDX-License-Identifier: 0BSD

"""Telemetry request backoff and feature-aware resend gating.

A tracked peer that never answers must not be polled on its base
interval forever, and feature-only outbound messages should not be
auto-resent to peers that never demonstrated feature support.
"""

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
from meshchatx.src.backend.telemetry_request_policy import (
    TELEMETRY_REQUEST_MAX_INTERVAL_SECONDS,
    TELEMETRY_REQUEST_MAX_UNANSWERED,
    effective_request_interval,
    is_request_paused,
)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "telemetry_policy.db")
    provider = DatabaseProvider(path)
    DatabaseSchema(provider).initialize()
    database = Database(path)
    yield database
    database.close_all()
    provider.close_all()


def test_effective_request_interval_backoff():
    assert effective_request_interval(60, 0) == 60
    assert effective_request_interval(60, 1) == 120
    assert effective_request_interval(60, 2) == 240
    assert effective_request_interval(60, 10) == 61440
    assert (
        effective_request_interval(60, 30)
        == TELEMETRY_REQUEST_MAX_INTERVAL_SECONDS
    )
    assert effective_request_interval(None, 3) == 480
    assert effective_request_interval("junk", 1) == 120
    assert effective_request_interval(60, "x") == 60


def test_is_request_paused():
    assert not is_request_paused(0)
    assert not is_request_paused(TELEMETRY_REQUEST_MAX_UNANSWERED - 1)
    assert is_request_paused(TELEMETRY_REQUEST_MAX_UNANSWERED)
    assert is_request_paused(TELEMETRY_REQUEST_MAX_UNANSWERED + 5)
    assert not is_request_paused(None)
    assert not is_request_paused("junk")


def test_tracking_mark_request_and_response(db):
    peer = "a" * 32
    db.telemetry.toggle_tracking(peer, True)
    row = db.provider.fetchone(
        "SELECT unanswered_count, last_request_at FROM telemetry_tracking WHERE destination_hash = ?",
        (peer,),
    )
    assert row["unanswered_count"] == 0

    db.telemetry.mark_request_sent(peer, 1000)
    db.telemetry.mark_request_sent(peer, 2000)
    row = db.provider.fetchone(
        "SELECT unanswered_count, last_request_at FROM telemetry_tracking WHERE destination_hash = ?",
        (peer,),
    )
    assert row["unanswered_count"] == 2
    assert row["last_request_at"] == 2000

    db.telemetry.mark_response_received(peer)
    row = db.provider.fetchone(
        "SELECT unanswered_count FROM telemetry_tracking WHERE destination_hash = ?",
        (peer,),
    )
    assert row["unanswered_count"] == 0


def test_mark_response_received_ignores_untracked_peer(db):
    # No row: nothing to reset, no crash.
    db.telemetry.mark_response_received("b" * 32)
    assert db.provider.fetchone(
        "SELECT 1 FROM telemetry_tracking WHERE destination_hash = ?",
        ("b" * 32,),
    ) is None


def test_toggle_tracking_rearms_paused_peer(db):
    peer = "c" * 32
    db.telemetry.toggle_tracking(peer, True)
    for _ in range(TELEMETRY_REQUEST_MAX_UNANSWERED):
        db.telemetry.mark_request_sent(peer)
    row = db.provider.fetchone(
        "SELECT unanswered_count FROM telemetry_tracking WHERE destination_hash = ?",
        (peer,),
    )
    assert is_request_paused(row["unanswered_count"])

    db.telemetry.toggle_tracking(peer, True)
    row = db.provider.fetchone(
        "SELECT unanswered_count FROM telemetry_tracking WHERE destination_hash = ?",
        (peer,),
    )
    assert row["unanswered_count"] == 0


def _bind_tracking_app(db, sent):
    app = MagicMock()
    app.running = True

    async def _send(**kwargs):
        sent.append(kwargs)
        # Stop the loop after the first peer pass.
        app.running = False

    app.send_message = AsyncMock(side_effect=_send)
    app.telemetry_tracking_loop = types.MethodType(
        ReticulumMeshChat.telemetry_tracking_loop,
        app,
    )

    ctx = MagicMock()
    ctx.database = db
    ctx.running = True
    ctx.session_id = 7

    def _enabled():
        # Exit after the first peer pass so the loop cannot spin.
        ctx.running = False
        return True

    ctx.config.telemetry_enabled.get.side_effect = _enabled
    return app, ctx


@pytest.mark.asyncio
async def test_tracking_loop_pauses_unanswered_peer(db, monkeypatch):
    peer = "d" * 32
    db.telemetry.toggle_tracking(peer, True)
    for _ in range(TELEMETRY_REQUEST_MAX_UNANSWERED):
        db.telemetry.mark_request_sent(peer)

    sent = []
    app, ctx = _bind_tracking_app(db, sent)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    await app.telemetry_tracking_loop(7, context=ctx)
    assert sent == []


@pytest.mark.asyncio
async def test_tracking_loop_sends_and_counts(db, monkeypatch):
    peer = "e" * 32
    db.telemetry.toggle_tracking(peer, True)

    sent = []
    app, ctx = _bind_tracking_app(db, sent)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    await app.telemetry_tracking_loop(7, context=ctx)
    assert len(sent) == 1
    assert sent[0]["destination_hash"] == peer
    row = db.provider.fetchone(
        "SELECT unanswered_count, last_request_at FROM telemetry_tracking WHERE destination_hash = ?",
        (peer,),
    )
    assert row["unanswered_count"] == 1
    assert row["last_request_at"] is not None


@pytest.mark.asyncio
async def test_tracking_loop_respects_backed_off_interval(db, monkeypatch):
    peer = "f" * 32
    db.telemetry.toggle_tracking(peer, True)
    # Three unanswered requests sent just now: next interval is 240s,
    # so a fresh loop pass must not send another one.
    db.telemetry.mark_request_sent(peer, time.time())
    db.telemetry.mark_request_sent(peer, time.time())
    db.telemetry.mark_request_sent(peer, time.time())

    sent = []
    app, ctx = _bind_tracking_app(db, sent)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    await app.telemetry_tracking_loop(7, context=ctx)
    assert sent == []


def _insert_failed(db, *, msg_hash, peer, content, fields="{}", title=""):
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
            "title": title,
            "content": content,
            "fields": fields,
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
            "timestamp": time.time(),
        },
    )


def _insert_incoming(db, *, msg_hash, peer, content="", fields="{}"):
    db.messages.upsert_lxmf_message(
        {
            "hash": msg_hash,
            "source_hash": peer,
            "destination_hash": "0" * 32,
            "peer_hash": peer,
            "state": "delivered",
            "progress": 1,
            "is_incoming": 1,
            "method": "direct",
            "delivery_attempts": 1,
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
            "timestamp": time.time(),
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


def test_is_feature_only_message():
    assert guard.is_feature_only_message("", "", '{"reaction": {"0x40": "smile"}}')
    assert guard.is_feature_only_message("", "", {"commands": [{"0x01": 0}]})
    assert guard.is_feature_only_message(None, None, {"telemetry": "deadbeef"})
    assert not guard.is_feature_only_message("hi", "", '{"reaction": {}}')
    assert not guard.is_feature_only_message("", "title", '{"reaction": {}}')
    assert not guard.is_feature_only_message("", "", "{}")
    assert not guard.is_feature_only_message("", "", '{"image": {"image_bytes": "aa"}}')


@pytest.mark.asyncio
async def test_resend_skips_feature_only_to_uncapable_peer(db):
    peer = "1" * 32
    _insert_failed(
        db,
        msg_hash="2" * 32,
        peer=peer,
        content="",
        fields=json.dumps({"commands": [{"0x01": 0}]}),
    )
    app, ctx = _bind_resend_app(db)
    await app.resend_failed_messages_for_destination(peer, context=ctx)
    app.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_resend_allows_feature_only_to_capable_peer(db):
    peer = "3" * 32
    _insert_incoming(
        db,
        msg_hash="4" * 32,
        peer=peer,
        fields=json.dumps({"reaction": {"smile": True}}),
    )
    _insert_failed(
        db,
        msg_hash="5" * 32,
        peer=peer,
        content="",
        fields=json.dumps({"commands": [{"0x01": 0}]}),
    )
    app, ctx = _bind_resend_app(db)
    await app.resend_failed_messages_for_destination(peer, context=ctx)
    app.send_message.assert_awaited()


@pytest.mark.asyncio
async def test_resend_regular_content_ignores_capability(db):
    peer = "6" * 32
    _insert_failed(
        db,
        msg_hash="7" * 32,
        peer=peer,
        content="hello there",
        fields="{}",
    )
    app, ctx = _bind_resend_app(db)
    await app.resend_failed_messages_for_destination(peer, context=ctx)
    app.send_message.assert_awaited()
