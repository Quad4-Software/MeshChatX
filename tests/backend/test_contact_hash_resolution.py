# SPDX-License-Identifier: 0BSD

"""Contact resolution across identity / LXMF / LXST hash forms."""

from unittest.mock import MagicMock

from meshchatx.meshchat import ReticulumMeshChat

IDENTITY = "a1" * 16
LXMF = "b2" * 16
LXST = "c3" * 16


def _app_with_db(contact_row=None, announces=None):
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    ctx.database = MagicMock()
    ctx.database.announces.get_announce_by_hash.return_value = None
    ctx.database.announces.get_announces_by_identity_hash.return_value = announces or []
    ctx.database.contacts.get_contact_by_identity_hash.return_value = contact_row
    app.current_context = ctx
    app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=LXMF)
    app.get_lxst_telephony_hash_for_identity_hash = MagicMock(return_value=LXST)
    return app


def test_related_hashes_include_announced_and_derived_destinations():
    app = _app_with_db(
        announces=[
            {
                "destination_hash": LXMF,
                "identity_hash": IDENTITY,
                "aspect": "lxmf.delivery",
            },
        ],
    )
    related = app._related_hashes_for_contact_lookup(IDENTITY)
    assert IDENTITY in related
    assert LXMF in related
    assert LXST in related


def test_is_contact_true_when_saved_under_lxmf_primary_key():
    contact = {"id": 1, "name": "Friend", "remote_identity_hash": LXMF}

    def lookup(primary, related_hashes=None):
        keys = {primary, *(related_hashes or ())}
        if LXMF in keys:
            return contact
        return None

    app = _app_with_db()
    app.current_context.database.contacts.get_contact_by_identity_hash.side_effect = (
        lookup
    )
    app.current_context.database.announces.get_announces_by_identity_hash.return_value = [
        {
            "destination_hash": LXMF,
            "identity_hash": IDENTITY,
            "aspect": "lxmf.delivery",
        },
    ]

    assert app._is_contact(IDENTITY) is True
    assert app._resolve_contact_for_hash(IDENTITY)["name"] == "Friend"


def test_is_contact_false_for_unknown_peer():
    app = _app_with_db(contact_row=None)
    assert app._is_contact(IDENTITY) is False
