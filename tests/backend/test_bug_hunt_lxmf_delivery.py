# SPDX-License-Identifier: 0BSD

"""Bug-hunt tests for inbound LXMF delivery edge cases.

Covers attacker-controlled LXMF payload shapes that reach on_lxmf_delivery:
msgpack str/bin type confusion on title/content/timestamp, non-JSON-serializable
field values, has_attachments() early-return bypass, and missing dedup on
allow_duplicate (propagated) redelivery.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import LXMF
import pytest

from meshchatx.src.backend.meshchat_utils import has_attachments
from tests.backend.lxmf_tools_support import (
    LOCAL_LXMF,
    PEER_ALIAS,
    PEER_FORWARD_TO,
    PEER_SPAMMER,
    make_inbound_lxmf,
    prepare_messaging_app,
    stored_message,
)


def _run_async(coro):
    if asyncio.iscoroutine(coro):
        asyncio.run(coro)


def _make(source=PEER_SPAMMER, content="hello", title="", fields=None, **kw):
    return make_inbound_lxmf(
        source_hash=source,
        destination_hash=LOCAL_LXMF,
        content=content,
        title=title,
        fields=fields,
        **kw,
    )


# ---------------------------------------------------------------------------
# has_attachments() early return: FIELD_FILE_ATTACHMENTS present but empty or
# non-sized makes the function return False without checking image/audio, so
# the stranger-attachment strip block in on_lxmf_delivery is skipped entirely.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("empty_value", [[], {}, "", None, 0])
def test_has_attachments_early_return_bypass(empty_value):
    fields = {
        LXMF.FIELD_FILE_ATTACHMENTS: empty_value,
        LXMF.FIELD_IMAGE: ["png", b"\x89PNG fake"],
    }
    # A real image field is present; the function must not report False.
    assert has_attachments(fields) is True


def test_stranger_attachment_smuggling_empty_file_attachments_field(mock_app):
    """block_attachments_from_strangers must strip image/audio even when the sender includes an empty FIELD_FILE_ATTACHMENTS entry."""
    app = prepare_messaging_app(mock_app)

    app.config.block_attachments_from_strangers.set(True)
    msg = _make(
        fields={
            LXMF.FIELD_FILE_ATTACHMENTS: [],
            LXMF.FIELD_IMAGE: ["png", b"\x89PNG fakeimagedata"],
        },
    )
    app.on_lxmf_delivery(msg)
    row = stored_message(app, msg)
    assert row is not None
    stored_fields = json.loads(row["fields"] or "{}")
    assert "image" not in stored_fields
    assert row["attachments_stripped"] == 1


def test_stranger_attachment_smuggling_none_file_attachments_field(mock_app):
    app = prepare_messaging_app(mock_app)
    app.config.block_attachments_from_strangers.set(True)
    msg = _make(
        fields={
            LXMF.FIELD_FILE_ATTACHMENTS: None,
            LXMF.FIELD_AUDIO: [0, b"\x00" * 32],
        },
    )
    app.on_lxmf_delivery(msg)
    row = stored_message(app, msg)
    assert row is not None
    stored_fields = json.loads(row["fields"] or "{}")
    assert "audio" not in stored_fields
    assert row["attachments_stripped"] == 1


def test_stranger_attachment_normal_strip_still_works(mock_app):
    """Sanity: without the bypass key, stripping behaves as before."""
    app = prepare_messaging_app(mock_app)
    app.config.block_attachments_from_strangers.set(True)
    msg = _make(fields={LXMF.FIELD_IMAGE: ["png", b"\x89PNG fakeimagedata"]})
    app.on_lxmf_delivery(msg)
    row = stored_message(app, msg)
    assert row is not None
    stored_fields = json.loads(row["fields"] or "{}")
    assert "image" not in stored_fields
    assert row["attachments_stripped"] == 1


# ---------------------------------------------------------------------------
# LXMF.unpack_from_bytes assigns unpacked_payload[0..3] verbatim. msgpack str
# values arrive as Python str (not bytes) for title/content, and arbitrary
# objects for timestamp. convert_lxmf_message_to_dict then crashes on
# .decode() or the DB layer rejects/mis-stores the value.
# ---------------------------------------------------------------------------


def test_inbound_msgpack_str_title_is_stored(mock_app):
    """A msgpack-str title unpacks to lxmf_message.title == str. The message must still be stored and broadcast, not silently dropped."""
    app = prepare_messaging_app(mock_app)

    msg = _make(title="wire title")
    msg.title = "wire title"  # what unpack_from_bytes yields for msgpack str
    app.on_lxmf_delivery(msg)
    row = stored_message(app, msg)
    assert row is not None
    assert row["title"] == "wire title"


def test_inbound_msgpack_str_content_is_stored(mock_app):
    app = prepare_messaging_app(mock_app)
    msg = _make(content="wire body")
    msg.content = "wire body"  # str, not bytes
    app.on_lxmf_delivery(msg)
    row = stored_message(app, msg)
    assert row is not None
    assert row["content"] == "wire body"


def test_inbound_string_timestamp_stays_numeric(mock_app):
    """Timestamp REAL column must not end up holding TEXT; a str timestamp later crashes datetime.fromtimestamp() in the conversations API."""
    app = prepare_messaging_app(mock_app)

    msg = _make()
    msg.timestamp = "not-a-number"  # msgpack str timestamp
    app.on_lxmf_delivery(msg)
    row = stored_message(app, msg)
    assert row is not None
    ts = row["timestamp"]
    assert isinstance(ts, (int, float))
    # The conversations endpoint does datetime.fromtimestamp(ts, UTC).
    datetime.fromtimestamp(ts, UTC)


def test_inbound_non_scalar_timestamp_is_stored(mock_app):
    """list/dict timestamps currently raise sqlite binding errors inside upsert and the whole message is silently dropped."""
    app = prepare_messaging_app(mock_app)

    msg = _make()
    msg.timestamp = [1, 2, 3]
    app.on_lxmf_delivery(msg)
    row = stored_message(app, msg)
    assert row is not None


def test_inbound_bytes_valued_app_extensions_is_stored(mock_app):
    """Field values that survive convert as bytes make json.dumps(fields) raise TypeError inside upsert -> message silently dropped."""
    app = prepare_messaging_app(mock_app)

    msg = _make(fields={16: {"key": b"\x00\x01binary"}})  # LXMF_APP_EXTENSIONS_FIELD
    app.on_lxmf_delivery(msg)
    row = stored_message(app, msg)
    assert row is not None


# ---------------------------------------------------------------------------
# Missing dedup: LXMRouter.lxmf_delivery invokes the delivery callback for
# every allow_duplicate (propagated) redelivery. on_lxmf_delivery has no
# seen-hash guard, so handle_forwarding re-sends and the UI re-broadcasts.
# ---------------------------------------------------------------------------


def test_redelivery_does_not_reforward(mock_app):
    app = prepare_messaging_app(mock_app)
    app.current_context.forwarding_manager = MagicMock()
    app.current_context.forwarding_manager.get_or_create_mapping.return_value = {
        "alias_hash": PEER_ALIAS,
    }
    app.database.misc.create_forwarding_rule(
        identity_hash=LOCAL_LXMF,
        forward_to_hash=PEER_FORWARD_TO,
        source_filter_hash=None,
        is_active=True,
        name="dedup-check",
    )
    app.send_message = AsyncMock()
    msg = _make(content="propagated once")
    with patch("meshchatx.meshchat.AsyncUtils.run_async", side_effect=_run_async):
        # Two deliveries of the same message hash = propagated redelivery.
        app.on_lxmf_delivery(msg)
        app.on_lxmf_delivery(msg)
    assert app.send_message.await_count == 1
