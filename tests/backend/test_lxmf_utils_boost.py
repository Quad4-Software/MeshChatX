from unittest.mock import MagicMock
from meshchatx.src.backend.lxmf_utils import (
    convert_lxmf_state_to_string,
    convert_lxmf_method_to_string,
    convert_db_lxmf_message_to_dict,
)
import LXMF


def test_convert_lxmf_state_to_string():
    msg = MagicMock(spec=LXMF.LXMessage)
    msg.state = LXMF.LXMessage.OUTBOUND
    assert convert_lxmf_state_to_string(msg) == "outbound"
    msg.state = LXMF.LXMessage.DELIVERED
    assert convert_lxmf_state_to_string(msg) == "delivered"
    msg.state = 999
    assert convert_lxmf_state_to_string(msg) == "unknown"


def test_convert_lxmf_method_to_string():
    msg = MagicMock(spec=LXMF.LXMessage)
    msg.method = LXMF.LXMessage.DIRECT
    assert convert_lxmf_method_to_string(msg) == "direct"
    msg.method = LXMF.LXMessage.PROPAGATED
    assert convert_lxmf_method_to_string(msg) == "propagated"
    msg.method = 999
    assert convert_lxmf_method_to_string(msg) == "unknown"


def test_convert_db_lxmf_message_to_dict_basic():
    db_msg = {
        "id": 1,
        "hash": "h",
        "source_hash": "s",
        "destination_hash": "d",
        "is_incoming": 1,
        "state": "sent",
        "progress": 100,
        "method": "direct",
        "delivery_attempts": 1,
        "next_delivery_attempt_at": None,
        "title": "T",
        "content": "C",
        "fields": '{"f": "v"}',
        "timestamp": 123,
        "rssi": -50,
        "snr": 10,
        "quality": 3,
        "is_spam": 0,
        "created_at": "2026-01-01 12:00:00",
        "updated_at": "2026-01-01 12:00:00",
    }
    res = convert_db_lxmf_message_to_dict(db_msg)
    assert res["id"] == 1
    assert res["fields"] == {"f": "v"}
    assert res["created_at"].endswith("Z")


def test_convert_db_lxmf_message_to_dict_strip_attachments():
    db_msg = {
        "id": 1,
        "hash": "h",
        "source_hash": "s",
        "destination_hash": "d",
        "is_incoming": 1,
        "state": "sent",
        "progress": 100,
        "method": "direct",
        "delivery_attempts": 1,
        "next_delivery_attempt_at": None,
        "title": "T",
        "content": "C",
        "fields": '{"image": {"image_type": "png", "image_bytes": "base64"}}',
        "timestamp": 123,
        "rssi": -50,
        "snr": 10,
        "quality": 3,
        "is_spam": 0,
        "created_at": "2026-01-01 12:00:00",
        "updated_at": "2026-01-01 12:00:00",
    }
    res = convert_db_lxmf_message_to_dict(db_msg, include_attachments=False)
    assert res["fields"]["image"]["image_bytes"] is None
    assert res["fields"]["image"]["image_size"] > 0
