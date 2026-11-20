# SPDX-License-Identifier: 0BSD
"""Stateful model test for the lxmf_messages DAO."""

import pytest
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)

PEERS = ("peer-a", "peer-b")


class MessagesDaoMachine(RuleBasedStateMachine):
    hashes = Bundle("hashes")

    def __init__(self):
        super().__init__()
        import os
        import tempfile

        from meshchatx.src.backend.database import Database
        from meshchatx.src.backend.database.provider import DatabaseProvider
        from meshchatx.src.backend.database.schema import DatabaseSchema

        self.tmp = os.path.join(tempfile.mkdtemp(prefix="msg-sm-"), "t.db")
        self.provider = DatabaseProvider(self.tmp)
        DatabaseSchema(self.provider).initialize()
        self.db = Database(self.tmp)
        self.seq = 0
        self.model = {}  # hash -> {peer, ts, content, seq}
        self.deleted = set()

    def teardown(self):
        self.db.close_all()
        self.provider.close_all()
        super().teardown()

    @initialize(target=hashes, num=st.integers(0, 9))
    def seed_hash(self, num):
        return f"h{num:02d}".ljust(64, "0")

    @rule(
        h=hashes,
        peer=st.sampled_from(PEERS),
        ts=st.floats(1_600_000_000, 1_800_000_000, allow_nan=False),
        body=st.text(max_size=40),
    )
    def upsert(self, h, peer, ts, body):
        self.seq += 1
        self.db.messages.upsert_lxmf_message(
            {
                "hash": h,
                "source_hash": peer,
                "destination_hash": "local",
                "peer_hash": peer,
                "state": "delivered",
                "is_incoming": 1,
                "method": "direct",
                "title": "",
                "content": body,
                "timestamp": ts,
            }
        )
        # Blank content never overwrites a stored value
        # (_LXMF_KEEP_IF_INCOMING_BLANK), and a deleted row keeps nothing.
        prev = self.model.get(h) if h not in self.deleted else None
        content = body if body != "" else (prev["content"] if prev else "")
        self.model[h] = {"peer": peer, "ts": ts, "content": content, "seq": self.seq}
        self.deleted.discard(h)

    @rule(h=hashes)
    def delete(self, h):
        self.db.messages.delete_lxmf_message_by_hash(h)
        self.deleted.add(h)

    @invariant()
    def count_matches(self):
        live = len(set(self.model) - self.deleted)
        assert self.db.messages.count_lxmf_messages() == live

    @invariant()
    def conversation_order_and_membership(self):
        for peer in PEERS:
            rows = self.db.messages.get_conversation_messages(peer)
            got = [r["hash"] for r in rows]
            want = {
                h
                for h, m in self.model.items()
                if m["peer"] == peer and h not in self.deleted
            }
            assert set(got) == want
            # ordered by timestamp DESC (id DESC tiebreak, we cannot predict
            # rowid for re-upserts, so check ts is non-increasing).
            ts = [r["timestamp"] for r in rows]
            assert ts == sorted(ts, reverse=True)

    @invariant()
    def upsert_dedupes_by_hash(self):
        rows = self.db.messages.get_all_lxmf_messages()
        hashes = [r["hash"] for r in rows]
        assert len(hashes) == len(set(hashes)), "duplicate hash rows"
        for r in rows:
            h = r["hash"]
            assert h in self.model and h not in self.deleted
            # content column reflects the latest upsert
            assert r["content"] == self.model[h]["content"]


@settings(derandomize=True, max_examples=30, stateful_step_count=30, deadline=None)
class BoundedMessagesDaoMachine(MessagesDaoMachine):
    pass


@pytest.mark.filterwarnings("ignore::ResourceWarning")
class TestMessagesDaoMachine(BoundedMessagesDaoMachine.TestCase):
    pass
