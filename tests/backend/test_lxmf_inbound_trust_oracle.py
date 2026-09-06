# SPDX-License-Identifier: 0BSD

"""Regression and adversarial oracles for LXMF inbound trust hardening.

Covers zenith fixes (SIGNATURE_INVALID drop, icon appearance parse, finite
telemetry numbers) and sibling fixes (signature-gated telemetry/icon/request/
forwarding, stream attribution, reaction spam bypass, reaction hash/emoji
bounds, convert-path attachment parse, stamp-cost clamp, display-name clamp).
"""

from __future__ import annotations

import base64
import math
import os
import time
from unittest.mock import MagicMock

import LXMF
import pytest
import RNS.vendor.umsgpack as msgpack
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.lxmf_utils import (
    FIELD_REACTION,
    REACTION_CONTENT,
    REACTION_TO,
    convert_lxmf_message_to_dict,
    lxmf_is_reaction_only_delivery,
    parse_lxmf_reaction_field_dict,
)
from meshchatx.src.backend.meshchat_utils import (
    lxmf_signature_validated,
    normalize_lxmf_destination_hash,
    parse_lxmf_audio_field_value,
    parse_lxmf_display_name,
    parse_lxmf_file_attachments_field_value,
    parse_lxmf_icon_appearance,
    parse_lxmf_image_field_value,
    parse_lxmf_stamp_cost,
)
from meshchatx.src.backend.telemetry_utils import Telemeter, _valid_number


# ---------------------------------------------------------------------------
# Pure parser oracles (zenith + siblings)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        (1, False),
        ("yes", False),
        (None, False),
    ],
)
def test_lxmf_signature_validated_strict_bool(value, expected):
    msg = MagicMock()
    msg.signature_validated = value
    assert lxmf_signature_validated(msg) is expected


def test_lxmf_signature_validated_rejects_magicmock_truthiness():
    assert lxmf_signature_validated(MagicMock()) is False


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ([], None),
        (["user", b"\xff\xff\xff"], None),
        (
            ("user", b"\xff\xff\xff", b"\x00\x00\x00", "extra"),
            ("user", "#ffffff", "#000000"),
        ),
        (["user", b"\xff\xff", b"\x00\x00\x00"], None),
        (["user", "#ffffff", b"\x00\x00\x00"], None),
        ([b"user", b"\xff\xff\xff", b"\x00\x00\x00"], None),
        (["", b"\xff\xff\xff", b"\x00\x00\x00"], None),
        (["x" * 65, b"\xff\xff\xff", b"\x00\x00\x00"], None),
        (["bad\nname", b"\xff\xff\xff", b"\x00\x00\x00"], None),
        (["user", b"\xaa\xbb\xcc", b"\x11\x22\x33"], ("user", "#aabbcc", "#112233")),
    ],
)
def test_parse_lxmf_icon_appearance_regression(value, expected):
    assert parse_lxmf_icon_appearance(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (b"\x01\x02", "0102"),
        ("AbCd", "abcd"),
        ("  ee  ", "ee"),
        ("", None),
        (1234, None),
    ],
)
def test_normalize_lxmf_destination_hash(value, expected):
    assert normalize_lxmf_destination_hash(value) == expected


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        (0, True),
        (1.5, True),
        (-3, True),
        (True, False),
        (False, False),
        ("1", False),
        (math.nan, False),
        (math.inf, False),
        (-math.inf, False),
        (None, False),
    ],
)
def test_valid_number_regression(value, ok):
    result = _valid_number(value)
    if ok:
        assert result == value
    else:
        assert result is None


