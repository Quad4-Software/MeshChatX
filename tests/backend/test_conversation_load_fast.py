# SPDX-License-Identifier: 0BSD

"""Regression tests for fast conversation list and heavy thread loads."""

import json
import secrets
import tempfile
import time
import unittest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.lxmf_utils import convert_db_lxmf_message_to_dict
from meshchatx.src.backend.message_handler import MessageHandler


def _message(peer_hash, i, *, fields="{}", content="hello"):
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
        "content": content,
        "fields": fields,
        "timestamp": time.time() - i,
        "rssi": -50,
        "snr": 5.0,
        "quality": 3,
        "is_spam": 0,
        "reply_to_hash": None,
    }


class TestConversationLoadFast(unittest.TestCase):
    def setUp(self):
        from meshchatx.src.backend.database.provider import DatabaseProvider

        if DatabaseProvider._instance is not None:
            DatabaseProvider._instance.close_all()
            DatabaseProvider._instance = None
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(f"{self.tmp.name}/database.db")
        self.db.initialize()
        self.handler = MessageHandler(self.db)

    def tearDown(self):
        from meshchatx.src.backend.database.provider import DatabaseProvider

        self.db.close()
        if DatabaseProvider._instance is not None:
            DatabaseProvider._instance.close_all()
            DatabaseProvider._instance = None
        self.tmp.cleanup()

    def test_upsert_stores_fields_meta_without_bytes(self):
        peer = secrets.token_hex(16)
        big_b64 = "A" * 80000
        fields = {
            "image": {
                "image_type": "png",
                "image_bytes": big_b64,
            },
        }
        self.db.messages.upsert_lxmf_message(_message(peer, 0, fields=fields))

        row = self.db.provider.fetchone(
            "SELECT fields, fields_meta, has_image, has_audio, has_files "
            "FROM lxmf_messages WHERE peer_hash = ?",
            (peer,),
        )
        self.assertEqual(row["has_image"], 1)
        self.assertEqual(row["has_audio"], 0)
        meta = json.loads(row["fields_meta"])
        self.assertIsNone(meta["image"]["image_bytes"])
        self.assertEqual(meta["image"]["image_type"], "png")
        self.assertGreater(meta["image"]["image_size"], 0)
        # Full blob remains available for the attachment endpoint.
        self.assertIn(big_b64, row["fields"])

    def test_conversation_messages_do_not_return_huge_fields_blob(self):
        peer = secrets.token_hex(16)
        big_b64 = "B" * 120000
        fields = {
            "image": {
                "image_type": "jpeg",
                "image_bytes": big_b64,
            },
        }
        for i in range(40):
            self.db.messages.upsert_lxmf_message(
                _message(peer, i, fields=fields if i % 2 == 0 else "{}"),
            )

        rows = self.handler.get_conversation_messages("local", peer, limit=30)
        self.assertEqual(len(rows), 30)
        for row in rows:
            row = dict(row)
            fields_value = row.get("fields")
            if fields_value:
                self.assertLess(
                    len(fields_value),
                    20000,
                    "conversation message query returned oversized fields",
                )
            converted = convert_db_lxmf_message_to_dict(row)
            if row.get("has_image"):
                self.assertIn("image", converted["fields"])
                self.assertIsNone(converted["fields"]["image"]["image_bytes"])

    def test_conversations_list_uses_flags_not_fields_column(self):
        peer = secrets.token_hex(16)
        big_b64 = "C" * 90000
        self.db.messages.upsert_lxmf_message(
            _message(
                peer,
                0,
                fields={
                    "image": {"image_type": "png", "image_bytes": big_b64},
                },
                content="",
            ),
        )
        rows = self.handler.get_conversations("local", limit=10)
        self.assertGreaterEqual(len(rows), 1)
        row = dict(rows[0])
        self.assertEqual(row["peer_hash"], peer)
        self.assertEqual(row["has_image"], 1)
        self.assertEqual(row["has_attachments"], 1)
        self.assertNotIn("fields", row.keys())


if __name__ == "__main__":
    unittest.main()
