import pytest
import json
from unittest.mock import MagicMock
from meshchatx.src.backend.database.messages import MessageDAO


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def message_dao(mock_provider):
    return MessageDAO(mock_provider)


def test_upsert_lxmf_message(message_dao, mock_provider):
    data = {"hash": "hash1", "content": "hello", "fields": {"key": "val"}}
    message_dao.upsert_lxmf_message(data)

    args, _ = mock_provider.execute.call_args
    query, params = args
    assert "INSERT INTO lxmf_messages" in query
    assert "hash1" in params
    assert "hello" in params
    assert json.dumps({"key": "val"}) in params


def test_get_lxmf_message_by_hash(message_dao, mock_provider):
    message_dao.get_lxmf_message_by_hash("hash1")
    mock_provider.fetchone.assert_called_with(
        "SELECT * FROM lxmf_messages WHERE hash = ?", ("hash1",)
    )


def test_delete_lxmf_messages_by_hashes(message_dao, mock_provider):
    message_dao.delete_lxmf_messages_by_hashes(["h1", "h2"])
    args, _ = mock_provider.execute.call_args
    assert "DELETE FROM lxmf_messages WHERE hash IN (?, ?)" in args[0]
    assert args[1] == ("h1", "h2")


def test_delete_all_lxmf_messages(message_dao, mock_provider):
    message_dao.delete_all_lxmf_messages()
    assert mock_provider.execute.call_count == 2


def test_get_conversation_messages(message_dao, mock_provider):
    message_dao.get_conversation_messages("peer1", limit=10, offset=5)
    mock_provider.fetchall.assert_called_with(
        "SELECT * FROM lxmf_messages WHERE peer_hash = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        ("peer1", 10, 5),
    )
