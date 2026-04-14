import json
from unittest.mock import MagicMock

import LXMF

from meshchatx.src.backend.lxmf_utils import (
    LXMF_APP_EXTENSIONS_FIELD,
    convert_db_lxmf_message_to_dict,
    convert_lxmf_message_to_dict,
    lxmf_fields_are_columba_reaction,
)


def test_lxmf_fields_are_columba_reaction():
    assert lxmf_fields_are_columba_reaction({}) is False
    assert lxmf_fields_are_columba_reaction({16: {"reaction_to": "abc"}}) is True
    assert lxmf_fields_are_columba_reaction({16: {"reply_to": "x"}}) is False


def test_convert_lxmf_message_to_dict_reaction_field_16():
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.hash = b"h" * 8
    mock_msg.source_hash = b"s" * 8
    mock_msg.destination_hash = b"d" * 8
    mock_msg.incoming = True
    mock_msg.state = LXMF.LXMessage.SENT
    mock_msg.progress = 1.0
    mock_msg.method = LXMF.LXMessage.OPPORTUNISTIC
    mock_msg.delivery_attempts = 0
    mock_msg.title = b""
    mock_msg.content = b""
    mock_msg.timestamp = 1000
    mock_msg.rssi = None
    mock_msg.snr = None
    mock_msg.q = None
    target = "a" * 32
    mock_msg.get_fields.return_value = {
        LXMF_APP_EXTENSIONS_FIELD: {
            "reaction_to": target,
            "emoji": "\U0001f44d",
            "sender": "f" * 32,
        }
    }

    out = convert_lxmf_message_to_dict(mock_msg, include_attachments=False)

    assert out["is_reaction"] is True
    assert out["reaction_to"] == target
    assert out["reaction_emoji"] == "\U0001f44d"
    assert out["reaction_sender"] == "f" * 32
    assert "app_extensions" in out["fields"]
    assert out["fields"]["app_extensions"]["reaction_to"] == target


def test_convert_db_lxmf_message_to_dict_reaction():
    target = "aa" * 16
    fields_obj = {
        "app_extensions": {
            "reaction_to": target,
            "emoji": "\u2764\ufe0f",
            "sender": "11" * 16,
        }
    }
    row = {
        "id": 1,
        "hash": "ab" * 16,
        "source_hash": "cd" * 16,
        "destination_hash": "ef" * 16,
        "is_incoming": 1,
        "state": "delivered",
        "progress": 100.0,
        "method": "opportunistic",
        "delivery_attempts": 0,
        "next_delivery_attempt_at": None,
        "title": "",
        "content": "",
        "fields": json.dumps(fields_obj),
        "timestamp": 1.0,
        "rssi": None,
        "snr": None,
        "quality": None,
        "is_spam": 0,
        "reply_to_hash": None,
        "attachments_stripped": 0,
        "created_at": "2020-01-01T00:00:00",
        "updated_at": "2020-01-01T00:00:00",
    }

    out = convert_db_lxmf_message_to_dict(row, include_attachments=False)
    assert out["is_reaction"] is True
    assert out["reaction_to"] == target
    assert out["reaction_emoji"] == "\u2764\ufe0f"
    assert out["reaction_sender"] == "11" * 16


def test_convert_lxmf_message_to_dict_non_reaction_field_16_reply_to():
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.hash = b"h" * 8
    mock_msg.source_hash = b"s" * 8
    mock_msg.destination_hash = b"d" * 8
    mock_msg.incoming = True
    mock_msg.state = LXMF.LXMessage.SENT
    mock_msg.progress = 1.0
    mock_msg.method = LXMF.LXMessage.DIRECT
    mock_msg.delivery_attempts = 0
    mock_msg.title = b""
    mock_msg.content = b"hi"
    mock_msg.timestamp = 1000
    mock_msg.rssi = None
    mock_msg.snr = None
    mock_msg.q = None
    mock_msg.get_fields.return_value = {
        LXMF_APP_EXTENSIONS_FIELD: {"reply_to": "someid", "pending": True},
    }

    out = convert_lxmf_message_to_dict(mock_msg, include_attachments=False)
    assert out["is_reaction"] is False
    assert "reaction_to" not in out
    assert "app_extensions" in out["fields"]
