# SPDX-License-Identifier: 0BSD

import json
import time
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.messages import MessageDAO
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def message_dao(mock_provider):
    return MessageDAO(mock_provider)


@pytest.fixture
def real_db(tmp_path):
    db_path = str(tmp_path / "messages.db")
    provider = DatabaseProvider(db_path)
    DatabaseSchema(provider).initialize()
    return Database(db_path)


def _insert_message(db, hash_hex, *, is_incoming, state, method="direct"):
    peer = "b" * 32
    db.messages.upsert_lxmf_message(
        {
            "hash": hash_hex,
            "source_hash": peer,
            "destination_hash": peer,
            "peer_hash": peer,
            "state": state,
            "progress": 0.0,
            "is_incoming": is_incoming,
            "method": method,
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "t",
            "content": "c",
            "fields": None,
            "timestamp": time.time(),
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
        },
    )


def test_mark_stuck_messages_never_fails_incoming_messages(real_db):
    # Incoming messages are stored with the default "generating" state and must
    # never be flagged as failed by the stuck-message sweep.
    _insert_message(real_db, "a" * 32, is_incoming=1, state="generating")
    # Outbound messages stuck mid-send should be failed.
    _insert_message(real_db, "c" * 32, is_incoming=0, state="generating")
    _insert_message(real_db, "d" * 32, is_incoming=0, state="sending")
    _insert_message(real_db, "e" * 32, is_incoming=0, state="delivered")

    real_db.messages.mark_stuck_messages_as_failed()

    assert real_db.messages.get_lxmf_message_by_hash("a" * 32)["state"] == "generating"
    assert real_db.messages.get_lxmf_message_by_hash("c" * 32)["state"] == "failed"
    assert real_db.messages.get_lxmf_message_by_hash("d" * 32)["state"] == "failed"
    assert real_db.messages.get_lxmf_message_by_hash("e" * 32)["state"] == "delivered"


def test_mark_stuck_messages_repairs_previously_failed_incoming(real_db):
    # Simulate a database corrupted by the previous buggy sweep that flipped
    # received messages to "failed".
    _insert_message(real_db, "a" * 32, is_incoming=1, state="failed")

    real_db.messages.mark_stuck_messages_as_failed()

    assert real_db.messages.get_lxmf_message_by_hash("a" * 32)["state"] == "generating"


def test_normalize_lxmf_message_for_import_strips_export_metadata():
    row = {
        "id": 1,
        "hash": "a" * 64,
        "source_hash": "b" * 32,
        "destination_hash": "c" * 32,
        "state": "generating",
        "is_incoming": 1,
        "fields": "{}",
        "created_at": "2026-05-09T01:12:37.063720+00:00",
        "lxmf_icon": {"icon_name": "account"},
    }
    normalized = MessageDAO.normalize_lxmf_message_for_import(row)
    assert normalized is not None
    assert normalized["peer_hash"] == "b" * 32
    assert "id" not in normalized
    assert "lxmf_icon" not in normalized


def test_import_lxmf_messages_skips_invalid_rows(real_db):
    messages = [
        {"hash": "a" * 64, "source_hash": "b" * 32, "destination_hash": "c" * 32},
        {"hash": "", "source_hash": "b" * 32, "destination_hash": "c" * 32},
    ]
    result = real_db.messages.import_lxmf_messages(messages)
    assert result["imported"] == 1
    assert result["skipped"] == 1
    assert result["errors"] == []


def test_import_lxmf_messages_without_attachments_stripped_column(tmp_path):
    db_path = str(tmp_path / "legacy.db")
    provider = DatabaseProvider(db_path)
    DatabaseSchema(provider).initialize()
    provider.execute("ALTER TABLE lxmf_messages DROP COLUMN attachments_stripped")
    db = Database(db_path)

    result = db.messages.import_lxmf_messages(
        [
            {
                "id": 1,
                "hash": "a" * 64,
                "source_hash": "b" * 32,
                "destination_hash": "c" * 32,
                "peer_hash": "b" * 32,
                "state": "generating",
                "progress": 0,
                "is_incoming": 1,
                "method": "opportunistic",
                "fields": "{}",
                "timestamp": 1773512977.322906,
                "attachments_stripped": 0,
            },
        ],
    )
    assert result["imported"] == 1
    assert result["errors"] == []


def test_upsert_lxmf_message(message_dao, mock_provider):
    mock_provider.fetchall.return_value = [
        {"name": field}
        for field in (
            "hash",
            "source_hash",
            "destination_hash",
            "peer_hash",
            "state",
            "progress",
            "is_incoming",
            "method",
            "delivery_attempts",
            "next_delivery_attempt_at",
            "title",
            "content",
            "fields",
            "timestamp",
            "rssi",
            "snr",
            "quality",
            "is_spam",
            "reply_to_hash",
            "attachments_stripped",
            "path_hops_at_send",
            "path_interface_at_send",
            "path_finding_measure",
            "path_row_hash_hex",
            "created_at",
            "updated_at",
        )
    ]
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
        "SELECT * FROM lxmf_messages WHERE hash = ?",
        ("hash1",),
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


def test_set_lxmf_message_path_at_send_if_unset(message_dao, mock_provider):
    message_dao.set_lxmf_message_path_at_send_if_unset("deadbeef", 2, "UDP Interface")
    args, _ = mock_provider.execute.call_args
    query, params = args
    assert "path_hops_at_send" in query
    assert "path_hops_at_send IS NULL" in query
    assert params[0] == 2
    assert params[1] == "UDP Interface"
    assert params[3] == "deadbeef"
