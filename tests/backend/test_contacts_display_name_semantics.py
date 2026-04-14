"""Contacts and announces: display names, custom labels, and announce app_data upserts.

Covers announce upsert semantics when app_data is NULL (COALESCE), contacts DAO
conflict behaviour, custom display name lifecycle, and related edge cases.
"""

import base64
import os
import tempfile

import pytest

from meshchatx.src.backend.database.announces import AnnounceDAO
from meshchatx.src.backend.database.contacts import ContactsDAO
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema
from meshchatx.src.backend.meshchat_utils import parse_lxmf_display_name

try:
    import RNS.vendor.umsgpack as msgpack
except ImportError:
    msgpack = None


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def provider(temp_db):
    p = DatabaseProvider(temp_db)
    schema = DatabaseSchema(p)
    schema.initialize()
    yield p
    p.close()


@pytest.fixture
def announce_dao(provider):
    return AnnounceDAO(provider)


@pytest.fixture
def contacts_dao(provider):
    return ContactsDAO(provider)


def _make_app_data_b64(name: str) -> str:
    if msgpack is None:
        return base64.b64encode(name.encode()).decode()
    packed = msgpack.packb([name.encode(), None, None])
    return base64.b64encode(packed).decode()


def _base_announce(dest="d" * 32, app_data="some_data"):
    return {
        "destination_hash": dest,
        "aspect": "lxmf.delivery",
        "identity_hash": "i" * 32,
        "identity_public_key": "k" * 32,
        "app_data": app_data,
        "rssi": -60,
        "snr": 8,
        "quality": 0.9,
    }


# ---------------------------------------------------------------------------
# Announce upsert when app_data is NULL (COALESCE)
# ---------------------------------------------------------------------------


class TestAnnounceUpsertNullAppDataCoalesce:
    """Upsert with app_data=None must not clear an existing app_data value."""

    def test_null_app_data_preserves_existing(self, announce_dao):
        announce_dao.upsert_announce(_base_announce(app_data="original_name"))
        row = announce_dao.get_announce_by_hash("d" * 32)
        assert row["app_data"] == "original_name"

        announce_dao.upsert_announce(_base_announce(app_data=None))
        row = announce_dao.get_announce_by_hash("d" * 32)
        assert row["app_data"] == "original_name"

    def test_new_app_data_overwrites_existing(self, announce_dao):
        announce_dao.upsert_announce(_base_announce(app_data="old_name"))
        announce_dao.upsert_announce(_base_announce(app_data="new_name"))
        row = announce_dao.get_announce_by_hash("d" * 32)
        assert row["app_data"] == "new_name"

    def test_first_insert_with_null_app_data(self, announce_dao):
        announce_dao.upsert_announce(_base_announce(app_data=None))
        row = announce_dao.get_announce_by_hash("d" * 32)
        assert row["app_data"] is None

    def test_first_null_then_real_then_null_again(self, announce_dao):
        dest = "a" * 32
        announce_dao.upsert_announce(_base_announce(dest=dest, app_data=None))
        row = announce_dao.get_announce_by_hash(dest)
        assert row["app_data"] is None

        announce_dao.upsert_announce(_base_announce(dest=dest, app_data="real_name"))
        row = announce_dao.get_announce_by_hash(dest)
        assert row["app_data"] == "real_name"

        announce_dao.upsert_announce(_base_announce(dest=dest, app_data=None))
        row = announce_dao.get_announce_by_hash(dest)
        assert row["app_data"] == "real_name"

    def test_multiple_null_upserts_no_degradation(self, announce_dao):
        dest = "b" * 32
        announce_dao.upsert_announce(_base_announce(dest=dest, app_data="stable_name"))
        for _ in range(10):
            announce_dao.upsert_announce(_base_announce(dest=dest, app_data=None))
        row = announce_dao.get_announce_by_hash(dest)
        assert row["app_data"] == "stable_name"

    def test_other_fields_still_update_on_null_app_data(self, announce_dao):
        dest = "c" * 32
        announce_dao.upsert_announce(
            {**_base_announce(dest=dest, app_data="keep_me"), "rssi": -50},
        )
        announce_dao.upsert_announce(
            {**_base_announce(dest=dest, app_data=None), "rssi": -90},
        )
        row = announce_dao.get_announce_by_hash(dest)
        assert row["app_data"] == "keep_me"
        assert row["rssi"] == -90

    def test_empty_string_app_data_is_not_null(self, announce_dao):
        dest = "e" * 32
        announce_dao.upsert_announce(_base_announce(dest=dest, app_data="good_name"))
        announce_dao.upsert_announce(_base_announce(dest=dest, app_data=""))
        row = announce_dao.get_announce_by_hash(dest)
        assert row["app_data"] == ""


# ---------------------------------------------------------------------------
# Custom display name lifecycle
# ---------------------------------------------------------------------------