def test_parse_lxmf_image_audio_file_oracles():
    assert parse_lxmf_image_field_value(["png", b"data"]) == ("png", b"data")
    assert parse_lxmf_image_field_value([b"jpg", b"data"]) == ("jpg", b"data")
    assert parse_lxmf_image_field_value(["x" * 33, b"data"]) is None
    assert parse_lxmf_image_field_value(["bad\n", b"data"]) is None
    assert parse_lxmf_image_field_value(["png", "not-bytes"]) is None
    assert parse_lxmf_audio_field_value([1, b"a"]) == (1, b"a")
    assert parse_lxmf_audio_field_value([True, b"a"]) is None
    assert parse_lxmf_file_attachments_field_value(
        [["note.txt", b"hi"], ["", b"x"], [None, b"x"], ["bad\n", b"x"]],
    ) == [("note.txt", b"hi")]


def test_display_name_clamped_and_printable():
    huge = "A" * 1000
    packed = msgpack.packb([huge])
    out = parse_lxmf_display_name(base64.b64encode(packed).decode("ascii"))
    assert out == "A" * 256
    dirty = msgpack.packb(["ok\x00name"])
    out2 = parse_lxmf_display_name(base64.b64encode(dirty).decode("ascii"))
    assert "\x00" not in out2


def test_stamp_cost_rejects_non_finite_and_oob(monkeypatch):
    monkeypatch.setattr(LXMF, "stamp_cost_from_app_data", lambda _b: math.nan)
    assert parse_lxmf_stamp_cost(b"\x91\x00") is None
    monkeypatch.setattr(LXMF, "stamp_cost_from_app_data", lambda _b: True)
    assert parse_lxmf_stamp_cost(b"\x91\x00") is None
    monkeypatch.setattr(LXMF, "stamp_cost_from_app_data", lambda _b: 255)
    assert parse_lxmf_stamp_cost(b"\x91\x00") is None
    monkeypatch.setattr(LXMF, "stamp_cost_from_app_data", lambda _b: 12)
    assert parse_lxmf_stamp_cost(b"\x91\x00") == 12


@settings(max_examples=100, deadline=None)
@given(
    app_data_base64=st.text(min_size=0, max_size=10000),
)
def test_parse_lxmf_stamp_cost_oracle(app_data_base64):
    """Stamp cost parse returns None or a non-negative number and never raises."""
    cost = parse_lxmf_stamp_cost(app_data_base64)
    assert cost is None or (isinstance(cost, (int, float)) and cost >= 0)


@pytest.mark.parametrize(
    ("raw", "expected_to"),
    [
        ({REACTION_TO: bytes.fromhex("aa" * 16), REACTION_CONTENT: b"x"}, "aa" * 16),
        ({REACTION_TO: "bb" * 32, REACTION_CONTENT: b"x"}, "bb" * 32),
        ({REACTION_TO: "not-hex", REACTION_CONTENT: b"x"}, None),
        ({REACTION_TO: "aa", REACTION_CONTENT: b"x"}, None),
        ({REACTION_TO: b"\x01" * 8, REACTION_CONTENT: b"x"}, None),
        ({REACTION_TO: "gg" * 16, REACTION_CONTENT: b"x"}, None),
    ],
)
def test_reaction_hash_oracle(raw, expected_to):
    parsed = parse_lxmf_reaction_field_dict(raw)
    if expected_to is None:
        assert parsed is None
    else:
        assert parsed["reaction_to"] == expected_to


def test_reaction_emoji_capped():
    parsed = parse_lxmf_reaction_field_dict(
        {
            REACTION_TO: bytes.fromhex("cc" * 16),
            REACTION_CONTENT: ("Z" * 100).encode("utf-8"),
        },
    )
    assert parsed is not None
    assert parsed["reaction_emoji"] == "Z" * 16


def test_reaction_only_classifier_oracle():
    target = bytes.fromhex("dd" * 16)
    reaction_fields = {
        FIELD_REACTION: {REACTION_TO: target, REACTION_CONTENT: b"+1"},
    }
    assert lxmf_is_reaction_only_delivery(reaction_fields, "", "") is True
    assert lxmf_is_reaction_only_delivery(reaction_fields, "", "spam body") is False
    assert (
        lxmf_is_reaction_only_delivery(
            {**reaction_fields, LXMF.FIELD_IMAGE: ["png", b"x"]},
            "",
            "",
        )
        is False
    )


