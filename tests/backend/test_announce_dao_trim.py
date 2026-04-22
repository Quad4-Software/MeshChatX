# SPDX-License-Identifier: 0BSD

import os
import tempfile

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider


def _insert(db, dest_hex, aspect, updated_order, identity_hex=None):
    db.announces.upsert_announce(
        {
            "destination_hash": dest_hex,
            "aspect": aspect,
            "identity_hash": identity_hex or ("a" * 32),
            "identity_public_key": "cHVibmtleQ==",
            "app_data": None,
            "rssi": None,
            "snr": None,
            "quality": None,
        },
    )
    db.provider.execute(
        "UPDATE announces SET updated_at = ? WHERE destination_hash = ?",
        (updated_order, dest_hex),
    )


def _new_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    db = Database(path)
    db.initialize()
    return db, path


def _cleanup(db, path):
    if db is not None:
        try:
            db.close()
        except Exception:
            pass
    DatabaseProvider._instance = None
    if path:
        try:
            os.unlink(path)
        except OSError:
            pass
        for suffix in ("-wal", "-shm"):
            try:
                os.unlink(path + suffix)
            except OSError:
                pass


def test_trim_announces_for_aspect_drops_oldest():
    db = path = None
    try:
        db, path = _new_db()
        aspect = "lxmf.delivery"
        _insert(db, "01" * 16, aspect, "2000-01-01T00:00:00Z")
        _insert(db, "02" * 16, aspect, "2000-01-02T00:00:00Z")
        _insert(db, "03" * 16, aspect, "2000-01-03T00:00:00Z")
        db.announces.trim_announces_for_aspect(aspect, 2)
        rows = db.announces.get_announces(aspect=aspect)
        hashes = {r["destination_hash"] for r in rows}
        assert hashes == {"03" * 16, "02" * 16}
    finally:
        _cleanup(db, path)


def test_trim_preserves_favourited_destination():
    """Favourited NomadNet/destination announces must survive aspect trim."""
    db = path = None
    try:
        db, path = _new_db()
        aspect = "nomadnetwork.node"

        _insert(db, "01" * 16, aspect, "2000-01-01T00:00:00Z")
        _insert(db, "02" * 16, aspect, "2000-01-02T00:00:00Z")
        _insert(db, "03" * 16, aspect, "2000-01-03T00:00:00Z")
        _insert(db, "04" * 16, aspect, "2000-01-04T00:00:00Z")

        db.announces.upsert_favourite("01" * 16, "Favourite Node", aspect)

        db.announces.trim_announces_for_aspect(aspect, 2)

        rows = db.announces.get_announces(aspect=aspect)
        hashes = {r["destination_hash"] for r in rows}

        assert "01" * 16 in hashes, "favourited announce was wrongly trimmed"
        assert "04" * 16 in hashes, "newest announce should be retained"
        assert "02" * 16 not in hashes
        assert "03" * 16 not in hashes
    finally:
        _cleanup(db, path)


def test_trim_preserves_contact_announce_by_identity_hash():
    """Announces tied to a saved contact via identity hash must not be dropped."""
    db = path = None
    try:
        db, path = _new_db()
        aspect = "lxmf.delivery"

        contact_identity = "b" * 32

        _insert(db, "01" * 16, aspect, "2000-01-01T00:00:00Z", contact_identity)
        _insert(db, "02" * 16, aspect, "2000-01-02T00:00:00Z")
        _insert(db, "03" * 16, aspect, "2000-01-03T00:00:00Z")
        _insert(db, "04" * 16, aspect, "2000-01-04T00:00:00Z")

        db.contacts.add_contact(
            name="Friend",
            remote_identity_hash=contact_identity,
        )

        db.announces.trim_announces_for_aspect(aspect, 2)

        rows = db.announces.get_announces(aspect=aspect)
        hashes = {r["destination_hash"] for r in rows}

        assert "01" * 16 in hashes, "contact-linked announce was wrongly trimmed"
        assert "04" * 16 in hashes
    finally:
        _cleanup(db, path)


def test_trim_preserves_contact_announce_by_lxmf_address():
    """Announces matching contacts.lxmf_address must be retained."""
    db = path = None
    try:
        db, path = _new_db()
        aspect = "lxmf.delivery"

        protected_dest = "01" * 16

        _insert(db, protected_dest, aspect, "2000-01-01T00:00:00Z")
        _insert(db, "02" * 16, aspect, "2000-01-02T00:00:00Z")
        _insert(db, "03" * 16, aspect, "2000-01-03T00:00:00Z")
        _insert(db, "04" * 16, aspect, "2000-01-04T00:00:00Z")

        db.contacts.add_contact(
            name="Friend",
            remote_identity_hash="c" * 32,
            lxmf_address=protected_dest,
        )

        db.announces.trim_announces_for_aspect(aspect, 2)

        rows = db.announces.get_announces(aspect=aspect)
        hashes = {r["destination_hash"] for r in rows}

        assert protected_dest in hashes
        assert "04" * 16 in hashes
    finally:
        _cleanup(db, path)