class TestCustomDisplayNameLifecycle:
    def test_set_and_get(self, announce_dao):
        announce_dao.upsert_custom_display_name("dest1", "Alice")
        assert announce_dao.get_custom_display_name("dest1") == "Alice"

    def test_update_overwrites(self, announce_dao):
        announce_dao.upsert_custom_display_name("dest1", "Alice")
        announce_dao.upsert_custom_display_name("dest1", "Bob")
        assert announce_dao.get_custom_display_name("dest1") == "Bob"

    def test_delete_removes(self, announce_dao):
        announce_dao.upsert_custom_display_name("dest1", "Alice")
        announce_dao.delete_custom_display_name("dest1")
        assert announce_dao.get_custom_display_name("dest1") is None

    def test_get_nonexistent_returns_none(self, announce_dao):
        assert announce_dao.get_custom_display_name("nonexistent") is None

    def test_delete_nonexistent_is_noop(self, announce_dao):
        announce_dao.delete_custom_display_name("nonexistent")

    def test_set_after_delete(self, announce_dao):
        announce_dao.upsert_custom_display_name("dest1", "First")
        announce_dao.delete_custom_display_name("dest1")
        announce_dao.upsert_custom_display_name("dest1", "Second")
        assert announce_dao.get_custom_display_name("dest1") == "Second"

    def test_unicode_display_name(self, announce_dao):
        announce_dao.upsert_custom_display_name("dest1", "\u5c71\u7530\u592a\u90ce")
        assert (
            announce_dao.get_custom_display_name("dest1") == "\u5c71\u7530\u592a\u90ce"
        )

    def test_very_long_display_name(self, announce_dao):
        long_name = "A" * 10000
        announce_dao.upsert_custom_display_name("dest1", long_name)
        assert announce_dao.get_custom_display_name("dest1") == long_name

    def test_empty_string_display_name(self, announce_dao):
        announce_dao.upsert_custom_display_name("dest1", "")
        assert announce_dao.get_custom_display_name("dest1") == ""

    def test_multiple_destinations_independent(self, announce_dao):
        announce_dao.upsert_custom_display_name("dest1", "Alice")
        announce_dao.upsert_custom_display_name("dest2", "Bob")
        announce_dao.delete_custom_display_name("dest1")
        assert announce_dao.get_custom_display_name("dest1") is None
        assert announce_dao.get_custom_display_name("dest2") == "Bob"


# ---------------------------------------------------------------------------
# Contacts DAO edge cases
# ---------------------------------------------------------------------------


class TestContactsEdgeCases:
    def test_add_contact_upsert_preserves_addresses(self, contacts_dao, provider):
        contacts_dao.add_contact(
            "Alice", "ih1", lxmf_address="lxmf1", lxst_address="lxst1",
        )
        contacts_dao.add_contact(
            "Alice Updated", "ih1", lxmf_address=None, lxst_address=None,
        )
        row = provider.fetchone(
            "SELECT * FROM contacts WHERE remote_identity_hash = ?", ("ih1",),
        )
        assert row["name"] == "Alice Updated"
        assert row["lxmf_address"] == "lxmf1"
        assert row["lxst_address"] == "lxst1"

    def test_add_contact_upsert_replaces_name_unconditionally(
        self, contacts_dao, provider,
    ):
        """Verifies add_contact always overwrites name on conflict."""
        contacts_dao.add_contact("Real Name", "ih2")
        contacts_dao.add_contact("Overwritten", "ih2")
        row = provider.fetchone(
            "SELECT * FROM contacts WHERE remote_identity_hash = ?", ("ih2",),
        )
        assert row["name"] == "Overwritten"

    def test_update_contact_partial(self, contacts_dao, provider):
        contacts_dao.add_contact("Alice", "ih3", lxmf_address="lx3")
        row = provider.fetchone(
            "SELECT id FROM contacts WHERE remote_identity_hash = ?", ("ih3",),
        )
        cid = row["id"]
        contacts_dao.update_contact(cid, name="Alice Renamed")
        updated = provider.fetchone("SELECT * FROM contacts WHERE id = ?", (cid,))
        assert updated["name"] == "Alice Renamed"
        assert updated["lxmf_address"] == "lx3"

    def test_update_contact_no_fields_is_noop(self, contacts_dao, provider):
        contacts_dao.add_contact("NoOp", "ih4")
        row = provider.fetchone(
            "SELECT id FROM contacts WHERE remote_identity_hash = ?", ("ih4",),
        )
        contacts_dao.update_contact(row["id"])
        updated = provider.fetchone("SELECT * FROM contacts WHERE id = ?", (row["id"],))
        assert updated["name"] == "NoOp"

    def test_update_contact_clear_image(self, contacts_dao, provider):
        contacts_dao.add_contact(
            "WithImage", "ih5", custom_image="data:image/png;base64,abc",
        )
        row = provider.fetchone(
            "SELECT id FROM contacts WHERE remote_identity_hash = ?", ("ih5",),
        )
        assert row is not None
        cid = row["id"]
        contacts_dao.update_contact(cid, clear_image=True)
        updated = provider.fetchone("SELECT * FROM contacts WHERE id = ?", (cid,))
        assert updated["custom_image"] is None

    def test_get_contact_by_identity_hash_matches_lxmf_address(self, contacts_dao):
        contacts_dao.add_contact("Via LXMF", "ih6", lxmf_address="lxmf6")
        result = contacts_dao.get_contact_by_identity_hash("lxmf6")
        assert result is not None
        assert result["name"] == "Via LXMF"

    def test_get_contact_by_identity_hash_matches_lxst_address(self, contacts_dao):
        contacts_dao.add_contact("Via LXST", "ih7", lxst_address="lxst7")
        result = contacts_dao.get_contact_by_identity_hash("lxst7")
        assert result is not None
        assert result["name"] == "Via LXST"

    def test_delete_nonexistent_contact(self, contacts_dao):
        contacts_dao.delete_contact(99999)

    def test_unicode_contact_name(self, contacts_dao, provider):
        contacts_dao.add_contact("\u00c9milie \u00d6sterreich", "ih8")
        row = provider.fetchone(
            "SELECT * FROM contacts WHERE remote_identity_hash = ?", ("ih8",),
        )
        assert row["name"] == "\u00c9milie \u00d6sterreich"

    def test_contacts_search_case_insensitive_name(self, contacts_dao):
        contacts_dao.add_contact("Charlie Delta", "ih9")
        results = contacts_dao.get_contacts(search="charlie")
        assert len(results) >= 1
        assert any(r["name"] == "Charlie Delta" for r in results)

    def test_contacts_count_with_search(self, contacts_dao):
        contacts_dao.add_contact("Alpha", "ih10")
        contacts_dao.add_contact("Beta", "ih11")
        contacts_dao.add_contact("AlphaTwo", "ih12")
        assert contacts_dao.get_contacts_count(search="alpha") == 2
        assert contacts_dao.get_contacts_count() == 3


