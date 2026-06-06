# SPDX-License-Identifier: 0BSD

import base64
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import LXMF

from meshchatx.src.backend.lxmf_utils import (
    compute_lxmf_conversation_unread_from_latest_row,
    convert_db_lxmf_message_to_dict,
    convert_lxmf_message_to_dict,
    convert_lxmf_state_to_string,
    lxmf_message_solving_stamps,
    lxmf_sidebar_preview_for_conversation_latest_row,
)


def test_convert_lxmf_message_to_dict_basic():
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.hash = b"msg_hash"
    mock_msg.source_hash = b"src_hash"
    mock_msg.destination_hash = b"dst_hash"
    mock_msg.incoming = True
    mock_msg.state = LXMF.LXMessage.SENT
    mock_msg.progress = 0.5
    mock_msg.method = LXMF.LXMessage.DIRECT
    mock_msg.delivery_attempts = 1
    mock_msg.title = b"Test Title"
    mock_msg.content = b"Test Content"
    mock_msg.timestamp = 1234567890
    mock_msg.rssi = -50
    mock_msg.snr = 10
    mock_msg.q = 3
    mock_msg.get_fields.return_value = {}

    result = convert_lxmf_message_to_dict(mock_msg)

    assert result["hash"] == "6d73675f68617368"
    assert result["title"] == "Test Title"
    assert result["content"] == "Test Content"
    assert result["progress"] == 50.0
    assert result["state"] == "sent"
    assert result["method"] == "direct"
    assert result["solving_stamps"] is False


def test_lxmf_message_solving_stamps_deferred_outbound():
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.incoming = False
    mock_msg.outbound_ticket = None
    mock_msg.stamp_cost = 16
    mock_msg.stamp = None
    mock_msg.defer_stamp = True
    mock_msg.desired_method = LXMF.LXMessage.DIRECT
    mock_msg.defer_propagation_stamp = True
    mock_msg.propagation_stamp = None
    mock_msg.state = LXMF.LXMessage.OUTBOUND
    mock_msg.message_id = b"msg_id"

    router = MagicMock()
    router.pending_deferred_stamps = {b"msg_id": mock_msg}

    assert lxmf_message_solving_stamps(mock_msg, router) is True


def test_lxmf_message_solving_stamps_false_with_ticket():
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.incoming = False
    mock_msg.outbound_ticket = b"ticket"
    mock_msg.stamp_cost = 16
    mock_msg.stamp = None
    mock_msg.defer_stamp = True
    mock_msg.state = LXMF.LXMessage.OUTBOUND

    assert lxmf_message_solving_stamps(mock_msg) is False


def test_lxmf_message_solving_stamps_false_after_stamp_generated():
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.incoming = False
    mock_msg.outbound_ticket = None
    mock_msg.stamp_cost = 16
    mock_msg.stamp = b"stamp_bytes"
    mock_msg.defer_stamp = True
    mock_msg.state = LXMF.LXMessage.OUTBOUND

    assert lxmf_message_solving_stamps(mock_msg) is False


def test_convert_lxmf_message_to_dict_includes_solving_stamps():
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.hash = b"hash"
    mock_msg.source_hash = b"src"
    mock_msg.destination_hash = b"dst"
    mock_msg.incoming = False
    mock_msg.outbound_ticket = None
    mock_msg.stamp_cost = 8
    mock_msg.stamp = None
    mock_msg.defer_stamp = True
    mock_msg.desired_method = LXMF.LXMessage.DIRECT
    mock_msg.defer_propagation_stamp = True
    mock_msg.propagation_stamp = None
    mock_msg.state = LXMF.LXMessage.OUTBOUND
    mock_msg.message_id = b"mid"
    mock_msg.progress = 0.0
    mock_msg.method = LXMF.LXMessage.DIRECT
    mock_msg.delivery_attempts = 0
    mock_msg.title = b""
    mock_msg.content = b"hi"
    mock_msg.timestamp = 1
    mock_msg.rssi = None
    mock_msg.snr = None
    mock_msg.q = None
    mock_msg.get_fields.return_value = {}

    router = MagicMock()
    router.pending_deferred_stamps = {b"mid": mock_msg}

    result = convert_lxmf_message_to_dict(mock_msg, message_router=router)
    assert result["solving_stamps"] is True


