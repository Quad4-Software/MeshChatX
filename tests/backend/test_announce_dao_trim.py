# SPDX-License-Identifier: 0BSD

import os
import tempfile

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider


def _insert(db, dest_hex, aspect, updated_order):
    db.announces.upsert_announce(
        {
            "destination_hash": dest_hex,
            "aspect": aspect,
            "identity_hash": "a" * 32,
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


def test_trim_announces_for_aspect_drops_oldest():
    path = None
    db = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        db = Database(path)
        db.initialize()
        aspect = "lxmf.delivery"
        _insert(db, "01" * 16, aspect, "2000-01-01T00:00:00Z")
        _insert(db, "02" * 16, aspect, "2000-01-02T00:00:00Z")
        _insert(db, "03" * 16, aspect, "2000-01-03T00:00:00Z")
        db.announces.trim_announces_for_aspect(aspect, 2)
        rows = db.announces.get_announces(aspect=aspect)
        hashes = {r["destination_hash"] for r in rows}
        assert hashes == {"03" * 16, "02" * 16}
    finally:
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