# ---------------------------------------------------------------------------
# parse_lxmf_display_name fallback behaviour
# ---------------------------------------------------------------------------


class TestParseLxmfDisplayNameFallback:
    def test_none_returns_anonymous_peer(self):
        assert parse_lxmf_display_name(None) == "Anonymous Peer"

    def test_none_with_custom_default(self):
        assert parse_lxmf_display_name(None, default_value="Fallback") == "Fallback"

    def test_none_with_none_default(self):
        assert parse_lxmf_display_name(None, default_value=None) is None

    @pytest.mark.skipif(msgpack is None, reason="msgpack not available")
    def test_valid_app_data_returns_name(self):
        name = "TestNode"
        packed = msgpack.packb([name.encode(), None, None])
        b64 = base64.b64encode(packed).decode()
        assert parse_lxmf_display_name(b64) == name

    @pytest.mark.skipif(msgpack is None, reason="msgpack not available")
    def test_empty_name_in_app_data(self):
        packed = msgpack.packb([b"", None, None])
        b64 = base64.b64encode(packed).decode()
        result = parse_lxmf_display_name(b64)
        assert result == ""

    def test_garbage_base64(self):
        result = parse_lxmf_display_name("!!!not-base64!!!")
        assert isinstance(result, str)

    @pytest.mark.skipif(msgpack is None, reason="msgpack not available")
    def test_none_name_in_app_data_returns_default(self):
        packed = msgpack.packb([None, None, None])
        b64 = base64.b64encode(packed).decode()
        assert parse_lxmf_display_name(b64) == "Anonymous Peer"


# ---------------------------------------------------------------------------
# Integration: announce + custom name + contact name resolution priority
# ---------------------------------------------------------------------------


