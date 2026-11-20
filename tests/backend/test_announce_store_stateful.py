# SPDX-License-Identifier: 0BSD
"""Stateful model test: announce trim never deletes protected rows.

At most max_rows unprotected rows per aspect survive each trim.
"""

import pytest
from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)

pytestmark = pytest.mark.filterwarnings("ignore::ResourceWarning")

ASPECTS = ("lxmf.delivery", "nomadnetwork.node")


class AnnounceStoreMachine(RuleBasedStateMachine):
    dests = Bundle("dests")

    def __init__(self):
        super().__init__()
        import os
        import tempfile

        from meshchatx.src.backend.database import Database
        from meshchatx.src.backend.database.provider import DatabaseProvider
        from meshchatx.src.backend.database.schema import DatabaseSchema

        temp_db = os.path.join(tempfile.mkdtemp(prefix="announce-sm-"), "test.db")
        self.provider = DatabaseProvider(temp_db)
        DatabaseSchema(self.provider).initialize()
        self.db = Database(temp_db)
        self.seq = 0
        # model: dest -> {"aspect": a, "identity": ihash, "seq": n, "count": c}
        self.model = {}
        self.favourites = set()
        self.contacts = set()  # identity hashes protected via contacts table
        self.trimmed = {}  # aspect -> last max_rows used

    def teardown(self):
        self.db.close_all()
        self.provider.close_all()
        super().teardown()

    @initialize(target=dests, num=st.integers(0, 19))
    def seed_dest(self, num):
        return f"dest{num:02d}".ljust(40, "0")

    @rule(dest=dests, aspect=st.sampled_from(ASPECTS))
    def upsert(self, dest, aspect):
        ihash = f"ih-{dest[-4:]}"
        self.db.announces.upsert_announce(
            {
                "destination_hash": dest,
                "aspect": aspect,
                "identity_hash": ihash,
                "identity_public_key": "pk",
                "app_data": "x",
            }
        )
        self.seq += 1
        m = self.model.get(dest)
        if m is None:
            self.model[dest] = {
                "aspect": aspect,
                "identity": ihash,
                "seq": self.seq,
                "count": 1,
            }
        else:
            m["aspect"] = aspect
            m["count"] += 1

    @rule(dest=dests)
    def favourite(self, dest):
        self.db.announces.upsert_favourite(dest, f"name-{dest}", "nomadnetwork.node")
        self.favourites.add(dest)

    @rule(dest=dests)
    def unfavourite(self, dest):
        self.db.announces.delete_favourite(dest)
        self.favourites.discard(dest)

    @rule(dest=dests)
    def contact(self, dest):
        # Contact protects the announce via lxmf_address == destination_hash.
        ihash = f"ih-{dest[-4:]}"
        self.db.contacts.add_contact(f"c-{dest}", ihash, lxmf_address=dest)
        self.contacts.add(dest)

    @rule(dest=dests)
    def uncontact(self, dest):
        # Look up the row id: delete_contact keys on contacts.id.
        rows = self.db.contacts.get_contacts(search=f"c-{dest}")
        for r in rows:
            if r["name"] == f"c-{dest}":
                self.db.contacts.delete_contact(r["id"])
        self.contacts.discard(dest)

    @rule(aspect=st.sampled_from(ASPECTS), max_rows=st.integers(1, 6))
    def trim(self, aspect, max_rows):
        self.db.announces.trim_announces_for_aspect(aspect, max_rows)
        self.trimmed[aspect] = max_rows

    @invariant()
    def protected_never_trimmed(self):
        rows = self.db.announces.get_announces()
        have = {r["destination_hash"] for r in rows}
        for dest in self.favourites | self.contacts:
            if dest in self.model:
                assert dest in have, f"protected announce {dest} was trimmed"

    @invariant()
    def trim_bound_and_newest_kept(self):
        for aspect, max_rows in self.trimmed.items():
            unprotected = [
                d
                for d, m in self.model.items()
                if m["aspect"] == aspect
                and d not in self.favourites
                and d not in self.contacts
            ]
            rows = {
                r["destination_hash"]
                for r in self.db.announces.get_announces(aspect=aspect)
            }
            kept = [d for d in unprotected if d in rows]
            assert len(kept) <= max_rows, (
                f"{len(kept)} unprotected {aspect} rows after trim to {max_rows}"
            )
            # Kept rows are a suffix of the unprotected inserts by seq order
            # only when timestamps order exactly. Assert the count bound and
            # that every missing unprotected row is no newer than every kept one.
            missing = [d for d in unprotected if d not in rows]
            if missing and kept:
                oldest_kept = min(self.model[d]["seq"] for d in kept)
                newest_missing = max(self.model[d]["seq"] for d in missing)
                assert newest_missing <= oldest_kept

    @invariant()
    def rows_match_model(self):
        rows = self.db.announces.get_announces()
        have = {r["destination_hash"]: r for r in rows}
        # No phantom rows: every stored announce came from an upsert.
        assert set(have) <= set(self.model)
        # announce_count mirrors the model's upsert count.
        for dest, r in have.items():
            assert r["announce_count"] == self.model[dest]["count"]
            assert r["aspect"] == self.model[dest]["aspect"]


from hypothesis import settings


@settings(derandomize=True, max_examples=30, stateful_step_count=30, deadline=None)
class BoundedAnnounceStoreMachine(AnnounceStoreMachine):
    pass


@pytest.mark.filterwarnings("ignore::ResourceWarning")
class TestAnnounceStoreMachine(BoundedAnnounceStoreMachine.TestCase):
    pass
