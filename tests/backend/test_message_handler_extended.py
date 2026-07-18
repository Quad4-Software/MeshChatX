# SPDX-License-Identifier: 0BSD

from unittest.mock import MagicMock

import pytest

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
    assert "SELECT *" not in query
    assert "fields_meta" in query
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

    assert mock_db.provider.execute.call_count == 4
    calls = [mock_db.provider.execute.call_args_list[i][0] for i in range(4)]
    assert "DELETE FROM lxmf_messages" in calls[0][0]
    assert calls[0][1] == ["peer"]
    assert "DELETE FROM lxmf_conversation_read_state" in calls[1][0]
    assert calls[1][1] == ["peer"]
    assert "DELETE FROM lxmf_conversation_folders" in calls[2][0]
    assert calls[2][1] == ["peer"]
    assert "DELETE FROM lxmf_conversation_pins" in calls[3][0]
    assert calls[3][1] == ["peer"]


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
    assert "FROM lxmf_conversation_summaries s" in query
    assert "content_preview" in query
    assert "has_image" in query
    assert "has_attachments" in query
    assert "failed_count" in query
    assert "has_contact_image" in query
    # Full attachment blobs and contact images must never be selected into the list API.
    assert ", m1.fields," not in query
    assert "con.custom_image as contact_image" not in query
    assert "SELECT peer_hash, MAX(id) as max_id" not in query
    assert "FROM lxmf_messages\n                WHERE state = 'failed'" not in query


def test_get_conversations_with_filters(mock_db):
    handler = MessageHandler(mock_db)
    handler.get_conversations(
        "local",
        search="test",
        filter_unread=True,
        filter_failed=True,
        filter_has_attachments=True,
    )

    args, _ = mock_db.provider.fetchall.call_args
    query = args[0]
    params = args[1]
    # Check if any part of the query matches search or filters
    assert "s.peer_hash" in query
    assert "s.state = 'failed'" in query
    assert "COALESCE(s.has_image" in query or "has_image" in query
    assert "%test%" in params


def test_clamp_conversations_limit():
    from meshchatx.src.backend.message_handler import MessageHandler

    assert MessageHandler.clamp_conversations_limit(None) == 500
    assert MessageHandler.clamp_conversations_limit(50) == 50
    assert MessageHandler.clamp_conversations_limit(99999) == 2000
    assert MessageHandler.clamp_conversations_limit(-1) == 0
    assert MessageHandler.clamp_conversations_limit("nope") == 500
