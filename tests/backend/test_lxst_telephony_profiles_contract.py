"""
Contract tests for LXST Telephony Profiles used by /api/v1/telephone/audio-profiles and TelephoneManager.

If lxst changes profile IDs, default profile, or display names, these tests fail so UI and config can be updated.
"""

import pytest

pytest.importorskip("LXST")

from LXST.Primitives.Telephony import Profiles

EXPECTED_DEFAULT_PROFILE = 64

EXPECTED_PROFILES = {
    16: "Ultra Low Bandwidth",
    32: "Very Low Bandwidth",
    48: "Low Bandwidth",
    64: "Medium Quality",
    80: "High Quality",
    96: "Super High Quality",
    112: "Ultra Low Latency",
    128: "Low Latency",
}


def test_default_profile_matches_contract():
    assert Profiles.DEFAULT_PROFILE == EXPECTED_DEFAULT_PROFILE


def test_available_profiles_match_contract():
    got = set(Profiles.available_profiles())
    assert got == set(EXPECTED_PROFILES.keys())


def test_profile_names_match_contract():
    for pid, name in EXPECTED_PROFILES.items():
        assert Profiles.profile_name(pid) == name