class TestNameResolutionPriority:
    """Simulates the priority chain:
    custom_display_name > announce app_data > contact name > 'Anonymous Peer'.
    """

    def test_custom_name_wins_over_announce(self, announce_dao):
        dest = "f" * 32
        announce_dao.upsert_announce(
            _base_announce(dest=dest, app_data="AnnounceAlice"),
        )
        announce_dao.upsert_custom_display_name(dest, "CustomAlice")

        custom = announce_dao.get_custom_display_name(dest)
        row = announce_dao.get_announce_by_hash(dest)
        display = custom or row["app_data"] or "Anonymous Peer"
        assert display == "CustomAlice"

    def test_announce_used_when_no_custom(self, announce_dao):
        dest = "f" * 32
        announce_dao.upsert_announce(_base_announce(dest=dest, app_data="AnnounceOnly"))

        custom = announce_dao.get_custom_display_name(dest)
        row = announce_dao.get_announce_by_hash(dest)
        display = custom or row["app_data"] or "Anonymous Peer"
        assert display == "AnnounceOnly"

    def test_fallback_to_anonymous_when_nothing(self, announce_dao):
        dest = "f" * 32
        announce_dao.upsert_announce(_base_announce(dest=dest, app_data=None))

        custom = announce_dao.get_custom_display_name(dest)
        row = announce_dao.get_announce_by_hash(dest)
        display = custom or row["app_data"] or "Anonymous Peer"
        assert display == "Anonymous Peer"

    def test_contact_name_used_when_no_announce_no_custom(
        self, announce_dao, contacts_dao, provider,
    ):
        dest = "f" * 32
        announce_dao.upsert_announce(_base_announce(dest=dest, app_data=None))
        contacts_dao.add_contact("ContactAlice", dest, lxmf_address=dest)

        custom = announce_dao.get_custom_display_name(dest)
        row = announce_dao.get_announce_by_hash(dest)
        contact = contacts_dao.get_contact_by_identity_hash(dest)
        contact_name = contact["name"] if contact else None
        display = custom or row["app_data"] or contact_name or "Anonymous Peer"
        assert display == "ContactAlice"

    def test_clearing_custom_name_falls_back_to_announce(self, announce_dao):
        dest = "f" * 32
        announce_dao.upsert_announce(_base_announce(dest=dest, app_data="AnnounceName"))
        announce_dao.upsert_custom_display_name(dest, "Custom")
        announce_dao.delete_custom_display_name(dest)

        custom = announce_dao.get_custom_display_name(dest)
        row = announce_dao.get_announce_by_hash(dest)
        display = custom or row["app_data"] or "Anonymous Peer"
        assert display == "AnnounceName"

    def test_wiping_announce_with_contact_still_resolves(
        self, announce_dao, contacts_dao,
    ):
        """After the COALESCE fix, this should not happen, but if app_data
        was already NULL, the contact name should still be available.
        """
        dest = "f" * 32
        contacts_dao.add_contact("ContactFallback", dest, lxmf_address=dest)
        announce_dao.upsert_announce(_base_announce(dest=dest, app_data=None))

        custom = announce_dao.get_custom_display_name(dest)
        row = announce_dao.get_announce_by_hash(dest)
        contact = contacts_dao.get_contact_by_identity_hash(dest)
        contact_name = contact["name"] if contact else None
        display = custom or row["app_data"] or contact_name or "Anonymous Peer"
        assert display == "ContactFallback"


# ---------------------------------------------------------------------------
# Announce trim does not break name resolution
# ---------------------------------------------------------------------------


class TestAnnounceTrimSafety:
    def test_trim_does_not_remove_active_announce(self, announce_dao):
        for i in range(5):
            announce_dao.upsert_announce(
                _base_announce(dest=f"{i:032x}", app_data=f"name_{i}"),
            )
        announce_dao.trim_announces_for_aspect("lxmf.delivery", max_rows=3)
        remaining = announce_dao.get_announces(aspect="lxmf.delivery")
        assert len(remaining) == 3
        for r in remaining:
            assert r["app_data"] is not None
            assert r["app_data"].startswith("name_")


# ---------------------------------------------------------------------------
# Contacts + custom display name sync edge cases
# ---------------------------------------------------------------------------


class TestContactCustomNameSync:
    def test_renaming_contact_and_custom_name_independently(
        self, contacts_dao, announce_dao, provider,
    ):
        contacts_dao.add_contact("Alice", "ih20", lxmf_address="lx20")
        row = provider.fetchone(
            "SELECT id FROM contacts WHERE remote_identity_hash = ?", ("ih20",),
        )
        cid = row["id"]

        announce_dao.upsert_custom_display_name("lx20", "Alice Custom")
        contacts_dao.update_contact(cid, name="Alice Renamed")

        assert announce_dao.get_custom_display_name("lx20") == "Alice Custom"
        contact = contacts_dao.get_contact(cid)
        assert contact["name"] == "Alice Renamed"

    def test_synced_rename_updates_both(self, contacts_dao, announce_dao, provider):
        """Simulates what the UI should do: update both contact and custom name."""
        contacts_dao.add_contact("Bob", "ih21", lxmf_address="lx21")
        row = provider.fetchone(
            "SELECT id FROM contacts WHERE remote_identity_hash = ?", ("ih21",),
        )
        cid = row["id"]

        new_name = "Bob Renamed"
        contacts_dao.update_contact(cid, name=new_name)
        announce_dao.upsert_custom_display_name("lx21", new_name)

        contact = contacts_dao.get_contact(cid)
        custom = announce_dao.get_custom_display_name("lx21")
        assert contact["name"] == new_name
        assert custom == new_name