def test_convert_rejects_malformed_image_metadata():
    msg = MagicMock(spec=LXMF.LXMessage)
    msg.hash = b"h" * 32
    msg.source_hash = b"s" * 16
    msg.destination_hash = b"d" * 16
    msg.incoming = True
    msg.state = LXMF.LXMessage.DELIVERED
    msg.progress = 1.0
    msg.method = LXMF.LXMessage.DIRECT
    msg.delivery_attempts = 0
    msg.title = b""
    msg.content = b""
    msg.timestamp = 1
    msg.rssi = msg.snr = msg.q = None
    msg.get_fields.return_value = {
        LXMF.FIELD_IMAGE: ["x" * 50, b"\x89PNG"],
        LXMF.FIELD_FILE_ATTACHMENTS: [["ok.txt", b"hi"], ["bad\n", b"no"]],
    }
    out = convert_lxmf_message_to_dict(msg, include_attachments=False)
    assert "image" not in out["fields"]
    assert out["fields"]["file_attachments"] == [
        {"file_name": "ok.txt", "file_size": 2, "file_bytes": None},
    ]


# ---------------------------------------------------------------------------
# Delivery harness
# ---------------------------------------------------------------------------


def _bind_delivery(app):
    app.on_lxmf_delivery = ReticulumMeshChat.on_lxmf_delivery.__get__(
        app,
        ReticulumMeshChat,
    )
    app.process_incoming_telemetry = (
        ReticulumMeshChat.process_incoming_telemetry.__get__(app, ReticulumMeshChat)
    )
    app.handle_forwarding = ReticulumMeshChat.handle_forwarding.__get__(
        app,
        ReticulumMeshChat,
    )
    app.is_destination_blocked = MagicMock(return_value=False)
    app.db_upsert_lxmf_message = MagicMock()
    app.update_lxmf_user_icon = MagicMock()
    app._apply_lxmf_sieve_folder_rule = MagicMock()
    app._apply_lxmf_sieve_banish_rule = MagicMock()
    app._apply_message_blocklist_banish_rule = MagicMock()
    app._maybe_store_path_at_send_for_lxmf = MagicMock()
    app._merge_stored_path_fields_from_db = MagicMock()
    app._lxmf_sieve_suppresses_notifications = MagicMock(return_value=False)
    app.check_spam_keywords = MagicMock(return_value=False)
    app._is_contact = MagicMock(return_value=True)
    app._lxmf_incoming_timestamps = []
    app.websocket_broadcast = MagicMock()
    app.send_message = MagicMock()
    app.current_context.running = True
    app.current_context.database = app.database
    app.current_context.config.block_all_from_strangers.get.return_value = False
    app.current_context.config.block_attachments_from_strangers.get.return_value = False
    app.current_context.config.message_blocklist_enabled.get.return_value = False
    app.database.announces.get_custom_display_name.return_value = None
    app.database.announces.get_announce_by_hash.return_value = None
    app.database.messages.get_lxmf_message_by_hash.return_value = {}
    app.database.messages.get_forwarding_mapping.return_value = None
    app.database.misc.get_forwarding_rules.return_value = []
    app.database.telemetry.is_tracking.return_value = False
    app.reticulum = MagicMock()
    app.reticulum.get_packet_rssi.return_value = None
    app.reticulum.get_packet_snr.return_value = None
    app.reticulum.get_packet_q.return_value = None


@pytest.fixture
def delivery_app():
    app = MagicMock(spec=ReticulumMeshChat)
    app.database = MagicMock()
    app.current_context = MagicMock()
    app.current_context.local_lxmf_destination = MagicMock()
    app.current_context.local_lxmf_destination.hexhash = "aa" * 16
    _bind_delivery(app)
    return app


def _base_msg(*, signed=True, fields=None, title="", content=""):
    msg = MagicMock()
    msg.source_hash = os.urandom(16)
    msg.hash = os.urandom(32)
    msg.destination_hash = os.urandom(16)
    msg.signature_validated = signed
    msg.unverified_reason = None if signed else LXMF.LXMessage.SOURCE_UNKNOWN
    msg.title = title
    msg.content = content
    msg.get_fields.return_value = dict(fields or {})
    return msg


