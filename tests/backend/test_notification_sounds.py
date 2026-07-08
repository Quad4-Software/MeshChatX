# SPDX-License-Identifier: 0BSD

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.config_manager import ConfigManager
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.ringtone_manager import RingtoneManager


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


def test_notification_sound_config_defaults(db):
    config = ConfigManager(db)
    assert config.notification_sound_enabled.get() is False
    assert config.notification_sound_preferred_id.get() == 0
    assert config.notification_sound_volume.get() == 100


def test_notification_sound_config_persists(db):
    config = ConfigManager(db)
    config.notification_sound_enabled.set(True)
    config.notification_sound_preferred_id.set(4)
    config.notification_sound_volume.set(60)

    config2 = ConfigManager(db)
    assert config2.notification_sound_enabled.get() is True
    assert config2.notification_sound_preferred_id.get() == 4
    assert config2.notification_sound_volume.get() == 60


def test_notification_sounds_dao_crud(db):
    sound_id = db.notification_sounds.add(
        filename="alert.mp3",
        storage_filename="notification_abcd.opus",
        display_name="Alert",
    )
    assert sound_id > 0

    row = db.notification_sounds.get_by_id(sound_id)
    assert row["filename"] == "alert.mp3"
    assert row["display_name"] == "Alert"
    assert row["is_primary"] == 1

    all_sounds = db.notification_sounds.get_all()
    assert len(all_sounds) == 1

    primary = db.notification_sounds.get_primary()
    assert primary["id"] == sound_id

    db.notification_sounds.update(sound_id, display_name="Updated Alert")
    updated = db.notification_sounds.get_by_id(sound_id)
    assert updated["display_name"] == "Updated Alert"

    db.notification_sounds.delete(sound_id)
    assert db.notification_sounds.get_by_id(sound_id) is None


def test_notification_sound_manager_uses_separate_storage_dir(tmp_path):
    config = MagicMock()
    manager = RingtoneManager(
        config,
        str(tmp_path),
        asset_subdir="notification_sounds",
        filename_prefix="notification",
    )
    assert manager.storage_dir == os.path.join(str(tmp_path), "notification_sounds")
    assert os.path.isdir(manager.storage_dir)
