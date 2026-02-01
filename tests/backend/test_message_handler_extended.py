import pytest
from unittest.mock import MagicMock
from meshchatx.src.backend.message_handler import MessageHandler


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.provider = MagicMock()
    return db


def test_get_conversation_messages(mock_db):
    handler = MessageHandler(mock_db)
    handler.get_conversation_messages("local", "peer", limit=50, offset=10)

    args, _ = mock_db.provider.fetchall.call_args
    query, params = args
    assert "peer_hash = ?" in query
    assert "LIMIT ? OFFSET ?" in query
    assert params == ["peer", 50, 10]


def test_get_conversation_messages_with_ids(mock_db):
    handler = MessageHandler(mock_db)
    handler.get_conversation_messages("local", "peer", after_id=100, before_id=200)

    args, _ = mock_db.provider.fetchall.call_args
    query, params = args
    assert "id > ?" in query
    assert "id < ?" in query
    assert 100 in params
    assert 200 in params


def test_delete_conversation(mock_db):
    handler = MessageHandler(mock_db)
    handler.delete_conversation("local", "peer")

    assert mock_db.provider.execute.call_count == 2
    args1, _ = mock_db.provider.execute.call_args_list[0]
    assert "DELETE FROM lxmf_messages" in args1[0]
    assert args1[1] == ["peer"]


def test_search_messages(mock_db):
    handler = MessageHandler(mock_db)
    handler.search_messages("local", "hello")

    args, _ = mock_db.provider.fetchall.call_args
    assert "%hello%" in args[1]


def test_get_conversations_base(mock_db):
    handler = MessageHandler(mock_db)
    handler.get_conversations("local")

    args, _ = mock_db.provider.fetchall.call_args
    query = args[0]
    assert "SELECT" in query
    assert "FROM lxmf_messages m1" in query


def test_get_conversations_with_filters(mock_db):
    handler = MessageHandler(mock_db)
    handler.get_conversations(
        "local", search="test", filter_unread=True, filter_failed=True
    )

    args, _ = mock_db.provider.fetchall.call_args
    query = args[0]
    params = args[1]
    # Check if any part of the query matches search or filters
    assert "m1.peer_hash" in query
    assert "m1.state = 'failed'" in query
    assert "%test%" in params
