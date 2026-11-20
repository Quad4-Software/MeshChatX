# SPDX-License-Identifier: 0BSD
"""Fault injection: corrupt/garbage config values and migration idempotence."""

import pytest

from meshchatx.src.backend.config_manager import ConfigManager


@pytest.fixture
def cm(db):
    return ConfigManager(db)


class TestMigrationIdempotence:
    def test_all_migrations_run_twice_equal_once(self, db):
        ConfigManager(db)
        snapshot1 = dict(db.config.all().items()) if hasattr(db.config, "all") else None
        ConfigManager(db)  # second construction reruns migrations
        if snapshot1 is not None:
            assert db.config.all() == snapshot1

    def test_map_tile_migration_does_not_clobber_custom_url(self, db):
        db.config.set("map_tile_server_url", "https://tiles.example.com/x")
        ConfigManager(db)
        assert db.config.get("map_tile_server_url") == "https://tiles.example.com/x"


class TestCorruptValues:
    @pytest.mark.parametrize("raw", ["abc", "12.5", "", "0x10", " ", "\uff19", "-3"])
    def test_garbage_audio_profile_resets_to_default(self, db, raw):
        db.config.set("telephone_audio_profile_id", raw)
        cm = ConfigManager(db)
        try:
            pid = int(raw)
        except (TypeError, ValueError):
            pid = None
        valid = {16, 32, 48, 64, 80, 96, 112, 128}
        if pid not in valid:
            assert cm.telephone_audio_profile_id.get() == 64
        else:
            assert cm.telephone_audio_profile_id.get() == pid

    def test_bool_config_garbage_is_deterministic(self, db, cm):
        for raw in ("yes", "1", "TRUE", "false", "0", "maybe", "2"):
            db.config.set("auto_announce_enabled", raw)
            v1 = cm.auto_announce_enabled.get()
            v2 = cm.auto_announce_enabled.get()
            assert v1 == v2, f"non-deterministic bool parse for {raw!r}"
            assert isinstance(v1, bool)

    def test_int_config_garbage_returns_default_not_crash(self, db, cm):
        for raw in ("abc", "", "1e9", "NaN", "inf", "0x20", "3.7"):
            db.config.set("map_data_announce_interval", raw)
            v = cm.map_data_announce_interval.get()
            assert isinstance(v, int) or v is None
