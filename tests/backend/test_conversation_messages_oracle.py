# SPDX-License-Identifier: 0BSD

"""Oracle tests for paginated conversation message loads."""

import secrets
import tempfile
import time
import unittest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.message_handler import MessageHandler


def _message(peer_hash, i, *, fields="{}"):
    return {
        "hash": secrets.token_hex(16),
        "source_hash": peer_hash,
        "destination_hash": "localhashlocalhashlocalhashlo12",
        "peer_hash": peer_hash,
        "state": "delivered",
        "progress": 1.0,
        "is_incoming": 1,
        "method": "direct",
        "delivery_attempts": 1,
        "next_delivery_attempt_at": None,
        "title": f"t{i}",
        "content": f"body {i}",
        "fields": fields,
        "timestamp": time.time() - i,
        "rssi": -50,
        "snr": 5.0,
        "quality": 3,
        "is_spam": 0,
        "reply_to_hash": None,
    }


class TestConversationMessagesOracle(unittest.TestCase):
    def setUp(self):
        from meshchatx.src.backend.database.provider import DatabaseProvider

        if DatabaseProvider._instance is not None:
            DatabaseProvider._instance.close_all()
            DatabaseProvider._instance = None
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(f"{self.tmp.name}/database.db")
        self.db.initialize()
        self.handler = MessageHandler(self.db)
        self.peer = secrets.token_hex(16)
        for i in range(240):
            self.db.messages.upsert_lxmf_message(_message(self.peer, i))

    def tearDown(self):
        from meshchatx.src.backend.database.provider import DatabaseProvider

        self.db.close()
        if DatabaseProvider._instance is not None:
            DatabaseProvider._instance.close_all()
            DatabaseProvider._instance = None
        self.tmp.cleanup()

    def test_before_id_pages_are_strictly_older_and_non_overlapping(self):
        page_size = 50
        cursor = None
        seen_ids = set()
        pages = 0
        while pages < 10:
            rows = self.handler.get_conversation_messages(
                "local",
                self.peer,
                limit=page_size,
                before_id=cursor,
            )
            if not rows:
                break
            ids = [row["id"] for row in rows]
            if cursor is not None:
                self.assertTrue(
                    all(i < cursor for i in ids),
                    "page must be strictly older than cursor",
                )
            overlap = seen_ids.intersection(ids)
            self.assertFalse(overlap, f"duplicate ids across pages: {overlap}")
            seen_ids.update(ids)
            cursor = min(ids)
            pages += 1
            if len(rows) < page_size:
                break
        self.assertGreaterEqual(len(seen_ids), 200)

    def test_conversation_rows_never_include_oversized_fields_blob(self):
        peer = secrets.token_hex(16)
        big = "Z" * 100_000
        self.db.messages.upsert_lxmf_message(
            _message(
                peer,
                0,
                fields='{"image":{"image_type":"png","image_bytes":"%s"}}' % big,
            ),
        )
        rows = self.handler.get_conversation_messages("local", peer, limit=5)
        self.assertEqual(len(rows), 1)
        fields = rows[0]["fields"] or ""
        self.assertLess(len(fields), 20_000)

    def test_negative_limit_clamps_to_zero_rows(self):
        rows = self.handler.get_conversation_messages(
            "local",
            self.peer,
            limit=-1,
        )
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
