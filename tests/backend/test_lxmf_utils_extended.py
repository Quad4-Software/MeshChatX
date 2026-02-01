import base64
import json
from unittest.mock import MagicMock

import LXMF

from meshchatx.src.backend.lxmf_utils import (
    convert_db_lxmf_message_to_dict,
    convert_lxmf_message_to_dict,
    convert_lxmf_state_to_string,
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
        "created_at": "2023-01-01 12:00:00",
        "updated_at": "2023-01-01 12:05:00",
    }

    # Test with attachments
    result = convert_db_lxmf_message_to_dict(db_msg, include_attachments=True)
    assert result["fields"]["image"]["image_bytes"] is not None
    assert result["created_at"].endswith("Z")

    # Test without attachments
    result_no_att = convert_db_lxmf_message_to_dict(db_msg, include_attachments=False)
    assert result_no_att["fields"]["image"]["image_bytes"] is None
    assert result_no_att["fields"]["image"]["image_size"] == len(b"img")
    assert result_no_att["fields"]["audio"]["audio_size"] == len(b"audio")
    assert result_no_att["fields"]["file_attachments"][0]["file_size"] == len(b"file")


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
