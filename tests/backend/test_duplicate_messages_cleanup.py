# SPDX-License-Identifier: 0BSD

import time

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


def _msg(db, *, msg_hash, peer, content, is_incoming=1, ts=None):
    now = ts if ts is not None else time.time()
    db.messages.upsert_lxmf_message(
        {
            "hash": msg_hash,
            "source_hash": peer,
            "destination_hash": peer,
            "peer_hash": peer,
            "state": "delivered",
            "progress": 1.0,
            "is_incoming": is_incoming,
            "method": "direct",
            "delivery_attempts": 1,
            "next_delivery_attempt_at": None,
            "title": "",
            "content": content,
            "fields": "{}",
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
            "timestamp": now,
        },
    )


def test_delete_duplicate_messages_by_content_keeps_oldest(tmp_path):
    path = str(tmp_path / "d.db")
    provider = DatabaseProvider(path)
    DatabaseSchema(provider).initialize()
    db = Database(path)
    peer = "a" * 32
    base = time.time()
    _msg(db, msg_hash="1" * 32, peer=peer, content="hello", ts=base - 30)
    _msg(db, msg_hash="2" * 32, peer=peer, content="hello", ts=base - 20)
    _msg(db, msg_hash="3" * 32, peer=peer, content="hello", ts=base - 10)
    _msg(db, msg_hash="4" * 32, peer=peer, content="other", ts=base)
    _msg(db, msg_hash="5" * 32, peer=peer, content="", ts=base)
    _msg(db, msg_hash="6" * 32, peer=peer, content="", ts=base + 1)

    assert db.messages.count_duplicate_lxmf_messages_by_content() == 2
    deleted = db.messages.delete_duplicate_lxmf_messages_by_content()
    assert deleted == 2
    assert db.messages.count_lxmf_messages() == 4
    remaining = {
        r["hash"]
        for r in db.provider.fetchall("SELECT hash, content FROM lxmf_messages")
    }
    assert "1" * 32 in remaining
    assert "4" * 32 in remaining
    assert "2" * 32 not in remaining
    assert "3" * 32 not in remaining
    db.close_all()
    provider.close_all()


def test_duplicates_are_scoped_by_peer_and_direction(tmp_path):
    path = str(tmp_path / "d2.db")
    provider = DatabaseProvider(path)
    DatabaseSchema(provider).initialize()
    db = Database(path)
    peer_a = "b" * 32
    peer_b = "c" * 32
    _msg(db, msg_hash="1" * 32, peer=peer_a, content="same", is_incoming=1)
    _msg(db, msg_hash="2" * 32, peer=peer_b, content="same", is_incoming=1)
    _msg(db, msg_hash="3" * 32, peer=peer_a, content="same", is_incoming=0)
    assert db.messages.count_duplicate_lxmf_messages_by_content() == 0
    db.close_all()
    provider.close_all()
