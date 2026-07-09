# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend.database import Database


def test_apply_memory_pressure_pragmas_roundtrip(tmp_path):
    db = Database(str(tmp_path / "pressure.db"))
    db.initialize()
    assert db.apply_memory_pressure_pragmas(True) is True
    assert db._sqlite_memory_relaxed is True
    assert db._get_pragma_value("temp_store") == 1  # FILE
    assert db.apply_memory_pressure_pragmas(False) is True
    assert db._sqlite_memory_relaxed is False
    assert db._get_pragma_value("temp_store") == 2  # MEMORY
