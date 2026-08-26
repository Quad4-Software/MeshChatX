# SPDX-License-Identifier: 0BSD

"""Paginated conversation message load performance."""

import secrets
import tempfile
import time
import unittest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.message_handler import MessageHandler


def _message(peer_hash, i):
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
        "fields": "{}",
        "timestamp": time.time() - i,
        "rssi": -50,
        "snr": 5.0,
        "quality": 3,
        "is_spam": 0,
        "reply_to_hash": None,
    }


class TestConversationPaginatedLoadPerf(unittest.TestCase):
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
        for i in range(5000):
            self.db.messages.upsert_lxmf_message(_message(self.peer, i))

    def tearDown(self):
        from meshchatx.src.backend.database.provider import DatabaseProvider

        self.db.close()
        if DatabaseProvider._instance is not None:
            DatabaseProvider._instance.close_all()
            DatabaseProvider._instance = None
        self.tmp.cleanup()

    def test_before_id_pages_stay_fast_on_large_thread(self):
        rows = self.handler.get_conversation_messages("local", self.peer, limit=50)
        self.assertEqual(len(rows), 50)
        oldest_id = min(row["id"] for row in rows)

        durations = []
        cursor = oldest_id
        for _ in range(20):
            t0 = time.perf_counter()
            page = self.handler.get_conversation_messages(
                "local",
                self.peer,
                limit=50,
                before_id=cursor,
            )
            durations.append((time.perf_counter() - t0) * 1000)
            self.assertGreater(len(page), 0)
            cursor = min(row["id"] for row in page)

        p95 = sorted(durations)[int(len(durations) * 0.95) - 1]
        self.assertLess(p95, 80, f"before_id page p95 {p95:.1f}ms exceeds 80ms")


if __name__ == "__main__":
    unittest.main()
