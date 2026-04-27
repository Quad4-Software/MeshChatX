# SPDX-License-Identifier: 0BSD

import os
import tempfile

from meshchatx.src.backend.config_manager import ConfigManager
from meshchatx.src.backend.database import Database


def test_migrates_legacy_translator_enabled_to_per_backend_keys():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "t.db")
        db = Database(db_path)
        db.initialize()
        db.config.set("translator_enabled", "true")
        config = ConfigManager(db)
        assert config.translator_argos_enabled.get() is True
        assert config.translator_libretranslate_enabled.get() is True
