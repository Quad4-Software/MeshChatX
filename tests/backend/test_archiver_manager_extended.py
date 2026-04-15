from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.archiver_manager import ArchiverManager


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.provider = MagicMock()
    db.misc = MagicMock()
    return db


def test_archive_page_new(mock_db):
    manager = ArchiverManager(mock_db)
    mock_db.provider.fetchone.side_effect = [None, {"total_size": 100}]
    mock_db.misc.get_archived_page_versions.return_value = []

    manager.archive_page("dest", "/path", "content")

    mock_db.misc.archive_page.assert_called_once()
    args, _ = mock_db.misc.archive_page.call_args
    assert args[0] == "dest"
    assert args[1] == "/path"
    assert args[2] == "content"


def test_archive_page_exists(mock_db):
    manager = ArchiverManager(mock_db)
    mock_db.provider.fetchone.return_value = {"id": 1}

    manager.archive_page("dest", "/path", "content")
    mock_db.misc.archive_page.assert_not_called()


def test_archive_page_enforce_max_versions(mock_db):
    manager = ArchiverManager(mock_db)
    mock_db.provider.fetchone.side_effect = [None, {"total_size": 100}]
    # 6 versions, max is 5
    mock_db.misc.get_archived_page_versions.return_value = [
        {"id": 1},
        {"id": 2},
        {"id": 3},
        {"id": 4},
        {"id": 5},
        {"id": 6},
    ]

    manager.archive_page("dest", "/path", "content", max_versions=5)

    # Should delete the 6th version (index 5)
    mock_db.provider.execute.assert_any_call(
        "DELETE FROM archived_pages WHERE id = ?",
        (6,),
    )


def test_archive_page_enforce_storage_limit(mock_db):
    manager = ArchiverManager(mock_db)
    mock_db.provider.fetchone.side_effect = [
        None,  # existing check
        {"total_size": 2 * 1024 * 1024 * 1024},  # total size (2GB)
        {"id": 10, "size": 1 * 1024 * 1024 * 1024},  # oldest
    ]
    mock_db.misc.get_archived_page_versions.return_value = []

    # max storage 1GB
    manager.archive_page("dest", "/path", "content", max_storage_gb=1)

    mock_db.provider.execute.assert_any_call(
        "DELETE FROM archived_pages WHERE id = ?",
        (10,),
    )
