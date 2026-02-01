import pytest
from unittest.mock import MagicMock
from meshchatx.src.backend.database.contacts import ContactsDAO


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def contacts_dao(mock_provider):
    return ContactsDAO(mock_provider)


def test_add_contact(contacts_dao, mock_provider):
    contacts_dao.add_contact("Name", "ih", lxmf_address="lx")
    args, _ = mock_provider.execute.call_args
    assert "INSERT INTO contacts" in args[0]
    assert args[1][0] == "Name"
    assert args[1][1] == "ih"
    assert args[1][2] == "lx"


def test_get_contacts_search(contacts_dao, mock_provider):
    contacts_dao.get_contacts(search="john")
    args, _ = mock_provider.fetchall.call_args
    assert "WHERE name LIKE ?" in args[0]
    assert args[1][0] == "%john%"


def test_update_contact(contacts_dao, mock_provider):
    contacts_dao.update_contact(1, name="New Name", clear_image=True)
    args, _ = mock_provider.execute.call_args
    assert "UPDATE contacts SET name = ?, custom_image = NULL" in args[0]
    assert args[1] == ("New Name", 1)


def test_delete_contact(contacts_dao, mock_provider):
    contacts_dao.delete_contact(1)
    mock_provider.execute.assert_called_with("DELETE FROM contacts WHERE id = ?", (1,))


def test_get_contact_by_identity_hash(contacts_dao, mock_provider):
    contacts_dao.get_contact_by_identity_hash("ih")
    mock_provider.fetchone.assert_called_with(
        "SELECT * FROM contacts WHERE remote_identity_hash = ? OR lxmf_address = ? OR lxst_address = ?",
        ("ih", "ih", "ih"),
    )
