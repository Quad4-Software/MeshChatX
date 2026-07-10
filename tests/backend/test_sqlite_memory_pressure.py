# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend.database import Database


def test_apply_memory_pressure_pragmas_roundtrip(tmp_path):
    db = Database(str(tmp_path / "pressure.db"))
    db.initialize()
    assert db.apply_memory_pressure_pragmas(True) is True
    assert db._sqlite_memory_relaxed is True
    assert db._get_pragma_value("temp_store") == 1  # FILE
    assert db.provider.prefer_temp_store_file is True
    assert db.apply_memory_pressure_pragmas(False) is True
    assert db._sqlite_memory_relaxed is False
    assert db._get_pragma_value("temp_store") == 2  # MEMORY
    assert db.provider.prefer_temp_store_file is False


def test_memory_pressure_keeps_memory_temp_under_landlock(tmp_path):
    db = Database(str(tmp_path / "pressure_ll.db"))
    db.initialize()
    assert db.apply_memory_pressure_pragmas(True, landlock_active=True) is True
    assert db._sqlite_memory_relaxed is True
    assert db._get_pragma_value("temp_store") == 2  # MEMORY
    assert db.provider.prefer_temp_store_file is False
    assert db._get_pragma_value("cache_size") == -2000
    assert db._get_pragma_value("mmap_size") == 0
