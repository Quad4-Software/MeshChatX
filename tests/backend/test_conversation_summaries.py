# SPDX-License-Identifier: 0BSD

"""Unit and integration tests for lxmf_conversation_summaries."""

from __future__ import annotations

import secrets
import tempfile
import time
import unittest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.message_handler import MessageHandler


def _message(
    peer_hash, i, *, state="delivered", content="hello", title=None, is_incoming=1
):
    return {
        "hash": secrets.token_hex(16),
        "source_hash": peer_hash if is_incoming else "localhashlocalhashlocalhashlo12",
        "destination_hash": "localhashlocalhashlocalhashlo12"
        if is_incoming
        else peer_hash,
        "peer_hash": peer_hash,
        "state": state,
        "progress": 1.0,
        "is_incoming": is_incoming,
        "method": "direct",
        "delivery_attempts": 1,
        "next_delivery_attempt_at": None,
        "title": title if title is not None else f"t{i}",
        "content": content,
        "fields": "{}",
        "timestamp": time.time() - i,
        "rssi": -50,
        "snr": 5.0,
        "quality": 3,
        "is_spam": 0,
        "reply_to_hash": None,
    }


class TestConversationSummaries(unittest.TestCase):
    def setUp(self):
        if DatabaseProvider._instance is not None:
            DatabaseProvider._instance.close_all()
            DatabaseProvider._instance = None
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(f"{self.tmp.name}/database.db")
        self.db.initialize()
        self.handler = MessageHandler(self.db)

    def tearDown(self):
        self.db.close()
        if DatabaseProvider._instance is not None:
            DatabaseProvider._instance.close_all()
            DatabaseProvider._instance = None
        self.tmp.cleanup()

    def test_schema_creates_summaries_table(self):
        row = self.db.provider.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='lxmf_conversation_summaries'",
        )
        self.assertIsNotNone(row)

    def test_upsert_creates_and_updates_summary(self):
        peer = secrets.token_hex(16)
        self.db.messages.upsert_lxmf_message(_message(peer, 2, content="old"))
        self.db.messages.upsert_lxmf_message(_message(peer, 1, content="new"))
        summary = self.db.provider.fetchone(
            "SELECT content_preview, latest_message_id FROM lxmf_conversation_summaries "
            "WHERE peer_hash = ?",
            (peer,),
        )
        self.assertEqual(summary["content_preview"], "new")
        latest = self.db.provider.fetchone(
            "SELECT MAX(id) AS max_id FROM lxmf_messages WHERE peer_hash = ?",
            (peer,),
        )
        self.assertEqual(summary["latest_message_id"], latest["max_id"])

    def test_failed_state_updates_failed_count(self):
        peer = secrets.token_hex(16)
        first = _message(peer, 2, state="failed")
        self.db.messages.upsert_lxmf_message(first)
        second = _message(peer, 1, state="delivered")
        self.db.messages.upsert_lxmf_message(second)
        summary = self.db.provider.fetchone(
            "SELECT failed_count, state FROM lxmf_conversation_summaries WHERE peer_hash = ?",
            (peer,),
        )
        self.assertEqual(summary["failed_count"], 1)
        self.assertEqual(summary["state"], "delivered")

        self.db.messages.update_lxmf_message_state(
            second["hash"],
            "failed",
            0.0,
            2,
            None,
        )
        summary = self.db.provider.fetchone(
            "SELECT failed_count, state FROM lxmf_conversation_summaries WHERE peer_hash = ?",
            (peer,),
        )
        self.assertEqual(summary["failed_count"], 2)
        self.assertEqual(summary["state"], "failed")

    def test_delete_last_message_removes_summary(self):
        peer = secrets.token_hex(16)
        msg = _message(peer, 0)
        self.db.messages.upsert_lxmf_message(msg)
        self.db.messages.delete_lxmf_message_by_hash(msg["hash"])
        summary = self.db.provider.fetchone(
            "SELECT 1 AS ok FROM lxmf_conversation_summaries WHERE peer_hash = ?",
            (peer,),
        )
        self.assertIsNone(summary)

    def test_delete_one_of_many_keeps_previous_latest(self):
        peer = secrets.token_hex(16)
        older = _message(peer, 2, content="older")
        newer = _message(peer, 1, content="newer")
        self.db.messages.upsert_lxmf_message(older)
        self.db.messages.upsert_lxmf_message(newer)
        self.db.messages.delete_lxmf_message_by_hash(newer["hash"])
        summary = self.db.provider.fetchone(
            "SELECT content_preview FROM lxmf_conversation_summaries WHERE peer_hash = ?",
            (peer,),
        )
        self.assertEqual(summary["content_preview"], "older")

    def test_delete_conversation_removes_summary(self):
        peer = secrets.token_hex(16)
        self.db.messages.upsert_lxmf_message(_message(peer, 0))
        self.handler.delete_conversation("local", peer)
        summary = self.db.provider.fetchone(
            "SELECT 1 AS ok FROM lxmf_conversation_summaries WHERE peer_hash = ?",
            (peer,),
        )
        self.assertIsNone(summary)

    def test_rebuild_after_empty_summary_table(self):
        peer = secrets.token_hex(16)
        self.db.messages.upsert_lxmf_message(_message(peer, 0, content="kept"))
        self.db.provider.execute("DELETE FROM lxmf_conversation_summaries")
        self.db.messages.refresh_conversation_summary(peer)
        summary = self.db.provider.fetchone(
            "SELECT content_preview FROM lxmf_conversation_summaries WHERE peer_hash = ?",
            (peer,),
        )
        self.assertEqual(summary["content_preview"], "kept")

    def test_get_conversations_reads_summaries_without_fields(self):
        peer_a = secrets.token_hex(16)
        peer_b = secrets.token_hex(16)
        self.db.messages.upsert_lxmf_message(_message(peer_a, 1, content="alpha"))
        self.db.messages.upsert_lxmf_message(_message(peer_b, 0, content="beta"))
        rows = self.handler.get_conversations("local", limit=10)
        self.assertEqual(len(rows), 2)
        for row in rows:
            row = dict(row)
            self.assertNotIn("fields", row)
            self.assertNotIn("contact_image", row)
            self.assertIn("has_contact_image", row)
            self.assertLessEqual(len(row.get("content") or ""), 240)

    def test_pagination_order_stable(self):
        peers = [secrets.token_hex(16) for _ in range(5)]
        for i, peer in enumerate(peers):
            self.db.messages.upsert_lxmf_message(
                _message(peer, 10 - i, content=f"p{i}")
            )
        page1 = [
            dict(r)["peer_hash"]
            for r in self.handler.get_conversations("local", limit=2, offset=0)
        ]
        page2 = [
            dict(r)["peer_hash"]
            for r in self.handler.get_conversations("local", limit=2, offset=2)
        ]
        self.assertEqual(len(page1), 2)
        self.assertEqual(len(page2), 2)
        self.assertEqual(len(set(page1) & set(page2)), 0)

    def test_search_matches_older_message(self):
        peer = secrets.token_hex(16)
        self.db.messages.upsert_lxmf_message(
            _message(peer, 2, content="needle in a haystack", title="old"),
        )
        self.db.messages.upsert_lxmf_message(
            _message(peer, 1, content="latest only", title="new"),
        )
        rows = self.handler.get_conversations("local", search="needle")
        hashes = {dict(r)["peer_hash"] for r in rows}
        self.assertIn(peer, hashes)

    def test_filter_failed_and_unread(self):
        failed_peer = secrets.token_hex(16)
        unread_peer = secrets.token_hex(16)
        self.db.messages.upsert_lxmf_message(
            _message(failed_peer, 0, state="failed", content="boom"),
        )
        self.db.messages.upsert_lxmf_message(
            _message(unread_peer, 0, content="hi", is_incoming=1),
        )
        failed_rows = self.handler.get_conversations("local", filter_failed=True)
        self.assertEqual({dict(r)["peer_hash"] for r in failed_rows}, {failed_peer})
        unread_rows = self.handler.get_conversations("local", filter_unread=True)
        self.assertIn(unread_peer, {dict(r)["peer_hash"] for r in unread_rows})

    def test_omit_limit_clamped_in_handler(self):
        peer = secrets.token_hex(16)
        self.db.messages.upsert_lxmf_message(_message(peer, 0))
        rows = self.handler.get_conversations("local", limit=None)
        self.assertEqual(len(rows), 1)
        rows_capped = self.handler.get_conversations("local", limit=99999)
        self.assertEqual(len(rows_capped), 1)
