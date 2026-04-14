from unittest.mock import MagicMock

import LXMF
from hypothesis import given
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat


def get_mock_mesh_chat():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.current_context = MagicMock()
    app.reticulum = MagicMock()
    return app


@given(content=st.text())
def test_fuzz_reply_detection_no_crash(content):
    mesh_chat = get_mock_mesh_chat()
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.hash = b"h" * 16
    mock_msg.source_hash = b"s" * 16
    mock_msg.destination_hash = b"d" * 16
    mock_msg.content = content.encode("utf-8", errors="replace")
    mock_msg.get_fields.return_value = {}
    mock_msg.timestamp = 0
    mock_msg.progress = 0
    mock_msg.incoming = True
    mock_msg.state = 0
    mock_msg.method = 0
    mock_msg.delivery_attempts = 0
    mock_msg.title = b""
    mock_msg.rssi = 0
    mock_msg.snr = 0
    mock_msg.q = 0

    mesh_chat.db_upsert_lxmf_message(mock_msg)


def test_explicit_reply_detection():
    mesh_chat = get_mock_mesh_chat()
    test_hash = "a" * 32
    content = f"> {test_hash}\nThis is a reply"

    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.hash = b"h" * 16
    mock_msg.source_hash = b"s" * 16
    mock_msg.destination_hash = b"d" * 16
    mock_msg.content = content.encode("utf-8")
    mock_msg.get_fields.return_value = {}
    mock_msg.timestamp = 0
    mock_msg.progress = 0
    mock_msg.incoming = True
    mock_msg.state = 0
    mock_msg.method = 0
    mock_msg.delivery_attempts = 0
    mock_msg.title = b""
    mock_msg.rssi = 0
    mock_msg.snr = 0
    mock_msg.q = 0

    # Mock database upsert to capture what was sent
    mesh_chat.current_context.database.messages.upsert_lxmf_message = MagicMock()
    mesh_chat.current_context.local_lxmf_destination.hexhash = "local"

    mesh_chat.db_upsert_lxmf_message(mock_msg)

    args, _ = mesh_chat.current_context.database.messages.upsert_lxmf_message.call_args
    upserted_dict = args[0]

    assert upserted_dict["reply_to_hash"] == test_hash