def test_convert_lxmf_message_to_dict_with_attachments():
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.hash = b"hash"
    mock_msg.source_hash = b"src"
    mock_msg.destination_hash = b"dst"
    mock_msg.incoming = False
    mock_msg.state = LXMF.LXMessage.DELIVERED
    mock_msg.progress = 1.0
    mock_msg.method = LXMF.LXMessage.PROPAGATED
    mock_msg.delivery_attempts = 1
    mock_msg.title = b""
    mock_msg.content = b""
    mock_msg.timestamp = 1234567890
    mock_msg.rssi = None
    mock_msg.snr = None
    mock_msg.q = None

    # Setup fields
    fields = {
        LXMF.FIELD_FILE_ATTACHMENTS: [("file1.txt", b"content1")],
        LXMF.FIELD_IMAGE: ("png", b"image_data"),
        LXMF.FIELD_AUDIO: ("voice", b"audio_data"),
    }
    mock_msg.get_fields.return_value = fields

    result = convert_lxmf_message_to_dict(mock_msg)

    assert result["fields"]["file_attachments"][0]["file_name"] == "file1.txt"
    assert (
        result["fields"]["file_attachments"][0]["file_bytes"]
        == base64.b64encode(b"content1").decode()
    )
    assert result["fields"]["image"]["image_type"] == "png"
    assert (
        result["fields"]["image"]["image_bytes"]
        == base64.b64encode(b"image_data").decode()
    )
    assert result["fields"]["audio"]["audio_mode"] == "voice"
    assert (
        result["fields"]["audio"]["audio_bytes"]
        == base64.b64encode(b"audio_data").decode()
    )


def test_convert_lxmf_state_to_string():
    mock_msg = MagicMock()

    states = {
        LXMF.LXMessage.GENERATING: "generating",
        LXMF.LXMessage.OUTBOUND: "outbound",
        LXMF.LXMessage.SENDING: "sending",
        LXMF.LXMessage.SENT: "sent",
        LXMF.LXMessage.DELIVERED: "delivered",
        LXMF.LXMessage.REJECTED: "rejected",
        LXMF.LXMessage.CANCELLED: "cancelled",
        LXMF.LXMessage.FAILED: "failed",
    }

    for state, expected in states.items():
        mock_msg.state = state
        assert convert_lxmf_state_to_string(mock_msg) == expected


def test_convert_db_lxmf_message_to_dict():
    db_msg = {
        "id": 1,
        "hash": "hash_hex",
        "source_hash": "src_hex",
        "destination_hash": "dst_hex",
        "is_incoming": 1,
        "state": "delivered",
        "progress": 100.0,
        "method": "direct",
        "delivery_attempts": 1,
        "next_delivery_attempt_at": None,
        "title": "Title",
        "content": "Content",
        "fields": json.dumps(
            {
                "image": {
                    "image_type": "jpg",
                    "image_bytes": base64.b64encode(b"img").decode(),
                },
                "audio": {
                    "audio_mode": "ogg",
                    "audio_bytes": base64.b64encode(b"audio").decode(),
                },
                "file_attachments": [
                    {
                        "file_name": "f.txt",
                        "file_bytes": base64.b64encode(b"file").decode(),
                    },
                ],
            },
        ),
        "timestamp": 1234567890,
        "rssi": -60,
        "snr": 5,
        "quality": 2,
        "is_spam": 0,
        "path_hops_at_send": 4,
        "path_interface_at_send": "RNode Interface",
        "created_at": "2023-01-01 12:00:00",
        "updated_at": "2023-01-01 12:05:00",
    }

    # Test with attachments
    result = convert_db_lxmf_message_to_dict(db_msg, include_attachments=True)
    assert result["fields"]["image"]["image_bytes"] is not None
    assert result["created_at"].endswith("Z")
    assert result["path_hops_at_send"] == 4
    assert result["path_interface_at_send"] == "RNode Interface"

    # Test without attachments
    result_no_att = convert_db_lxmf_message_to_dict(db_msg, include_attachments=False)
    assert result_no_att["fields"]["image"]["image_bytes"] is None
    assert result_no_att["fields"]["image"]["image_size"] == len(b"img")
    assert result_no_att["fields"]["audio"]["audio_size"] == len(b"audio")
    assert result_no_att["fields"]["file_attachments"][0]["file_size"] == len(b"file")


