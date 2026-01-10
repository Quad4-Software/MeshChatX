import os
import shutil
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.map_manager import MapManager


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.map_offline_path.get.return_value = None
    config.map_mbtiles_dir.get.return_value = None
    return config


def test_map_manager_init(mock_config, temp_dir):
    mm = MapManager(mock_config, temp_dir)
    assert mm.storage_dir == temp_dir


def test_get_offline_path_default(mock_config, temp_dir):
    mm = MapManager(mock_config, temp_dir)
    default_path = os.path.join(temp_dir, "offline_map.mbtiles")

    # Not exists
    assert mm.get_offline_path() is None

    # Exists
    with open(default_path, "w") as f:
        f.write("data")
    assert mm.get_offline_path() == default_path


def test_list_mbtiles(mock_config, temp_dir):
    mm = MapManager(mock_config, temp_dir)

    # Create some dummy .mbtiles files
    f1 = os.path.join(temp_dir, "map1.mbtiles")
    f2 = os.path.join(temp_dir, "map2.mbtiles")
    with open(f1, "w") as f:
        f.write("1")
    with open(f2, "w") as f:
        f.write("22")

    files = mm.list_mbtiles()
    assert len(files) == 2
    assert any(f["name"] == "map1.mbtiles" for f in files)
    assert any(f["size"] == 2 for f in files if f["name"] == "map2.mbtiles")


def test_get_metadata(mock_config, temp_dir):
    mm = MapManager(mock_config, temp_dir)
    db_path = os.path.join(temp_dir, "test.mbtiles")
    mock_config.map_offline_path.get.return_value = db_path

    # Create valid sqlite mbtiles
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE metadata (name text, value text)")
    conn.execute("INSERT INTO metadata VALUES ('name', 'Test Map')")
    conn.execute("INSERT INTO metadata VALUES ('format', 'jpg')")
    conn.commit()
    conn.close()

    metadata = mm.get_metadata()
    assert metadata["name"] == "Test Map"
    assert metadata["format"] == "jpg"


def test_get_tile(mock_config, temp_dir):
    mm = MapManager(mock_config, temp_dir)
    db_path = os.path.join(temp_dir, "test.mbtiles")
    mock_config.map_offline_path.get.return_value = db_path

    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)",
    )
    # Zoom 0, Tile 0,0. TMS y for 0/0/0 is (1<<0)-1-0 = 0
    conn.execute(
        "INSERT INTO tiles VALUES (0, 0, 0, ?)",
        (sqlite3.Binary(b"tile_data"),),
    )
    conn.commit()
    conn.close()

    tile = mm.get_tile(0, 0, 0)
    assert tile == b"tile_data"


def test_start_export_status(mock_config, temp_dir):
    mm = MapManager(mock_config, temp_dir)

    with patch.object(mm, "_run_export"):
        export_id = mm.start_export("test_id", [0, 0, 1, 1], 0, 1)
        assert export_id == "test_id"
        status = mm.get_export_status(export_id)
        assert status["status"] == "starting"
