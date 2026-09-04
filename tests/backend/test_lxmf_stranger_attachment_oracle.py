# SPDX-License-Identifier: 0BSD
"""Oracles for inbound LXMF stranger attachment policy.

Independent model:
- block_all_from_strangers + non-contact -> drop entire message (no DB row)
- block_attachments_from_strangers + non-contact + attachments -> keep text,
  strip FIELD_FILE_ATTACHMENTS / FIELD_IMAGE / FIELD_AUDIO, set attachments_stripped
- Large direct deliveries use RNS resources. lxmf_inbound_policy rejects those
  transfers before download only when the peer identity is already known and
  stranger settings apply. Unknown identity at advertise (common on fresh
  links) is accepted and handled by on_lxmf_delivery stripping or drop.
  Small single-packet messages always use on_lxmf_delivery stripping.
- contact or disabled settings -> attachment bytes may persist
- blocked or spam attachment-bearing messages -> drop entire message
"""

from __future__ import annotations

import base64
import json

import LXMF
import pytest

from meshchatx.src.backend.meshchat_utils import message_fields_have_attachments
from tests.backend.lxmf_tools_support import (
    LOCAL_LXMF,
    PEER_FRIEND,
    PEER_SPAMMER,
    delivery_ws_payload,
    make_inbound_lxmf,
    prepare_messaging_app,
    stored_message,
)

_ORACLE_SECRET = b"ORACLE_SECRET_ATTACHMENT_PAYLOAD_7f3a"


def oracle_stranger_inbound_outcome(
    *,
    block_all: bool,
    block_attachments: bool,
    is_contact: bool,
    has_attachments: bool,
    is_blocked: bool = False,
    is_spam: bool = False,
) -> str:
    """Predict inbound handling without calling on_lxmf_delivery."""
    if is_blocked:
        return "drop_all"
    if block_all and not is_contact:
        return "drop_all"
    if has_attachments and is_spam:
        return "drop_all"
    if block_attachments and not is_contact and has_attachments:
        return "strip_attachments"
    return "allow"


def _fields_blob_contains_secret(fields_raw) -> bool:
    if fields_raw is None:
        return False
    if isinstance(fields_raw, dict):
        blob = json.dumps(fields_raw)
    else:
        blob = str(fields_raw)
    secret_b64 = base64.b64encode(_ORACLE_SECRET).decode("ascii")
    return _ORACLE_SECRET.decode("ascii") in blob or secret_b64 in blob


def _attachment_field_sets():
    return {
        "file": {
            LXMF.FIELD_FILE_ATTACHMENTS: [[b"oracle.txt", _ORACLE_SECRET]],
        },
        "image": {
            LXMF.FIELD_IMAGE: [b"png", b"\x89PNG\r\n\x1a\n" + _ORACLE_SECRET],
        },
        "audio": {
            LXMF.FIELD_AUDIO: [LXMF.AM_CODEC2_1200, _ORACLE_SECRET],
        },
        "combined": {
            LXMF.FIELD_FILE_ATTACHMENTS: [[b"multi.bin", _ORACLE_SECRET]],
            LXMF.FIELD_IMAGE: [b"webp", _ORACLE_SECRET],
            LXMF.FIELD_AUDIO: [LXMF.AM_OPUS_OGG, _ORACLE_SECRET],
        },
    }


def _deliver(app, source, fields, content="oracle body"):
    msg = make_inbound_lxmf(
        source_hash=source,
        destination_hash=LOCAL_LXMF,
        content=content,
        fields=fields,
    )
    app.on_lxmf_delivery(msg)
    return msg


@pytest.mark.parametrize("kind", ["file", "image", "audio", "combined"])
def test_oracle_stranger_attachments_stripped_not_persisted(mock_app, kind):
    app = prepare_messaging_app(mock_app)
    app.config.block_attachments_from_strangers.set(True)
    app.config.block_all_from_strangers.set(False)

    fields = _attachment_field_sets()[kind]
    expected = oracle_stranger_inbound_outcome(
        block_all=False,
        block_attachments=True,
        is_contact=False,
        has_attachments=True,
    )
    assert expected == "strip_attachments"

    msg = _deliver(app, PEER_SPAMMER, fields)
    row = stored_message(app, msg)
    assert row is not None
    assert row["content"] == "oracle body"
    assert int(row["attachments_stripped"]) == 1
    assert not _fields_blob_contains_secret(row.get("fields"))
    assert not _fields_blob_contains_secret(row.get("fields_meta"))
    assert message_fields_have_attachments(row.get("fields")) is False

    live_fields = msg.get_fields()
    assert LXMF.FIELD_FILE_ATTACHMENTS not in live_fields
    assert LXMF.FIELD_IMAGE not in live_fields
    assert LXMF.FIELD_AUDIO not in live_fields

    payload = delivery_ws_payload(app)
    assert payload is not None
    ws_fields = payload["lxmf_message"].get("fields") or {}
    assert not _fields_blob_contains_secret(ws_fields)


def test_oracle_block_all_drops_stranger_attachment_message(mock_app):
    app = prepare_messaging_app(mock_app)
    app.config.block_all_from_strangers.set(True)
    app.config.block_attachments_from_strangers.set(True)

    fields = _attachment_field_sets()["combined"]
    expected = oracle_stranger_inbound_outcome(
        block_all=True,
        block_attachments=True,
        is_contact=False,
        has_attachments=True,
    )
    assert expected == "drop_all"

    msg = _deliver(app, PEER_SPAMMER, fields)
    assert stored_message(app, msg) is None
    assert delivery_ws_payload(app) is None


def test_oracle_contact_keeps_attachment_bytes(mock_app):
    app = prepare_messaging_app(mock_app)
    app.config.block_attachments_from_strangers.set(True)
    app.config.block_all_from_strangers.set(False)
    app.database.contacts.add_contact("Friend", PEER_FRIEND, lxmf_address=PEER_FRIEND)

    fields = _attachment_field_sets()["file"]
    expected = oracle_stranger_inbound_outcome(
        block_all=False,
        block_attachments=True,
        is_contact=True,
        has_attachments=True,
    )
    assert expected == "allow"

    msg = _deliver(app, PEER_FRIEND, fields)
    row = stored_message(app, msg)
    assert row is not None
    assert int(row.get("attachments_stripped") or 0) == 0
    assert _fields_blob_contains_secret(row.get("fields"))


def test_oracle_blocked_peer_attachment_message_dropped(mock_app):
    app = prepare_messaging_app(mock_app)
    app.config.block_attachments_from_strangers.set(False)
    app.config.block_all_from_strangers.set(False)
    app.database.misc.add_blocked_destination(PEER_SPAMMER)

    fields = _attachment_field_sets()["image"]
    expected = oracle_stranger_inbound_outcome(
        block_all=False,
        block_attachments=False,
        is_contact=False,
        has_attachments=True,
        is_blocked=True,
    )
    assert expected == "drop_all"

    msg = _deliver(app, PEER_SPAMMER, fields)
    assert stored_message(app, msg) is None


def test_oracle_stranger_text_without_attachments_still_stored(mock_app):
    app = prepare_messaging_app(mock_app)
    app.config.block_attachments_from_strangers.set(True)
    app.config.block_all_from_strangers.set(False)

    msg = _deliver(app, PEER_SPAMMER, {}, content="plain text only")
    row = stored_message(app, msg)
    assert row is not None
    assert row["content"] == "plain text only"
    assert int(row.get("attachments_stripped") or 0) == 0