def test_convert_db_lxmf_message_to_dict_defaults_missing_method():
    db_msg = {
        "id": 1,
        "hash": "a" * 32,
        "source_hash": "b" * 32,
        "destination_hash": "c" * 32,
        "is_incoming": 0,
        "state": "sent",
        "progress": 100.0,
        "delivery_attempts": 0,
        "next_delivery_attempt_at": None,
        "title": "",
        "content": "x",
        "fields": "{}",
        "timestamp": 1.0,
        "rssi": None,
        "snr": None,
        "quality": None,
        "is_spam": 0,
        "created_at": "2023-01-01 12:00:00",
        "updated_at": "2023-01-01 12:00:00",
    }
    result = convert_db_lxmf_message_to_dict(db_msg)
    assert result["method"] == "unknown"


def test_convert_lxmf_message_to_dict_with_reply():
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.hash = b"msg_hash"
    mock_msg.source_hash = b"src_hash"
    mock_msg.destination_hash = b"dst_hash"
    mock_msg.incoming = True
    mock_msg.state = LXMF.LXMessage.SENT
    mock_msg.progress = 1.0
    mock_msg.method = LXMF.LXMessage.DIRECT
    mock_msg.delivery_attempts = 1
    mock_msg.title = b""
    mock_msg.content = b"Reply text"
    mock_msg.timestamp = 1234567890
    mock_msg.rssi = None
    mock_msg.snr = None
    mock_msg.q = None

    # Reply to hash
    reply_hash = b"original_msg_hash"
    mock_msg.get_fields.return_value = {0x30: reply_hash}

    result = convert_lxmf_message_to_dict(mock_msg)
    assert result["fields"]["reply_to"] == reply_hash.hex()


def test_convert_db_lxmf_message_to_dict_with_reply():
    db_msg = {
        "id": 1,
        "hash": "hash_hex",
        "source_hash": "src_hex",
        "destination_hash": "dst_hex",
        "is_incoming": 1,
        "state": "delivered",
        "progress": 100.0,
        "method": "direct",
        "delivery_attempts": 1,
        "next_delivery_attempt_at": None,
        "title": "Title",
        "content": "Content",
        "fields": "{}",
        "timestamp": 1234567890,
        "rssi": -60,
        "snr": 5,
        "quality": 2,
        "is_spam": 0,
        "reply_to_hash": "original_hash_hex",
        "created_at": "2023-01-01 12:00:00",
        "updated_at": "2023-01-01 12:05:00",
    }
    result = convert_db_lxmf_message_to_dict(db_msg)
    assert result["reply_to_hash"] == "original_hash_hex"


def test_compute_unread_outgoing_latest_never_unread_even_without_read_cursor():
    row = {
        "is_incoming": 0,
        "last_read_at": None,
        "timestamp": 1_700_000_000.0,
    }
    assert compute_lxmf_conversation_unread_from_latest_row(row) is False


def test_compute_unread_incoming_no_read_cursor_is_unread():
    row = {
        "is_incoming": 1,
        "last_read_at": None,
        "timestamp": 1_700_000_000.0,
    }
    assert compute_lxmf_conversation_unread_from_latest_row(row) is True


def test_compute_unread_incoming_not_unread_when_read_cursor_covers_message():
    ts = 1_700_000_000.0
    read_after_msg = datetime.fromtimestamp(ts + 60, UTC).isoformat()
    row = {
        "is_incoming": 1,
        "last_read_at": read_after_msg,
        "timestamp": ts,
    }
    assert compute_lxmf_conversation_unread_from_latest_row(row) is False


def test_compute_unread_incoming_newer_than_read_cursor_unread():
    ts = 1_700_000_000.0
    read = datetime.fromtimestamp(ts - 120, UTC).isoformat()
    row = {
        "is_incoming": 1,
        "last_read_at": read,
        "timestamp": ts,
    }
    assert compute_lxmf_conversation_unread_from_latest_row(row) is True


def test_sidebar_preview_reaction_incoming_uses_peer_name():
    local = "a" * 32
    row = {
        "content": "",
        "fields": json.dumps(
            {"reaction": {"reaction_to": "abc123", "reaction_content": "\U0001f44d"}},
        ),
        "is_incoming": 1,
        "source_hash": "b" * 32,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash=local,
        peer_display_name="Charlie",
    )
    assert out == "Charlie reacted \U0001f44d"


