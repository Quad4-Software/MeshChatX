# SPDX-License-Identifier: 0BSD

"""Config defaults for offline-first maps."""

import os
import tempfile

import pytest

from meshchatx.src.backend.config_manager import ConfigManager
from meshchatx.src.backend.database import Database


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    database = Database(path)
    database.initialize()
    yield database
    database.close()
    if os.path.exists(path):
        os.remove(path)


def test_map_offline_enabled_defaults_true(db):
    cfg = ConfigManager(db)
    assert cfg.map_offline_enabled.get() is True


def test_map_coordinate_format_defaults_wgs84(db):
    cfg = ConfigManager(db)
    assert cfg.map_coordinate_format.get() == "wgs84"
