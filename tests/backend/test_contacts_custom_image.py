import os

import pytest

from meshchatx.src.backend.database.contacts import ContactsDAO
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


@pytest.fixture
def db_provider():
    db_path = "test_contacts.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    provider = DatabaseProvider(db_path)
    schema = DatabaseSchema(provider)
    schema.initialize()

    yield provider

    provider.close()
    if os.path.exists(db_path):
        os.remove(db_path)


def test_contacts_with_custom_image(db_provider):
    contacts_dao = ContactsDAO(db_provider)

    # Test adding contact with image
    contacts_dao.add_contact(
        name="Test Contact",
        remote_identity_hash="abc123def456",
        custom_image="data:image/png;base64,mockdata",
    )

    contact = contacts_dao.get_contact_by_identity_hash("abc123def456")
    assert contact is not None
    assert contact["name"] == "Test Contact"
    assert contact["custom_image"] == "data:image/png;base64,mockdata"

    # Test updating contact image
    contacts_dao.update_contact(
        contact["id"],
        custom_image="data:image/png;base64,updateddata",
    )

    contact = contacts_dao.get_contact(contact["id"])
    assert contact["custom_image"] == "data:image/png;base64,updateddata"

    # Test removing contact image
    contacts_dao.update_contact(contact["id"], clear_image=True)

    contact = contacts_dao.get_contact(contact["id"])
    assert contact["custom_image"] is None


def test_contacts_upsert_image(db_provider):
    contacts_dao = ContactsDAO(db_provider)

    # Initial add
    contacts_dao.add_contact("User", "hash1", custom_image="img1")
    contact = contacts_dao.get_contact_by_identity_hash("hash1")
    assert contact["custom_image"] == "img1"

    # Upsert with different image
    contacts_dao.add_contact("User", "hash1", custom_image="img2")
    contact = contacts_dao.get_contact_by_identity_hash("hash1")
    assert contact["custom_image"] == "img2"
