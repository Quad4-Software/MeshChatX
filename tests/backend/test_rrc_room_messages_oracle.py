# SPDX-License-Identifier: 0BSD

"""Oracle tests for RRC room message pagination."""

import unittest
from unittest.mock import MagicMock

from meshchatx.src.backend.rrc.manager import RRCHub


class _Msg:
    def __init__(self, seq, text="x"):
        self.seq = seq
        self.text = text
        self.kind = "msg"
        self.room = "lobby"

    def to_dict(self):
        return {
            "seq": self.seq,
            "text": self.text,
            "kind": self.kind,
            "room": self.room,
        }


class TestRrcRoomMessagesOracle(unittest.TestCase):
    def _hub_with_messages(self, seqs):
        manager = MagicMock()
        manager.identity.hash = b"\x01" * 16
        manager.history_per_room_cap = 0
        manager.filter_loaded_history = False
        manager.ephemeral_notices = 0
        manager._ensure_history_dir = MagicMock()
        manager._history_path = MagicMock(return_value="/tmp/unused")
        manager._notify_messages = MagicMock()
        manager._on_welcome = MagicMock()
        manager.active_room_for = MagicMock(return_value=None)
        hub = RRCHub(manager, "aa" * 16, name="test")
        hub.messages["lobby"] = [_Msg(s) for s in seqs]
        return hub

    def test_before_seq_pages_are_non_overlapping_and_older(self):
        hub = self._hub_with_messages(list(range(1, 501)))
        cursor = None
        seen = set()
        for _ in range(10):
            page, has_more = hub.room_messages("lobby", limit=50, before_seq=cursor)
            ids = [row["seq"] for row in page]
            if not ids:
                break
            if cursor is not None:
                self.assertTrue(all(i < cursor for i in ids))
            overlap = seen.intersection(ids)
            self.assertFalse(overlap, f"duplicate seq across pages: {overlap}")
            seen.update(ids)
            cursor = min(ids)
            if not has_more:
                break
        self.assertGreaterEqual(len(seen), 400)

    def test_initial_page_returns_newest_limit_rows_oldest_first(self):
        hub = self._hub_with_messages(list(range(1, 201)))
        page, has_more = hub.room_messages("lobby", limit=50)
        self.assertTrue(has_more)
        seqs = [row["seq"] for row in page]
        self.assertEqual(seqs[0], 151)
        self.assertEqual(seqs[-1], 200)
        for i in range(1, len(seqs)):
            self.assertGreater(seqs[i], seqs[i - 1])


if __name__ == "__main__":
    unittest.main()
