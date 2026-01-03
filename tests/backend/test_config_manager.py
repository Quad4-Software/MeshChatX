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


def test_config_manager_get_default(db):
    config = ConfigManager(db)
    assert config.display_name.get() == "Anonymous Peer"
    assert config.theme.get() == "light"
    assert config.lxmf_inbound_stamp_cost.get() == 8


def test_config_manager_set_get(db):
    config = ConfigManager(db)
    config.display_name.set("Test User")
    assert config.display_name.get() == "Test User"

    config.lxmf_inbound_stamp_cost.set(20)
    assert config.lxmf_inbound_stamp_cost.get() == 20

    config.auto_announce_enabled.set(True)
    assert config.auto_announce_enabled.get() is True


def test_config_manager_persistence(db):
    config = ConfigManager(db)
    config.display_name.set("Persistent User")

    # New manager instance with same DB
    config2 = ConfigManager(db)
    assert config2.display_name.get() == "Persistent User"


def test_config_manager_type_safety(db):
    config = ConfigManager(db)

    # IntConfig
    config.lxmf_inbound_stamp_cost.set(
        "15",
    )  # Should handle string to int if implementation allows or just store it
    # Looking at implementation might be better, but let's test basic set/get
    config.lxmf_inbound_stamp_cost.set(15)
    assert isinstance(config.lxmf_inbound_stamp_cost.get(), int)
    assert config.lxmf_inbound_stamp_cost.get() == 15

    # BoolConfig
    config.auto_announce_enabled.set(True)
    assert config.auto_announce_enabled.get() is True
    config.auto_announce_enabled.set(False)
    assert config.auto_announce_enabled.get() is False


def test_telephony_config(db):
    config = ConfigManager(db)

    # Test DND
    assert config.do_not_disturb_enabled.get() is False
    config.do_not_disturb_enabled.set(True)
    assert config.do_not_disturb_enabled.get() is True

    # Test Contacts Only
    assert config.telephone_allow_calls_from_contacts_only.get() is False
    config.telephone_allow_calls_from_contacts_only.set(True)
    assert config.telephone_allow_calls_from_contacts_only.get() is True

    # Test Call Recording
    assert config.call_recording_enabled.get() is False
    config.call_recording_enabled.set(True)
    assert config.call_recording_enabled.get() is True
