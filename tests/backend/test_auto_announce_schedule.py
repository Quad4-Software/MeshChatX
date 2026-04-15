"""Regression tests for auto-announce and periodic interval scheduling (config / DB time)."""

import pytest

from meshchatx.src.backend.meshchat_utils import interval_action_due


class TestIntervalActionDue:
    def test_disabled_never_fires(self):
        assert interval_action_due(False, None, 3600, 1_000_000.0) is False
        assert interval_action_due(False, 1, 3600, 1_000_000.0) is False

    def test_zero_or_negative_interval_never_fires_even_if_enabled(self):
        assert interval_action_due(True, 100, 0, 200.0) is False
        assert interval_action_due(True, 100, -1, 200.0) is False
        assert interval_action_due(True, None, 0, 200.0) is False

    def test_none_interval_treated_as_zero(self):
        assert interval_action_due(True, 100, None, 500.0) is False

    def test_first_run_when_last_at_is_none(self):
        assert interval_action_due(True, None, 900, 1.0) is True

    def test_due_when_past_next_boundary(self):
        now = 1_000_000.0
        last = int(now - 1000)
        assert interval_action_due(True, last, 900, now) is True

    def test_not_due_inside_interval(self):
        now = 1_000_000.0
        last = int(now - 100)
        assert interval_action_due(True, last, 900, now) is False

    def test_future_last_at_treated_as_due_regression(self):
        """Stale future timestamps (clock skew, restored DB) must not stall the loop."""
        now = 1_000_000.0
        last = int(now + 86_400)
        assert interval_action_due(True, last, 3600, now) is True

    def test_boundary_exclusive(self):
        now = 1_000_000.0
        last = int(now - 900)
        assert interval_action_due(True, last, 900, now) is False
        assert interval_action_due(True, last, 900, now + 0.001) is True

    def test_propagation_sync_equivalent_enabled_flag(self):
        interval = 600
        now = 500_000.0
        last = int(now - 601)
        assert interval_action_due(interval > 0, last, interval, now) is True

    def test_large_interval_last_at_slightly_in_future_ntp(self):
        """Small positive skew still triggers one correction announce."""
        now = 1_000_000.0
        last = int(now + 2)
        assert interval_action_due(True, last, 3600, now) is True


@pytest.mark.parametrize(
    ("enabled", "last", "interval", "now", "expected"),
    [
        (True, None, 60, 0.0, True),
        (True, 0, 60, 61.0, True),
        (True, 0, 60, 60.0, False),
        (False, None, 60, 999.0, False),
    ],
)
def test_interval_action_due_table(enabled, last, interval, now, expected):
    assert interval_action_due(enabled, last, interval, now) is expected


def test_last_announced_at_config_roundtrip_db(tmp_path):
    """Config table stores last_announced_at; invalid strings fall back to default."""
    import os

    from meshchatx.src.backend.config_manager import ConfigManager
    from meshchatx.src.backend.database import Database

    db_path = tmp_path / "c.db"
    database = Database(str(db_path))
    database.initialize()
    try:
        cfg = ConfigManager(database)
        cfg.last_announced_at.set(1_700_000_000)
        assert cfg.last_announced_at.get() == 1_700_000_000

        cfg2 = ConfigManager(database)
        assert cfg2.last_announced_at.get() == 1_700_000_000

        database.config.set("last_announced_at", "not-an-int")
        cfg3 = ConfigManager(database)
        assert cfg3.last_announced_at.get() is None
    finally:
        database.close()
        if os.path.exists(db_path):
            os.remove(db_path)
