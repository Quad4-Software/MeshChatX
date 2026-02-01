import pytest
from unittest.mock import MagicMock
from meshchatx.src.backend.database.misc import MiscDAO


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def misc_dao(mock_provider):
    return MiscDAO(mock_provider)


def test_add_blocked_destination(misc_dao, mock_provider):
    misc_dao.add_blocked_destination("dest1")
    args, _ = mock_provider.execute.call_args
    assert "INSERT OR IGNORE INTO blocked_destinations" in args[0]
    assert args[1][0] == "dest1"


def test_is_destination_blocked(misc_dao, mock_provider):
    mock_provider.fetchone.return_value = {"1": 1}
    assert misc_dao.is_destination_blocked("dest1") is True

    mock_provider.fetchone.return_value = None
    assert misc_dao.is_destination_blocked("dest2") is False


def test_add_spam_keyword(misc_dao, mock_provider):
    misc_dao.add_spam_keyword("buy now")
    args, _ = mock_provider.execute.call_args
    assert "INSERT OR IGNORE INTO spam_keywords" in args[0]
    assert args[1][0] == "buy now"


def test_check_spam_keywords(misc_dao, mock_provider):
    mock_provider.fetchall.return_value = [{"keyword": "spam"}]
    assert misc_dao.check_spam_keywords("Hello", "This is spam") is True
    assert misc_dao.check_spam_keywords("Hello", "This is fine") is False


def test_update_lxmf_user_icon(misc_dao, mock_provider):
    misc_dao.update_lxmf_user_icon("dest1", "icon", "#fff", "#000")
    args, _ = mock_provider.execute.call_args
    assert "INSERT INTO lxmf_user_icons" in args[0]
    assert "dest1" in args[1]
    assert "icon" in args[1]


def test_get_user_icons(misc_dao, mock_provider):
    misc_dao.get_user_icons(["d1", "d2"])
    args, _ = mock_provider.fetchall.call_args
    assert "IN (?, ?)" in args[0]
    assert args[1] == ("d1", "d2")
