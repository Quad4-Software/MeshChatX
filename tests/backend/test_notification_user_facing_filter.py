# SPDX-License-Identifier: 0BSD

"""Notification bell must never raise on silent payloads.

Covers:
  - the pure helper :func:`is_user_facing_lxmf_payload`
  - the conversation-row helper
    :func:`compute_lxmf_conversation_unread_from_latest_row` with
    ``require_user_facing=True``
  - the DAO method
    :func:`MessageDAO.get_latest_user_facing_incoming_message`
  - end-to-end ``GET /api/v1/notifications`` integration: reactions,
    telemetry-only, icon-only, empty pings and delivery-status updates
    must not produce false unread badges or empty dropdown entries
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.lxmf_utils import (
    LXMF_APP_EXTENSIONS_FIELD,
    compute_lxmf_conversation_unread_from_latest_row,
    is_user_facing_lxmf_payload,
)
from meshchatx.src.backend.message_handler import MessageHandler


LOCAL_HASH = "aa" * 16
PEER_HASH = "bb" * 16
PEER_HASH_2 = "cc" * 16


# ---------------------------------------------------------------------------
# Pure helper: is_user_facing_lxmf_payload
# ---------------------------------------------------------------------------


class TestIsUserFacingLxmfPayload:
    def test_plain_text_message_is_user_facing(self):
        assert is_user_facing_lxmf_payload({}, "hello", "")
        assert is_user_facing_lxmf_payload({}, "hello", None)

    def test_title_only_is_user_facing(self):
        assert is_user_facing_lxmf_payload({}, "", "Subject")
        assert is_user_facing_lxmf_payload({}, None, "Subject")

    def test_empty_payload_is_not_user_facing(self):
        assert not is_user_facing_lxmf_payload({}, "", "")
        assert not is_user_facing_lxmf_payload({}, None, None)
        assert not is_user_facing_lxmf_payload({}, "   ", "  \t\n")

    def test_reaction_via_app_extensions_string_keys(self):
        fields = {"app_extensions": {"reaction_to": "abc", "emoji": "fire"}}
        assert not is_user_facing_lxmf_payload(fields, "", "")
        assert not is_user_facing_lxmf_payload(fields, None, None)

    def test_reaction_via_raw_int_field(self):
        fields = {LXMF_APP_EXTENSIONS_FIELD: {"reaction_to": "abc"}}
        assert not is_user_facing_lxmf_payload(fields, "", "")

    def test_reaction_with_text_is_still_not_user_facing(self):
        # A reaction payload that also carries content is still a reaction
        # event; we never raise the bell on reactions.
        fields = {"app_extensions": {"reaction_to": "abc"}}
        assert not is_user_facing_lxmf_payload(fields, "noise", "noise")

    def test_telemetry_only_is_not_user_facing(self):
        fields = {"telemetry": {"some": "data"}}
        assert not is_user_facing_lxmf_payload(fields, "", "")

    def test_icon_only_is_not_user_facing(self):
        # Icon appearance updates are processed separately and never appear in
        # the converted ``fields`` dict; an icon-only message therefore looks
        # like an empty payload to this helper.
        assert not is_user_facing_lxmf_payload({}, "", "")

    def test_image_attachment_is_user_facing(self):
        fields = {"image": {"image_size": 12345, "image_type": "png"}}
        assert is_user_facing_lxmf_payload(fields, "", "")

    def test_audio_attachment_is_user_facing(self):
        fields = {"audio": {"audio_size": 4242, "audio_mode": 1}}
        assert is_user_facing_lxmf_payload(fields, "", "")

    def test_file_attachment_is_user_facing(self):
        fields = {"file_attachments": [{"file_name": "hi.txt", "file_size": 5}]}
        assert is_user_facing_lxmf_payload(fields, "", "")

    def test_empty_file_attachments_list_not_user_facing(self):
        fields = {"file_attachments": []}
        assert not is_user_facing_lxmf_payload(fields, "", "")

    def test_accepts_json_string_fields(self):
        fields = json.dumps({"app_extensions": {"reaction_to": "abc"}})
        assert not is_user_facing_lxmf_payload(fields, "", "")
        fields = json.dumps({"image": {"image_size": 1}})
        assert is_user_facing_lxmf_payload(fields, "", "")

    def test_garbage_fields_do_not_crash(self):
        assert not is_user_facing_lxmf_payload(None, "", "")
        assert not is_user_facing_lxmf_payload("not json {", "", "")
        assert not is_user_facing_lxmf_payload(12345, "", "")
        assert is_user_facing_lxmf_payload(None, "hello", "")

    def test_bytes_content_is_handled(self):
        assert is_user_facing_lxmf_payload({}, b"hello", b"")
        assert not is_user_facing_lxmf_payload({}, b"", b"")
        assert not is_user_facing_lxmf_payload({}, b"   ", b"")


# ---------------------------------------------------------------------------
# Row-level helper: compute_lxmf_conversation_unread_from_latest_row
# ---------------------------------------------------------------------------


def _row(*, incoming, content="", title="", fields=None, last_read=None, ts=None):
    return {
        "is_incoming": incoming,
        "content": content,
        "title": title,
        "fields": fields if fields is not None else {},
        "last_read_at": last_read,
        "timestamp": ts if ts is not None else 1_700_000_000.0,
    }


class TestRequireUserFacingFlag:
    def test_legacy_behavior_unchanged_without_flag(self):
        row = _row(
            incoming=1,
            fields={"app_extensions": {"reaction_to": "abc"}},
        )
        # Without ``require_user_facing`` the helper preserves its old behavior
        # so the conversation list (which renders reactions) is unaffected.
        assert (
            compute_lxmf_conversation_unread_from_latest_row(row) is True
        )

    def test_reaction_filtered_when_require_user_facing(self):
        row = _row(
            incoming=1,
            fields={"app_extensions": {"reaction_to": "abc"}},
        )
        assert (
            compute_lxmf_conversation_unread_from_latest_row(
                row,
                require_user_facing=True,
            )
            is False
        )

    def test_telemetry_only_filtered_when_require_user_facing(self):
        row = _row(
            incoming=1,
            fields={"telemetry": {"k": "v"}},
        )
        assert (
            compute_lxmf_conversation_unread_from_latest_row(
                row,
                require_user_facing=True,
            )
            is False
        )

    def test_user_facing_message_still_unread(self):
        row = _row(incoming=1, content="hello")
        assert (
            compute_lxmf_conversation_unread_from_latest_row(
                row,
                require_user_facing=True,
            )
            is True
        )

    def test_outgoing_never_unread_even_user_facing(self):
        row = _row(incoming=0, content="hello")
        assert (
            compute_lxmf_conversation_unread_from_latest_row(
                row,
                require_user_facing=True,
            )
            is False
        )

    def test_user_facing_already_read(self):
        ts = 1_700_000_000.0
        row = _row(
            incoming=1,
            content="hello",
            last_read=datetime.fromtimestamp(ts + 1, UTC).isoformat(),
            ts=ts,
        )
        assert (
            compute_lxmf_conversation_unread_from_latest_row(
                row,
                require_user_facing=True,
            )
            is False
        )


# ---------------------------------------------------------------------------
# DAO: MessageDAO.get_latest_user_facing_incoming_message
# ---------------------------------------------------------------------------


def _mk_message(
    *,
    msg_hash,
    peer_hash,
    is_incoming=1,
    content="",
    title="",
    fields=None,
    timestamp=None,
    state="delivered",
):
    return {
        "hash": msg_hash,
        "source_hash": peer_hash if is_incoming else LOCAL_HASH,
        "destination_hash": LOCAL_HASH if is_incoming else peer_hash,
        "peer_hash": peer_hash,
        "state": state,
        "progress": 100,
        "is_incoming": is_incoming,
        "method": "direct",
        "delivery_attempts": 0,
        "next_delivery_attempt_at": None,
        "title": title,
        "content": content,
        "fields": fields if fields is not None else {},
        "timestamp": timestamp if timestamp is not None else time.time(),
        "rssi": None,
        "snr": None,
        "quality": None,
        "is_spam": 0,
        "reply_to_hash": None,
        "attachments_stripped": 0,
    }


class TestGetLatestUserFacingIncomingMessage:
    def test_returns_none_when_no_messages(self, db):
        result = db.messages.get_latest_user_facing_incoming_message(PEER_HASH)
        assert result is None

    def test_returns_latest_when_user_facing(self, db):
        db.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="h1",
                peer_hash=PEER_HASH,
                content="first",
                timestamp=100,
            ),
        )
        db.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="h2",
                peer_hash=PEER_HASH,
                content="second",
                timestamp=200,
            ),
        )
        result = db.messages.get_latest_user_facing_incoming_message(PEER_HASH)
        assert result is not None
        assert result["content"] == "second"

    def test_skips_reactions_returns_prior_message(self, db):
        db.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="h1",
                peer_hash=PEER_HASH,
                content="real message",
                timestamp=100,
            ),
        )
        db.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="h2",
                peer_hash=PEER_HASH,
                content="",
                fields={"app_extensions": {"reaction_to": "abc"}},
                timestamp=200,
            ),
        )
        result = db.messages.get_latest_user_facing_incoming_message(PEER_HASH)
        assert result is not None
        assert result["content"] == "real message"

    def test_skips_telemetry_only(self, db):
        db.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="h1",
                peer_hash=PEER_HASH,
                content="",
                fields={"telemetry": {"k": "v"}},
                timestamp=200,
            ),
        )
        result = db.messages.get_latest_user_facing_incoming_message(PEER_HASH)
        assert result is None

    def test_skips_outgoing_messages(self, db):
        db.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="h1",
                peer_hash=PEER_HASH,
                is_incoming=0,
                content="i sent this",
                timestamp=200,
            ),
        )
        result = db.messages.get_latest_user_facing_incoming_message(PEER_HASH)
        assert result is None

    def test_only_returns_messages_for_requested_peer(self, db):
        db.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="h1",
                peer_hash=PEER_HASH_2,
                content="other peer",
                timestamp=200,
            ),
        )
        result = db.messages.get_latest_user_facing_incoming_message(PEER_HASH)
        assert result is None

    def test_scan_limit_respected(self, db):
        # Insert many reactions then a real message past the scan window.
        # The real message is at the oldest position; with scan_limit=3 only
        # the 3 newest (all reactions) are scanned, so we should get None.
        db.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="real",
                peer_hash=PEER_HASH,
                content="hello",
                timestamp=1,
            ),
        )
        for i in range(5):
            db.messages.upsert_lxmf_message(
                _mk_message(
                    msg_hash=f"react{i}",
                    peer_hash=PEER_HASH,
                    content="",
                    fields={"app_extensions": {"reaction_to": "x"}},
                    timestamp=100 + i,
                ),
            )
        result = db.messages.get_latest_user_facing_incoming_message(
            PEER_HASH,
            scan_limit=3,
        )
        assert result is None
        # With a wider window we find the real message.
        result = db.messages.get_latest_user_facing_incoming_message(
            PEER_HASH,
            scan_limit=50,
        )
        assert result is not None
        assert result["content"] == "hello"


# ---------------------------------------------------------------------------
# Integration: GET /api/v1/notifications must not falsely raise the bell
# ---------------------------------------------------------------------------


pytestmark_integration = pytest.mark.usefixtures("require_loopback_tcp")


def _build_aio_app(app):
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw = app._define_routes(routes)
    aio_app = web.Application(middlewares=[auth_mw, mime_mw, sec_mw])
    aio_app.add_routes(routes)
    return aio_app


def _wire_real_message_handler(app):
    app.message_handler = MessageHandler(app.database)
    app.local_lxmf_destination = MagicMock()
    app.local_lxmf_destination.hexhash = LOCAL_HASH
    app.current_context.running = True
    app.config.auth_enabled.set(False)
    # Avoid name lookups touching real DAOs.
    app.get_lxmf_conversation_name = lambda h, default_name=None: f"peer-{h[:6]}"
    app.get_lxmf_destination_hash_for_identity_hash = lambda h: None
    app.get_name_for_identity_hash = lambda h: None
    return app


def _set_read_state(db, peer_hash, when_iso):
    db.provider.execute(
        "INSERT INTO lxmf_conversation_read_state (destination_hash, last_read_at, "
        "created_at, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(destination_hash) DO UPDATE SET "
        "last_read_at = EXCLUDED.last_read_at, updated_at = EXCLUDED.updated_at",
        (peer_hash, when_iso, when_iso, when_iso),
    )


@pytest.fixture
def bell_app(mock_app):
    return _wire_real_message_handler(mock_app)


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
class TestNotificationsGetUserFacingFilter:
    """End-to-end checks that the bell never falsely triggers."""

    async def _get(self, app, **params):
        aio_app = _build_aio_app(app)
        async with TestClient(TestServer(aio_app)) as client:
            resp = await client.get("/api/v1/notifications", params=params)
            assert resp.status == 200
            return await resp.json()

    async def test_no_data_returns_empty(self, bell_app):
        body = await self._get(bell_app, unread="true", limit=10)
        assert body["notifications"] == []
        assert body["unread_count"] == 0

    async def test_user_facing_message_raises_bell(self, bell_app):
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="h1",
                peer_hash=PEER_HASH,
                content="hello world",
                timestamp=1_700_000_000,
            ),
        )
        body = await self._get(bell_app, unread="true", limit=10)
        assert body["unread_count"] == 1
        assert len(body["notifications"]) == 1
        assert body["notifications"][0]["type"] == "lxmf_message"
        assert body["notifications"][0]["latest_message_preview"] == "hello world"

    async def test_lone_reaction_does_not_raise_bell(self, bell_app):
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="r1",
                peer_hash=PEER_HASH,
                content="",
                fields={"app_extensions": {"reaction_to": "abc", "emoji": "fire"}},
                timestamp=1_700_000_000,
            ),
        )
        body = await self._get(bell_app, unread="true", limit=10)
        assert body["unread_count"] == 0
        assert body["notifications"] == []

    async def test_reaction_after_read_message_does_not_raise_bell(self, bell_app):
        # Real message arrived, was read, then a reaction landed afterwards.
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="m1",
                peer_hash=PEER_HASH,
                content="hello",
                timestamp=1_700_000_000,
            ),
        )
        # Mark conversation as read AFTER hello but BEFORE reaction.
        _set_read_state(
            bell_app.database,
            PEER_HASH,
            datetime.fromtimestamp(1_700_000_500, UTC).isoformat(),
        )
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="r1",
                peer_hash=PEER_HASH,
                content="",
                fields={"app_extensions": {"reaction_to": "m1"}},
                timestamp=1_700_001_000,
            ),
        )
        body = await self._get(bell_app, unread="true", limit=10)
        assert body["unread_count"] == 0
        assert body["notifications"] == []

    async def test_reaction_after_unread_message_keeps_bell_for_real_message(
        self,
        bell_app,
    ):
        # Real unread message + later reaction should still surface ONE entry
        # describing the real message (the reaction itself is silent).
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="m1",
                peer_hash=PEER_HASH,
                content="hello",
                timestamp=1_700_000_000,
            ),
        )
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="r1",
                peer_hash=PEER_HASH,
                content="",
                fields={"app_extensions": {"reaction_to": "m1"}},
                timestamp=1_700_001_000,
            ),
        )
        body = await self._get(bell_app, unread="true", limit=10)
        assert body["unread_count"] == 1
        assert len(body["notifications"]) == 1
        assert body["notifications"][0]["latest_message_preview"] == "hello"

    async def test_telemetry_only_does_not_raise_bell(self, bell_app):
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="t1",
                peer_hash=PEER_HASH,
                content="",
                fields={"telemetry": {"k": "v"}},
                timestamp=1_700_000_000,
            ),
        )
        body = await self._get(bell_app, unread="true", limit=10)
        assert body["unread_count"] == 0
        assert body["notifications"] == []

    async def test_empty_payload_does_not_raise_bell(self, bell_app):
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="e1",
                peer_hash=PEER_HASH,
                content="",
                title="",
                fields={},
                timestamp=1_700_000_000,
            ),
        )
        body = await self._get(bell_app, unread="true", limit=10)
        assert body["unread_count"] == 0
        assert body["notifications"] == []

    async def test_outgoing_message_does_not_raise_bell(self, bell_app):
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="o1",
                peer_hash=PEER_HASH,
                is_incoming=0,
                content="i sent this",
                timestamp=1_700_000_000,
            ),
        )
        body = await self._get(bell_app, unread="true", limit=10)
        assert body["unread_count"] == 0
        assert body["notifications"] == []

    async def test_attachment_only_message_raises_bell(self, bell_app):
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="i1",
                peer_hash=PEER_HASH,
                content="",
                fields={"image": {"image_size": 9999, "image_type": "png"}},
                timestamp=1_700_000_000,
            ),
        )
        body = await self._get(bell_app, unread="true", limit=10)
        assert body["unread_count"] == 1
        assert len(body["notifications"]) == 1

    async def test_badge_count_matches_dropdown_items(self, bell_app):
        # Mix of user-facing and silent messages across multiple peers must
        # produce a badge that exactly equals the dropdown listing size.
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="m1",
                peer_hash=PEER_HASH,
                content="hello",
                timestamp=1_700_000_100,
            ),
        )
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="m2",
                peer_hash=PEER_HASH_2,
                content="",
                fields={"app_extensions": {"reaction_to": "x"}},
                timestamp=1_700_000_200,
            ),
        )
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="m3",
                peer_hash="dd" * 16,
                content="hi again",
                timestamp=1_700_000_300,
            ),
        )
        body = await self._get(bell_app, unread="true", limit=50)
        lxmf_items = [n for n in body["notifications"] if n["type"] == "lxmf_message"]
        assert body["unread_count"] == len(lxmf_items)
        assert body["unread_count"] == 2

    async def test_count_is_consistent_with_unread_filter_off(self, bell_app):
        # When ``unread=false`` the lxmf unread_count must still ignore
        # silent payloads so the badge never disagrees with the dropdown.
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="r1",
                peer_hash=PEER_HASH,
                content="",
                fields={"app_extensions": {"reaction_to": "abc"}},
                timestamp=1_700_000_000,
            ),
        )
        body = await self._get(bell_app, unread="false", limit=10)
        assert body["unread_count"] == 0

    async def test_marking_as_viewed_zeroes_count(self, bell_app):
        bell_app.database.messages.upsert_lxmf_message(
            _mk_message(
                msg_hash="m1",
                peer_hash=PEER_HASH,
                content="hello",
                timestamp=1_700_000_000,
            ),
        )
        body = await self._get(bell_app, unread="true", limit=10)
        assert body["unread_count"] == 1
        bell_app.database.messages.mark_all_notifications_as_viewed(
            [PEER_HASH],
        )
        body = await self._get(bell_app, unread="true", limit=10)
        assert body["unread_count"] == 0
        assert body["notifications"] == []
