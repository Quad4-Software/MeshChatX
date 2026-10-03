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
    assert config.map_data_announce_enabled.get() is False
    assert config.map_offline_enabled.get() is True
    assert config.map_coordinate_format.get() == "wgs84"


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


def test_map_announce_interval_migrates_legacy_default(db):
    db.config.set("map_data_announce_interval", "900")
    config = ConfigManager(db)
    assert config.map_data_announce_interval.get() == 21600

    config.map_data_announce_interval.set(900)
    reloaded = ConfigManager(db)
    assert reloaded.map_data_announce_interval.get() == 900


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

    # Default audio profile must match LXST DEFAULT_PROFILE (64)
    assert config.telephone_audio_profile_id.get() == 64
    config.telephone_audio_profile_id.set(48)
    assert config.telephone_audio_profile_id.get() == 48

    # Legacy invalid profile 2 is migrated to 64 on reload
    config.telephone_audio_profile_id.set(2)
    config3 = ConfigManager(db)
    assert config3.telephone_audio_profile_id.get() == 64

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
    config.telephone_audio_profile_id.set(96)
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

    config.notification_sound_enabled.set(True)
    config.notification_sound_preferred_id.set(2)
    config.notification_sound_volume.set(55)

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
    assert config2.telephone_audio_profile_id.get() == 96
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

    # Notification sound
    assert config2.notification_sound_enabled.get() is True
    assert config2.notification_sound_preferred_id.get() == 2
    assert config2.notification_sound_volume.get() == 55

    # Desktop
    assert config2.desktop_open_calls_in_separate_window.get() is True


def test_auto_propagation_config(db):
    config = ConfigManager(db)
    assert config.lxmf_preferred_propagation_node_auto_select.get() is False
    config.lxmf_preferred_propagation_node_auto_select.set(True)
    assert config.lxmf_preferred_propagation_node_auto_select.get() is True


def test_all_registered_config_keys_are_handled_in_update_config():
    """Every registered config key must reach storage via update_config.

    StringConfig/BoolConfig/IntConfig/FloatConfig keys reach storage either
    through an explicit `in data` handler or the generic catch-all. Keys in
    GENERIC_CONFIG_DENY bypass the generic pass, so a denylisted key with no
    explicit handler and no dedicated route is silently dropped: flag those.
    """
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    cm_src = (repo / "meshchatx/src/backend/config_manager.py").read_text()
    app_src = (repo / "meshchatx/meshchat.py").read_text()

    registered = set(
        re.findall(
            r'(?:StringConfig|BoolConfig|IntConfig|FloatConfig)\(\s*self\s*,\s*["\']([^"\']+)["\']',
            cm_src,
            re.S,
        )
    )
    # Keys set through dedicated routes/system paths, never via update_config.
    EXEMPT = {
        "lxmf_address_hash",
        "lxst_address_hash",
        "last_announced_at",
        "map_offline_path",
        "ringtone_filename",
        # Written by the auth subsystem during login/setup, never client-settable.
        "auth_enabled",
        "auth_password_hash",
        "auth_session_secret",
        "auth_session_epoch",
        # CSP hardening knobs set by server admins, not the app PATCH.
        "csp_extra_frame_src",
        "csp_extra_img_src",
        "csp_extra_script_src",
        "csp_extra_style_src",
    }
    # Denylist parsed from meshchat.py so the test follows the source of truth.
    deny_start = app_src.index("GENERIC_CONFIG_DENY = frozenset(")
    deny_end = app_src.index("\n)", deny_start)
    denylisted = set(
        re.findall(r'"([a-z_]+)"', app_src[deny_start:deny_end])
    )

    # Extract all keys checked with `in data` inside update_config.
    uc_start = app_src.index("async def update_config(self, data):")
    uc_tail = app_src[uc_start:]
    m = re.search(r"\n    (?:async )?def \w+\(", uc_tail[10:])
    uc_end = uc_start + 10 + m.start() if m else len(app_src)
    uc_body = app_src[uc_start:uc_end]
    handled = set(re.findall(r'["\']([a-z_]+)["\']\s+in\s+data', uc_body))

    # Non-denylisted keys are covered by the generic pass even without an
    # explicit handler. Denylisted keys need an explicit handler or an EXEMPT
    # entry - otherwise they can never be persisted at all.
    uncovered = registered - handled - EXEMPT
    dead = uncovered & denylisted
    assert not dead, (
        f"Config keys denylisted from the generic update_config pass with no "
        f"explicit handler and no dedicated route - can never persist: {sorted(dead)}"
    )

    # The denylist must not contain typos - every entry must be a real
    # registered config key.
    unknown_deny = denylisted - registered
    assert not unknown_deny, (
        f"GENERIC_CONFIG_DENY entries that are not registered config keys: "
        f"{sorted(unknown_deny)}"
    )

    # SERIALIZE_CONFIG_DENY entries likewise must be real registered keys.
    ser_start = app_src.index("SERIALIZE_CONFIG_DENY = frozenset(")
    ser_end = app_src.index("\n)", ser_start)
    ser_denylisted = set(
        re.findall(r'"([a-z_]+)"', app_src[ser_start:ser_end])
    )
    unknown_ser = ser_denylisted - registered
    assert not unknown_ser, (
        f"SERIALIZE_CONFIG_DENY entries that are not registered config keys: "
        f"{sorted(unknown_ser)}"
    )


def test_generic_config_pass_sets_and_denies(db):
    """_apply_generic_config_fields stores unhandled registered keys.

    Applies type coercion and refuses denylisted keys.
    """
    from meshchatx.meshchat import (
        GENERIC_CONFIG_DENY,
        _apply_generic_config_fields,
        _TrackedConfigData,
    )

    config = ConfigManager(db)

    data = _TrackedConfigData(
        {
            "ui_glass_enabled": False,
            "ui_transparency": "42",
            "ui_font_family": "inter",
            "auth_password_hash": "should-never-stick",
            "nonexistent_key": "ignored",
        }
    )
    _apply_generic_config_fields(config, data)

    assert config.ui_glass_enabled.get() is False
    assert config.ui_transparency.get() == 42
    assert config.ui_font_family.get() == "inter"
    # Denylisted key refused even though it was never probed by a handler.
    assert config.auth_password_hash.get() != "should-never-stick"
    assert "auth_password_hash" in GENERIC_CONFIG_DENY
    # Unknown payload keys are ignored.
    assert not hasattr(config, "nonexistent_key")


def test_font_family_whitelist_matches_frontend_bundled_fonts():
    """The ui_font_family whitelist must cover every bundled font.

    update_config must accept every key in BUNDLED_FONTS plus 'system' and
    'custom', or font selection silently resets.
    """
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    app_src = (repo / "meshchatx/meshchat.py").read_text()

    start = app_src.index('if "ui_font_family" in data:')
    end = app_src.index("self.config.ui_font_family.set", start)
    backend_fonts = set(re.findall(r'"([a-z\-]+)"', app_src[start:end]))

    fe_src = (repo / "meshchatx/src/frontend/js/fontLoader.js").read_text()
    bundled = set(re.findall(r"^\s+\"?([a-z\-]+)\"?:\s*'", fe_src, re.M))

    expected = bundled | {"system", "custom"}
    assert backend_fonts == expected, (
        f"backend whitelist {sorted(backend_fonts)} != frontend fonts {sorted(expected)}"
    )
