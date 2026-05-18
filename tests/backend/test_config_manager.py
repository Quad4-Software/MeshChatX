# SPDX-License-Identifier: 0BSD

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

    config.lxmf_inbound_stamp_cost.set(0)
    assert config.lxmf_inbound_stamp_cost.get() == 0

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

    # Test Contacts Only (defaults to True for security)
    assert config.telephone_allow_calls_from_contacts_only.get() is True
    config.telephone_allow_calls_from_contacts_only.set(False)
    assert config.telephone_allow_calls_from_contacts_only.get() is False

    # Test Call Recording
    assert config.call_recording_enabled.get() is False
    config.call_recording_enabled.set(True)
    assert config.call_recording_enabled.get() is True

    # Test Telephone Enabled (defaults to True)
    assert config.telephone_enabled.get() is True
    config.telephone_enabled.set(False)
    assert config.telephone_enabled.get() is False


def test_all_telephony_settings_persist(db):
    """Verify every telephone/call setting survives a manager reload (simulated restart)."""
    config = ConfigManager(db)

    # Set all telephone-related settings
    config.telephone_enabled.set(False)
    config.do_not_disturb_enabled.set(True)
    config.telephone_allow_calls_from_contacts_only.set(False)
    config.telephone_announce_enabled.set(True)
    config.telephone_audio_profile_id.set(5)
    config.telephone_web_audio_enabled.set(True)
    config.telephone_web_audio_allow_fallback.set(False)
    config.call_recording_enabled.set(True)
    config.telephone_tone_generator_enabled.set(False)
    config.telephone_tone_generator_volume.set(80)

    # Voicemail settings
    config.voicemail_enabled.set(True)
    config.voicemail_auto_answer_delay_seconds.set(15)
    config.voicemail_max_recording_seconds.set(120)
    config.voicemail_tts_speed.set(150)
    config.voicemail_tts_pitch.set(50)
    config.voicemail_tts_word_gap.set(10)
    config.voicemail_tts_voice.set("de-de+f1")

    # Ringtone settings
    config.custom_ringtone_enabled.set(True)
    config.ringtone_volume.set(75)
    config.ringtone_preferred_id.set(3)

    # Desktop / misc
    config.desktop_open_calls_in_separate_window.set(True)

    # Simulate restart: new ConfigManager on same DB
    config2 = ConfigManager(db)

    # Assert all values persisted

    # Telephone base
    assert config2.telephone_enabled.get() is False
    assert config2.do_not_disturb_enabled.get() is True
    assert config2.telephone_allow_calls_from_contacts_only.get() is False
    assert config2.telephone_announce_enabled.get() is True
    assert config2.telephone_audio_profile_id.get() == 5
    assert config2.telephone_web_audio_enabled.get() is True
    assert config2.telephone_web_audio_allow_fallback.get() is False
    assert config2.call_recording_enabled.get() is True
    assert config2.telephone_tone_generator_enabled.get() is False
    assert config2.telephone_tone_generator_volume.get() == 80

    # Voicemail
    assert config2.voicemail_enabled.get() is True
    assert config2.voicemail_auto_answer_delay_seconds.get() == 15
    assert config2.voicemail_max_recording_seconds.get() == 120
    assert config2.voicemail_tts_speed.get() == 150
    assert config2.voicemail_tts_pitch.get() == 50
    assert config2.voicemail_tts_word_gap.get() == 10
    assert config2.voicemail_tts_voice.get() == "de-de+f1"

    # Ringtone
    assert config2.custom_ringtone_enabled.get() is True
    assert config2.ringtone_volume.get() == 75
    assert config2.ringtone_preferred_id.get() == 3

    # Desktop
    assert config2.desktop_open_calls_in_separate_window.get() is True


def test_auto_propagation_config(db):
    config = ConfigManager(db)
    assert config.lxmf_preferred_propagation_node_auto_select.get() is False
    config.lxmf_preferred_propagation_node_auto_select.set(True)
    assert config.lxmf_preferred_propagation_node_auto_select.get() is True
