# SPDX-License-Identifier: 0BSD

"""Oracles for conversation and announce list joins.

Contact OR-joins must not multiply rows. Announce COUNT must equal the
number of matching announce rows. Conversation list SQL must not GROUP BY
the summaries table (that blocks LIMIT from using latest_message_id).
"""

from __future__ import annotations

import secrets
import tempfile
import time
import unittest

from meshchatx.src.backend.announce_manager import AnnounceManager
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.message_handler import MessageHandler


def _reset_provider():
    if DatabaseProvider._instance is not None:
        DatabaseProvider._instance.close_all()
        DatabaseProvider._instance = None


def _message(peer_hash, i, *, content="hello"):
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
        "fields": "{}",
        "timestamp": time.time() - i,
        "rssi": -50,
        "snr": 5.0,
        "quality": 3,
        "is_spam": 0,
        "reply_to_hash": None,
    }


def _announce(dest, ident, aspect="lxmf.delivery"):
    return {
        "destination_hash": dest,
        "aspect": aspect,
        "identity_hash": ident,
        "identity_public_key": "pubkey_" + dest[:8],
        "app_data": "appdata",
        "rssi": -50,
        "snr": 5.0,
        "quality": 3,
    }


class TestQueryJoinPerf(unittest.TestCase):
    def setUp(self):
        _reset_provider()
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(f"{self.tmp.name}/database.db")
        self.db.initialize()
        self.handler = MessageHandler(self.db)
        self.announce_mgr = AnnounceManager(self.db)

    def tearDown(self):
        self.db.close()
        _reset_provider()
        self.tmp.cleanup()

    def test_announce_count_ignores_matching_contacts(self):
        dest = secrets.token_hex(16)
        ident = secrets.token_hex(16)
        self.db.announces.upsert_announce(_announce(dest, ident))
        self.db.contacts.add_contact(
            name="ByIdent",
            remote_identity_hash=ident,
            custom_image="img-a",
        )
        other_ident = secrets.token_hex(16)
        self.db.contacts.add_contact(
            name="ByLxmf",
            remote_identity_hash=other_ident,
            lxmf_address=dest,
            custom_image="img-b",
        )

        count = self.announce_mgr.get_filtered_announces_count(aspect="lxmf.delivery")
        self.assertEqual(count, 1)

        rows = self.announce_mgr.get_filtered_announces(
            aspect="lxmf.delivery",
            limit=50,
        )
        dests = [r["destination_hash"] for r in rows]
        self.assertEqual(dests.count(dest), 1)
        self.assertIn(rows[0].get("contact_image"), ("img-a", "img-b"))

    def test_announce_count_sql_does_not_join_contacts(self):
        captured = []
        real = self.db.provider.fetchone

        def wrap(query, params=None):
            captured.append(query)
            return real(query, params)

        self.db.provider.fetchone = wrap
        try:
            self.announce_mgr.get_filtered_announces_count(aspect="lxmf.delivery")
        finally:
            self.db.provider.fetchone = real
        self.assertEqual(len(captured), 1)
        sql = captured[0].lower()
        self.assertIn("count(*)", sql)
        self.assertNotIn("contacts", sql)

    def test_conversation_list_one_row_with_two_matching_contacts(self):
        peer = secrets.token_hex(16)
        self.db.messages.upsert_lxmf_message(_message(peer, 0, content="hi"))
        self.db.contacts.add_contact(
            name="IdentName",
            remote_identity_hash=peer,
        )
        self.db.contacts.add_contact(
            name="LxmfName",
            remote_identity_hash=secrets.token_hex(16),
            lxmf_address=peer,
        )

        rows = self.handler.get_conversations("local", limit=50)
        peers = [r["peer_hash"] for r in rows]
        self.assertEqual(peers.count(peer), 1)
        match = next(r for r in rows if r["peer_hash"] == peer)
        self.assertEqual(match["contact_name"], "IdentName")
        self.assertEqual(int(match["is_contact"]), 1)

    def test_conversation_list_sql_has_no_group_by(self):
        captured = []
        real = self.db.provider.fetchall

        def wrap(query, params=None):
            captured.append((query, params))
            return real(query, params)

        self.db.provider.fetchall = wrap
        try:
            self.handler.get_conversations("local", limit=50, offset=0)
        finally:
            self.db.provider.fetchall = real
        self.assertEqual(len(captured), 1)
        sql, params = captured[0]
        self.assertNotIn("GROUP BY", sql)
        self.assertIn("ORDER BY s.latest_message_id DESC", sql)

        plan_rows = real("EXPLAIN QUERY PLAN " + sql, params)
        plan = " ".join(str(r["detail"]) for r in plan_rows).lower()
        self.assertNotIn("group by", plan)
        self.assertTrue(
            "idx_lxmf_conversation_summaries_latest_id" in plan or "summaries" in plan,
            f"expected summaries index in plan, got: {plan}",
        )

    def test_related_announces_batch_one_in_query(self):
        ident_a = secrets.token_hex(16)
        ident_b = secrets.token_hex(16)
        self.db.announces.upsert_announce(
            _announce(secrets.token_hex(16), ident_a, "lxmf.delivery"),
        )
        self.db.announces.upsert_announce(
            _announce(secrets.token_hex(16), ident_a, "nomadnetwork.node"),
        )
        self.db.announces.upsert_announce(
            _announce(secrets.token_hex(16), ident_b, "lxmf.delivery"),
        )

        captured = []
        real = self.db.provider.fetchall

        def wrap(query, params=None):
            captured.append(query)
            return real(query, params)

        self.db.provider.fetchall = wrap
        try:
            rows = self.db.announces.get_announces_for_identity_hashes(
                [ident_a, ident_b],
                aspects=["lxmf.delivery", "nomadnetwork.node"],
            )
        finally:
            self.db.provider.fetchall = real
        self.assertEqual(len(captured), 1)
        self.assertIn("identity_hash IN", captured[0])
        self.assertEqual(len(rows), 3)

        index = self.db.announces.index_announces_by_identity_aspect(rows)
        self.assertIn((ident_a, "lxmf.delivery"), index)
        self.assertIn((ident_a, "nomadnetwork.node"), index)
        self.assertIn((ident_b, "lxmf.delivery"), index)

    def test_get_announces_limit_does_not_load_all_rows(self):
        ident = secrets.token_hex(16)
        for _ in range(8):
            self.db.announces.upsert_announce(
                _announce(secrets.token_hex(16), ident, "lxmf.propagation"),
            )
        page = self.db.announces.get_announces(aspect="lxmf.propagation", limit=3)
        self.assertEqual(len(page), 3)
        all_rows = self.db.announces.get_announces(aspect="lxmf.propagation")
        self.assertEqual(len(all_rows), 8)

    def test_identity_hash_lookup_is_equality_not_like(self):
        captured = []
        real = self.db.provider.fetchall

        def wrap(query, params=None):
            captured.append((query, params))
            return real(query, params)

        self.db.provider.fetchall = wrap
        try:
            self.db.announces.get_filtered_announces(
                aspect="lxmf.delivery",
                identity_hash="abc123",
                limit=1,
            )
        finally:
            self.db.provider.fetchall = real
        sql, params = captured[0]
        self.assertIn("identity_hash = ?", sql)
        self.assertNotIn("LIKE", sql)
        self.assertIn("abc123", params)

    def test_notification_viewed_map_is_one_query(self):
        peer_a = secrets.token_hex(16)
        peer_b = secrets.token_hex(16)
        now = time.time()
        self.db.messages.import_notification_viewed_state(
            [
                {
                    "destination_hash": peer_a,
                    "last_viewed_at": "2030-01-01T00:00:00+00:00",
                },
            ],
        )
        captured = []
        real = self.db.provider.fetchall

        def wrap(query, params=None):
            captured.append(query)
            return real(query, params)

        self.db.provider.fetchall = wrap
        try:
            viewed = self.db.messages.get_notification_last_viewed_at_map(
                [peer_a, peer_b, peer_a],
            )
        finally:
            self.db.provider.fetchall = real
        self.assertEqual(len(captured), 1)
        self.assertIn("IN (?, ?)", captured[0])
        self.assertTrue(
            self.db.messages.notification_viewed_covers(
                viewed.get(peer_a),
                now,
            ),
        )
        self.assertFalse(
            self.db.messages.notification_viewed_covers(
                viewed.get(peer_b),
                now,
            ),
        )
        self.assertTrue(self.db.messages.is_notification_viewed(peer_a, now))
        self.assertFalse(self.db.messages.is_notification_viewed(peer_b, now))

    def test_destination_hash_bulk_query_does_not_duplicate(self):
        dest = secrets.token_hex(16)
        ident = secrets.token_hex(16)
        self.db.announces.upsert_announce(_announce(dest, ident))
        self.db.contacts.add_contact(name="A", remote_identity_hash=ident)
        self.db.contacts.add_contact(
            name="B",
            remote_identity_hash=secrets.token_hex(16),
            lxmf_address=dest,
        )
        rows = self.announce_mgr.get_announces_for_destination_hashes(
            [dest],
            aspects=["lxmf.delivery"],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["destination_hash"], dest)


if __name__ == "__main__":
    unittest.main()
