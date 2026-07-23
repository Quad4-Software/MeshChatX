# SPDX-License-Identifier: 0BSD

"""Compat for LXST Profiles call modes on Android 0.4.x vs duplex builds."""

from types import SimpleNamespace

from meshchatx.src.backend import lxst_profiles_compat as lxst_modes


def test_legacy_profiles_without_modes_falls_back_to_full_duplex():
    legacy = SimpleNamespace(
        BANDWIDTH_LOW=0x30,
        # No MODE_* or available_modes on Android lxst 0.4.8
    )
    assert lxst_modes.duplex_modes_supported(legacy) is False
    assert lxst_modes.available_modes(legacy) == [lxst_modes.MODE_FULL_DUPLEX]
    assert lxst_modes.default_mode(legacy) == lxst_modes.MODE_FULL_DUPLEX
    assert lxst_modes.mode_name(lxst_modes.MODE_FULL_DUPLEX, legacy) == "Full Duplex"
    assert lxst_modes.mode_abbreviation(lxst_modes.MODE_HALF_DUPLEX, legacy) == "HDX"


def test_native_profiles_modes_are_forwarded():
    native = SimpleNamespace(
        MODE_FULL_DUPLEX=1,
        MODE_HALF_DUPLEX=2,
        DEFAULT_MODE=1,
        available_modes=lambda: [1, 2],
        mode_name=lambda mid: f"mode-{mid}",
        mode_abbrevation=lambda mid: f"m{mid}",
    )
    assert lxst_modes.duplex_modes_supported(native) is True
    assert lxst_modes.available_modes(native) == [1, 2]
    assert lxst_modes.mode_name(2, native) == "mode-2"
    assert lxst_modes.mode_abbreviation(1, native) == "m1"


def test_telephone_manager_resolves_modes_on_legacy_profiles(monkeypatch):
    from unittest.mock import MagicMock

    from meshchatx.src.backend.telephone_manager import TelephoneManager

    legacy = SimpleNamespace()
    monkeypatch.setattr(
        "meshchatx.src.backend.lxst_profiles_compat.import_profiles",
        lambda: legacy,
    )
    tm = TelephoneManager(identity=MagicMock())
    assert tm.resolve_call_mode_id(None) == lxst_modes.MODE_FULL_DUPLEX
    assert (
        tm.resolve_call_mode_id(lxst_modes.MODE_HALF_DUPLEX)
        == lxst_modes.MODE_FULL_DUPLEX
    )
    assert tm.is_half_duplex() is False
