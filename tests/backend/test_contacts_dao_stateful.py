# SPDX-License-Identifier: 0BSD
"""Stateful model test for the contacts DAO."""

from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    invariant,
    rule,
)


class ContactsDaoMachine(RuleBasedStateMachine):
    hashes = Bundle("hashes")

    def __init__(self):
        super().__init__()
        import os
        import tempfile

        from meshchatx.src.backend.database import Database
        from meshchatx.src.backend.database.provider import DatabaseProvider
        from meshchatx.src.backend.database.schema import DatabaseSchema

        self.tmp = os.path.join(tempfile.mkdtemp(prefix="ct-sm-"), "t.db")
        self.provider = DatabaseProvider(self.tmp)
        DatabaseSchema(self.provider).initialize()
        self.db = Database(self.tmp)
        self.seq = 0
        self.model = {}  # remote_identity_hash -> dict(id, name, lxmf, lxst)

    def teardown(self):
        self.db.close_all()
        self.provider.close_all()

    @rule(target=hashes, h=st.from_regex(r"[0-9a-f]{16,64}", fullmatch=True))
    def make_hash(self, h):
        return h

    @rule(
        h=hashes,
        name=st.text(max_size=40),
        lxmf=st.one_of(st.none(), st.from_regex(r"[0-9a-f]{32}", fullmatch=True)),
    )
    def upsert(self, h, name, lxmf):
        self.db.contacts.add_contact(name, h, lxmf_address=lxmf)
        row = self.db.contacts.get_contact_by_identity_hash(h)
        m = self.model.get(h)
        # DAO upsert: name overwritten, lxmf kept when incoming is None.
        self.model[h] = {
            "id": m["id"] if m else row["id"],
            "name": name,
            "lxmf": lxmf if lxmf is not None else (m["lxmf"] if m else None),
        }

    @rule(h=hashes)
    def delete(self, h):
        m = self.model.pop(h, None)
        if m is not None:
            self.db.contacts.delete_contact(m["id"])
        assert self.db.contacts.get_contact_by_identity_hash(h) is None

    @rule(name=st.text("ab", min_size=1, max_size=3))
    def check_search(self, name):
        expected = [h for h, m in self.model.items() if name in m["name"]]
        got = self.db.contacts.get_contacts(search=name, limit=1000)
        got_hashes = {r["remote_identity_hash"] for r in got}
        for h in expected:
            assert h in got_hashes
        assert self.db.contacts.get_contacts_count(search=name) == len(got)

    @rule()
    def check_pagination_union(self):
        page1 = self.db.contacts.get_contacts(limit=3, offset=0)
        page2 = self.db.contacts.get_contacts(limit=1000, offset=3)
        all_rows = self.db.contacts.get_contacts(limit=10000, offset=0)
        assert page1 + page2 == all_rows
        # Ordered by name asc, no duplicates.
        ids = [r["id"] for r in all_rows]
        assert len(ids) == len(set(ids))
        assert all_rows == sorted(all_rows, key=lambda r: r["name"])

    @invariant()
    def row_count_matches(self):
        assert self.db.contacts.get_contacts_count() == len(self.model)

    @invariant()
    def fields_match_model(self):
        for h, m in self.model.items():
            row = self.db.contacts.get_contact_by_identity_hash(h)
            assert row is not None
            assert row["name"] == m["name"]
            assert row["lxmf_address"] == m["lxmf"]


TestContactsStateful = ContactsDaoMachine.TestCase
TestContactsStateful.settings = settings(
    max_examples=30,
    stateful_step_count=40,
    derandomize=True,
    deadline=None,
)
