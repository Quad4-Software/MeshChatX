# SPDX-License-Identifier: 0BSD

import os
import tempfile

import pytest

from meshchatx.src.backend.database import (
    Database,
    _sanitize_pragma_read_name,
    _sanitize_wal_checkpoint_mode,
)
from meshchatx.src.backend.database.provider import DatabaseProvider


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)
    wal = path + "-wal"
    shm = path + "-shm"
    for p in (wal, shm):
        if os.path.exists(p):
            os.remove(p)


@pytest.fixture(autouse=True)
def reset_db_singleton(temp_db_path):
    DatabaseProvider._instance = None
    yield
    DatabaseProvider._instance = None


def test_sanitize_pragma_read_name_accepts_known_tokens():
    assert _sanitize_pragma_read_name("journal_mode") == "journal_mode"
    assert _sanitize_pragma_read_name("  page_size  ") == "page_size"


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "journal mode",
        "journal-mode",
        "x;detach",
        "x'y",
        "../../../x",
        "pragma(x)",
    ],
)
def test_sanitize_pragma_read_name_rejects_injection(bad):
    assert _sanitize_pragma_read_name(bad) is None


def test_sanitize_wal_checkpoint_mode_accepts_keywords():
    assert _sanitize_wal_checkpoint_mode("truncate") == "TRUNCATE"
    assert _sanitize_wal_checkpoint_mode("PASSIVE") == "PASSIVE"


def test_sanitize_wal_checkpoint_mode_rejects_injection():
    with pytest.raises(ValueError):
        _sanitize_wal_checkpoint_mode("FULL);VACUUM")
    with pytest.raises(ValueError):
        _sanitize_wal_checkpoint_mode("bogus")


def test_get_pragma_value_returns_default_for_malicious_name(temp_db_path):
    db = Database(temp_db_path)
    db.initialize()
    assert db._get_pragma_value("journal_mode;evil", "fallback") == "fallback"
    jm = db._get_pragma_value("journal_mode")
    assert jm is not None and str(jm).lower() == "wal"


def test_checkpoint_wal_rejects_injected_mode(temp_db_path):
    db = Database(temp_db_path)
    db.initialize()
    with pytest.raises(ValueError):
        db._checkpoint_wal("TRUNCATE);ATTACH DATABASE 'x' AS z")


def test_checkpoint_wal_passive_succeeds(temp_db_path):
    db = Database(temp_db_path)
    db.initialize()
    db._checkpoint_wal("PASSIVE")
