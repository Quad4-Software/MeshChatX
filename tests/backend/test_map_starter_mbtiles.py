# SPDX-License-Identifier: 0BSD

import os
from unittest.mock import MagicMock

from meshchatx.src.backend.map_manager import MapManager
from meshchatx.src.backend.map_starter_mbtiles import (
    STARTER_FILENAME,
    ensure_bundled_starter_file,
    write_starter_mbtiles,
)


def _config(tmp_path):
    cfg = MagicMock()
    offline_path = {"value": None}
    offline_enabled = {"value": True}

    class StrCfg:
        def get(self):
            return offline_path["value"]

        def set(self, v):
            offline_path["value"] = v

    class BoolCfg:
        def get(self):
            return offline_enabled["value"]

        def set(self, v):
            offline_enabled["value"] = v

    class DirCfg:
        def get(self):
            return None

    cfg.map_offline_path = StrCfg()
    cfg.map_offline_enabled = BoolCfg()
    cfg.map_mbtiles_dir = DirCfg()
    return cfg


def test_write_starter_mbtiles_has_tiles(tmp_path):
    dest = tmp_path / "starter.mbtiles"
    write_starter_mbtiles(dest, max_zoom=1)
    assert dest.is_file()
    assert dest.stat().st_size > 1024


def test_write_starter_default_zoom_covers_z0_to_z4(tmp_path):
    import sqlite3

    dest = tmp_path / "starter_z4.mbtiles"
    write_starter_mbtiles(dest)
    conn = sqlite3.connect(str(dest))
    try:
        count = conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
        maxzoom = conn.execute(
            "SELECT value FROM metadata WHERE name='maxzoom'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert maxzoom == "4"
    # 1 + 4 + 16 + 64 + 256
    assert count == 341


def test_ensure_starter_seeds_when_empty(tmp_path):
    cfg = _config(tmp_path)
    mm = MapManager(cfg, str(tmp_path))
    path = mm.ensure_starter_mbtiles()
    assert path is not None
    assert os.path.basename(path) == STARTER_FILENAME
    assert os.path.exists(path)
    # Second call should keep existing
    path2 = mm.ensure_starter_mbtiles()
    assert path2 == path


def test_ensure_starter_force_restore(tmp_path):
    cfg = _config(tmp_path)
    mm = MapManager(cfg, str(tmp_path))
    first = mm.ensure_starter_mbtiles()
    os.remove(first)
    restored = mm.ensure_starter_mbtiles(force_restore=True)
    assert restored is not None
    assert os.path.exists(restored)


def test_bundled_starter_generate():
    path = ensure_bundled_starter_file()
    assert path.is_file()


def test_concurrent_ensure_starter_mbtiles_race(tmp_path):
    """Oracle: parallel seeds must leave one valid SQLite MBTiles, not a torn file."""
    import sqlite3
    import threading

    cfg = _config(tmp_path)
    mm = MapManager(cfg, str(tmp_path))
    results = []
    errors = []

    def worker():
        try:
            results.append(mm.ensure_starter_mbtiles())
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert len(results) == 8
    assert len(set(results)) == 1
    path = results[0]
    assert path is not None
    assert os.path.exists(path)
    conn = sqlite3.connect(path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
        name = conn.execute("SELECT value FROM metadata WHERE name='name'").fetchone()[
            0
        ]
    finally:
        conn.close()
    assert count == 341
    assert "starter" in name.lower()


def test_write_starter_atomic_replace(tmp_path):
    dest = tmp_path / "atomic.mbtiles"
    write_starter_mbtiles(dest, max_zoom=0)
    first_size = dest.stat().st_size
    write_starter_mbtiles(dest, max_zoom=1)
    assert dest.is_file()
    assert dest.stat().st_size >= first_size
    leftovers = list(tmp_path.glob(".atomic.mbtiles.*.tmp"))
    assert leftovers == []