# ---------------------------------------------------------------------------
# Zenith + sibling delivery regressions
# ---------------------------------------------------------------------------


def test_signature_invalid_drops_before_block_check(delivery_app):
    msg = _base_msg(signed=False, content="hi")
    msg.unverified_reason = LXMF.LXMessage.SIGNATURE_INVALID
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.is_destination_blocked.assert_not_called()
    delivery_app.db_upsert_lxmf_message.assert_not_called()


def test_stream_rejects_foreign_entry_without_trusted_sender(delivery_app):
    sender = os.urandom(16)
    victim = os.urandom(16)
    packed = Telemeter.pack(location={"latitude": 1.0, "longitude": 2.0})
    msg = _base_msg(
        fields={LXMF.FIELD_TELEMETRY_STREAM: [(victim, int(time.time()), packed)]},
    )
    msg.source_hash = sender
    delivery_app.database.contacts.get_contact_by_identity_hash.return_value = {
        "is_telemetry_trusted": False,
    }
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.database.telemetry.upsert_telemetry.assert_not_called()


def test_stream_allows_foreign_entry_from_trusted_sender(delivery_app):
    sender = os.urandom(16)
    victim = os.urandom(16)
    packed = Telemeter.pack(location={"latitude": 1.0, "longitude": 2.0})
    ts = int(time.time())
    msg = _base_msg(fields={LXMF.FIELD_TELEMETRY_STREAM: [(victim, ts, packed)]})
    msg.source_hash = sender
    delivery_app.database.contacts.get_contact_by_identity_hash.return_value = {
        "is_telemetry_trusted": True,
    }
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.database.telemetry.upsert_telemetry.assert_called_once()
    assert (
        delivery_app.database.telemetry.upsert_telemetry.call_args.kwargs[
            "destination_hash"
        ]
        == victim.hex()
    )


def test_stream_allows_own_hash_entry_without_trust(delivery_app):
    sender = os.urandom(16)
    packed = Telemeter.pack(location={"latitude": 1.0, "longitude": 2.0})
    msg = _base_msg(
        fields={LXMF.FIELD_TELEMETRY_STREAM: [(sender, int(time.time()), packed)]},
    )
    msg.source_hash = sender
    delivery_app.database.contacts.get_contact_by_identity_hash.return_value = None
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.database.telemetry.upsert_telemetry.assert_called_once()
    assert (
        delivery_app.database.telemetry.upsert_telemetry.call_args.kwargs[
            "destination_hash"
        ]
        == sender.hex()
    )


def test_stream_rejects_non_finite_timestamp(delivery_app):
    sender = os.urandom(16)
    packed = Telemeter.pack(location={"latitude": 1.0, "longitude": 2.0})
    msg = _base_msg(fields={LXMF.FIELD_TELEMETRY_STREAM: [(sender, math.nan, packed)]})
    msg.source_hash = sender
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.database.telemetry.upsert_telemetry.assert_not_called()


def test_signed_single_telemetry_and_icon_accepted(delivery_app):
    packed = Telemeter.pack(location={"latitude": 1.0, "longitude": 2.0})
    msg = _base_msg(
        fields={
            LXMF.FIELD_TELEMETRY: packed,
            LXMF.FIELD_ICON_APPEARANCE: ["user", b"\xff\xff\xff", b"\x00\x00\x00"],
        },
    )
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.database.telemetry.upsert_telemetry.assert_called_once()
    delivery_app.update_lxmf_user_icon.assert_called_once()


