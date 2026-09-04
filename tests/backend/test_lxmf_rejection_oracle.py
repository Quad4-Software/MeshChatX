# SPDX-License-Identifier: 0BSD
"""Oracles for LXMF rejection paths: spam, stranger attachments, telemetry bypass.

Independent model (oracle_reject_inbound_outcome):
- blocked peer -> drop_all
- block_all strangers -> drop_all
- spam + attachments -> drop_all
- stranger + attachments + block_attachments -> strip_attachments
- otherwise allow (may still mark is_spam for text-only spam)
"""

from __future__ import annotations

import base64
import json
import time

import LXMF

from meshchatx.src.backend.lxmf_utils import (
    convert_lxmf_message_to_dict,
    extract_sideband_command_entries,
)
from meshchatx.src.backend.sideband_commands import SidebandCommands
from tests.backend.lxmf_tools_support import (
    LOCAL_LXMF,
    PEER_FRIEND,
    PEER_SPAMMER,
    make_inbound_lxmf,
    prepare_messaging_app,
    stored_message,
)

_ORACLE_SECRET = b"REJECT_ORACLE_ATTACHMENT_SECRET_9c2e"


def oracle_reject_inbound_outcome(
    *,
    block_all: bool,
    block_attachments: bool,
    is_contact: bool,
    has_attachments: bool,
    is_blocked: bool = False,
    is_spam: bool = False,
) -> str:
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


def _deliver(app, source, fields, content="oracle body", title=""):
    msg = make_inbound_lxmf(
        source_hash=source,
        destination_hash=LOCAL_LXMF,
        content=content,
        title=title,
        fields=fields,
    )
    app.on_lxmf_delivery(msg)
    return msg


def test_oracle_spam_plus_attachment_drops_entire_message(mock_app):
    app = prepare_messaging_app(mock_app)
    app.database.misc.add_spam_keyword("viagra")
    app.database.contacts.add_contact("Friend", PEER_FRIEND, lxmf_address=PEER_FRIEND)
    expected = oracle_reject_inbound_outcome(
        block_all=False,
        block_attachments=False,
        is_contact=True,
        has_attachments=True,
        is_spam=True,
    )
    assert expected == "drop_all"
    msg = _deliver(
        app,
        PEER_FRIEND,
        {LXMF.FIELD_IMAGE: ["png", b"\x89PNG" + _ORACLE_SECRET]},
        content="buy VIAGRA now",
    )
    assert stored_message(app, msg) is None


def test_oracle_telemetry_request_cannot_bypass_stranger_attachment_strip(mock_app):
    """Field-0x01 telemetry request must not skip stranger attachment stripping."""
    app = prepare_messaging_app(mock_app)
    app.config.block_attachments_from_strangers.set(True)
    fields = {
        0x01: [{SidebandCommands.TELEMETRY_REQUEST: int(time.time())}],
        LXMF.FIELD_IMAGE: ["png", b"\x89PNG" + _ORACLE_SECRET],
    }
    expected = oracle_reject_inbound_outcome(
        block_all=False,
        block_attachments=True,
        is_contact=False,
        has_attachments=True,
    )
    assert expected == "strip_attachments"
    msg = _deliver(app, PEER_SPAMMER, fields, content="ping")
    row = stored_message(app, msg)
    assert row is not None
    assert int(row["attachments_stripped"] or 0) == 1
    assert LXMF.FIELD_IMAGE not in msg.get_fields()
    assert not _fields_blob_contains_secret(row["fields"])


def test_oracle_telemetry_request_cannot_bypass_spam_attachment_drop(mock_app):
    app = prepare_messaging_app(mock_app)
    app.database.misc.add_spam_keyword("casino")
    app.database.contacts.add_contact("Friend", PEER_FRIEND, lxmf_address=PEER_FRIEND)
    fields = {
        0x01: [{SidebandCommands.TELEMETRY_REQUEST: int(time.time())}],
        LXMF.FIELD_FILE_ATTACHMENTS: [["spam.bin", _ORACLE_SECRET]],
    }
    expected = oracle_reject_inbound_outcome(
        block_all=False,
        block_attachments=False,
        is_contact=True,
        has_attachments=True,
        is_spam=True,
    )
    assert expected == "drop_all"
    msg = _deliver(app, PEER_FRIEND, fields, content="online CASINO deal")
    assert stored_message(app, msg) is None


def test_oracle_embedded_lxms_bytes_are_not_sideband_commands():
    packed_inner = b"\x82fake-embedded-lxm"
    assert extract_sideband_command_entries([packed_inner]) == []
    assert extract_sideband_command_entries(
        [{SidebandCommands.TELEMETRY_REQUEST: 1}],
    ) == [{SidebandCommands.TELEMETRY_REQUEST: 1}]

    msg = make_inbound_lxmf(
        source_hash=PEER_FRIEND,
        destination_hash=LOCAL_LXMF,
        content="",
        fields={LXMF.FIELD_EMBEDDED_LXMS: [packed_inner]},
    )
    out = convert_lxmf_message_to_dict(msg, include_attachments=False)
    assert "commands" not in out["fields"]
    assert out["fields"]["embedded_lxms"] == [{"size": len(packed_inner)}]


def test_oracle_blocked_peer_never_stores(mock_app):
    app = prepare_messaging_app(mock_app)
    app.database.misc.add_blocked_destination(PEER_SPAMMER)
    expected = oracle_reject_inbound_outcome(
        block_all=False,
        block_attachments=False,
        is_contact=False,
        has_attachments=False,
        is_blocked=True,
    )
    assert expected == "drop_all"
    msg = _deliver(app, PEER_SPAMMER, {}, content="hello")
    assert stored_message(app, msg) is None