def test_sidebar_preview_reaction_outbound_from_self_is_you():
    me = "c" * 32
    row = {
        "content": "",
        "fields": json.dumps(
            {"reaction": {"reaction_to": "abc123", "reaction_content": "\u2764\ufe0f"}},
        ),
        "is_incoming": 0,
        "source_hash": me,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash=me,
        peer_display_name="Dana",
    )
    assert out == "You reacted \u2764\ufe0f"


def test_sidebar_preview_prefers_non_empty_content():
    row = {
        "content": " hi ",
        "fields": json.dumps(
            {"reaction": {"reaction_to": "abc123", "reaction_content": "\U0001f44d"}},
        ),
        "is_incoming": 1,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash="a" * 32,
        peer_display_name="Eve",
    )
    assert out == " hi "


def test_sidebar_preview_telemetry_location_incoming():
    local = "a" * 32
    row = {
        "content": "",
        "fields": json.dumps(
            {"telemetry": {"location": {"latitude": 1.0, "longitude": 2.0}}},
        ),
        "is_incoming": 1,
        "source_hash": "b" * 32,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash=local,
        peer_display_name="Riley",
    )
    assert out == "Riley shared their location"


def test_sidebar_preview_telemetry_location_outbound_you():
    me = "c" * 32
    row = {
        "content": "",
        "fields": json.dumps(
            {"telemetry": {"location": {"latitude": 1.0, "longitude": 2.0}}},
        ),
        "is_incoming": 0,
        "source_hash": me,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash=me,
        peer_display_name="Sam",
    )
    assert out == "You shared your location"


def test_sidebar_preview_location_request_outbound_you():
    me = "c" * 32
    row = {
        "content": "",
        "fields": json.dumps({"commands": [{"0x01": 1_700_000_000}]}),
        "is_incoming": 0,
        "source_hash": me,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash=me,
        peer_display_name="Sam",
    )
    assert out == "You sent a location request"


def test_sidebar_preview_telemetry_battery_only():
    row = {
        "content": "",
        "fields": json.dumps({"telemetry": {"battery": {"charge_percent": 50}}}),
        "is_incoming": 1,
        "source_hash": "b" * 32,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash="a" * 32,
        peer_display_name="Taylor",
    )
    assert out == "Taylor sent telemetry"


def test_sidebar_preview_telemetry_stream():
    row = {
        "content": "",
        "fields": json.dumps({"telemetry_stream": [{"t": 1}]}),
        "is_incoming": 1,
        "source_hash": "b" * 32,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash="a" * 32,
        peer_display_name="Jordan",
    )
    assert out == "Jordan sent a telemetry stream"


def test_sidebar_preview_image_incoming():
    row = {
        "content": "",
        "fields": json.dumps({"image": {"image_type": "png", "image_size": 12}}),
        "is_incoming": 1,
        "source_hash": "b" * 32,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash="a" * 32,
        peer_display_name="Quinn",
    )
    assert out == "Quinn sent an image"


def test_sidebar_preview_image_outbound_you():
    me = "c" * 32
    row = {
        "content": "",
        "fields": json.dumps({"image": {"image_type": "jpeg", "image_size": 99}}),
        "is_incoming": 0,
        "source_hash": me,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash=me,
        peer_display_name="Pat",
    )
    assert out == "You sent an image"


def test_sidebar_preview_audio_voice_note():
    row = {
        "content": "",
        "fields": json.dumps({"audio": {"audio_mode": "opus", "audio_size": 500}}),
        "is_incoming": 1,
        "source_hash": "b" * 32,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash="a" * 32,
        peer_display_name="Morgan",
    )
    assert out == "Morgan sent a voice note"


def test_sidebar_preview_file_attachments_plural():
    row = {
        "content": "",
        "fields": json.dumps(
            {
                "file_attachments": [
                    {"file_name": "a.txt", "file_size": 1},
                    {"file_name": "b.txt", "file_size": 2},
                ],
            },
        ),
        "is_incoming": 0,
        "source_hash": "d" * 32,
    }
    out = lxmf_sidebar_preview_for_conversation_latest_row(
        row,
        local_hash="d" * 32,
        peer_display_name="Casey",
    )
    assert out == "You sent 2 files"