def test_unsigned_telemetry_and_icon_are_ignored(delivery_app):
    packed = Telemeter.pack(location={"latitude": 1.0, "longitude": 2.0})
    msg = _base_msg(
        signed=False,
        content="hi",
        fields={
            LXMF.FIELD_TELEMETRY: packed,
            LXMF.FIELD_ICON_APPEARANCE: ["user", b"\xff\xff\xff", b"\x00\x00\x00"],
        },
    )
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.database.telemetry.upsert_telemetry.assert_not_called()
    delivery_app.update_lxmf_user_icon.assert_not_called()
    delivery_app.db_upsert_lxmf_message.assert_called_once()


def test_unsigned_telemetry_request_does_not_respond(delivery_app):
    msg = _base_msg(signed=False, fields={0x01: [{0x01: int(time.time())}]})
    msg.source_hash = b"source_hash_bytes"
    delivery_app.handle_telemetry_request = MagicMock()
    delivery_app.current_context.config.telemetry_enabled.get.return_value = True
    delivery_app.database.contacts.get_contact_by_identity_hash.return_value = {
        "is_telemetry_trusted": True,
    }
    delivery_app.current_context.config.location_source.get.return_value = "manual"
    delivery_app.current_context.config.location_manual_lat.get.return_value = 1.0
    delivery_app.current_context.config.location_manual_lon.get.return_value = 2.0
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.handle_telemetry_request.assert_not_called()


def test_malformed_icon_does_not_update_icon(delivery_app):
    msg = _base_msg(
        fields={LXMF.FIELD_ICON_APPEARANCE: ["bad", "#ffffff", "#000000"]},
    )
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.update_lxmf_user_icon.assert_not_called()
    delivery_app.db_upsert_lxmf_message.assert_called_once()


def test_reaction_plus_spam_body_marks_spam(delivery_app):
    target = bytes.fromhex("ee" * 16)
    delivery_app.check_spam_keywords = MagicMock(return_value=True)
    msg = _base_msg(
        title="SPAM_TITLE",
        content="SPAM_BODY",
        fields={
            FIELD_REACTION: {REACTION_TO: target, REACTION_CONTENT: b"+1"},
        },
    )
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.check_spam_keywords.assert_called_once()
    kwargs = delivery_app.db_upsert_lxmf_message.call_args.kwargs
    assert kwargs.get("is_spam") is True


def test_reaction_only_skips_spam_keywords(delivery_app):
    target = bytes.fromhex("ef" * 16)
    delivery_app.check_spam_keywords = MagicMock(return_value=True)
    msg = _base_msg(
        fields={
            FIELD_REACTION: {REACTION_TO: target, REACTION_CONTENT: b"+1"},
        },
    )
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.check_spam_keywords.assert_not_called()
    kwargs = delivery_app.db_upsert_lxmf_message.call_args.kwargs
    assert kwargs.get("is_spam") is False


def test_unsigned_message_does_not_enter_forwarding(delivery_app):
    delivery_app.handle_forwarding = MagicMock()
    msg = _base_msg(signed=False, content="please forward")
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.handle_forwarding.assert_not_called()


def test_handle_forwarding_noops_when_unsigned(delivery_app):
    delivery_app.send_message = MagicMock()
    delivery_app.database.messages.get_forwarding_mapping.return_value = {
        "original_sender_hash": "ff" * 16,
    }
    msg = _base_msg(signed=False, content="relay me")
    delivery_app.handle_forwarding(msg, context=delivery_app.current_context)
    delivery_app.database.messages.get_forwarding_mapping.assert_not_called()
    delivery_app.send_message.assert_not_called()


def test_plugin_command_requires_strict_signature(delivery_app):
    from meshchatx.src.backend.sideband_commands import SidebandCommands

    delivery_app.sideband_plugin_loader = MagicMock()
    msg = _base_msg(
        fields={
            LXMF.FIELD_COMMANDS: [
                {SidebandCommands.PLUGIN_COMMAND: "do_thing"},
            ],
        },
    )
    # MagicMock-truthy signature must not unlock plugins
    msg.signature_validated = MagicMock()
    delivery_app.on_lxmf_delivery(msg)
    delivery_app.sideband_plugin_loader.handle_plugin_command.assert_not_called()
