# SPDX-License-Identifier: 0BSD

"""LXST Profiles helpers that work across LXST versions.

Android previously vendored lxst 0.4.8 without call-mode helpers
(available_modes, MODE_FULL_DUPLEX, MODE_HALF_DUPLEX). Desktop and current
Android builds ship 0.5.0+. MeshChatX keeps this shim so identity setup never
crashes when an older Profiles class is present.
"""

from __future__ import annotations

# Match LXST 0.5+ Profiles constants when the installed package lacks them.
MODE_FULL_DUPLEX = 0x01
MODE_HALF_DUPLEX = 0x02
DEFAULT_MODE = MODE_FULL_DUPLEX

_MODE_NAMES = {
    MODE_FULL_DUPLEX: "Full Duplex",
    MODE_HALF_DUPLEX: "Half Duplex",
}
_MODE_ABBREVS = {
    MODE_FULL_DUPLEX: "FDX",
    MODE_HALF_DUPLEX: "HDX",
}


def import_profiles():
    """Import LXST Profiles, or raise ImportError if LXST is unavailable."""
    from LXST.Primitives.Telephony import Profiles

    return Profiles


def duplex_modes_supported(profiles=None) -> bool:
    """True when the installed LXST Profiles exposes call-mode helpers."""
    Profiles = profiles if profiles is not None else import_profiles()
    return callable(getattr(Profiles, "available_modes", None))


def mode_full_duplex(profiles=None) -> int:
    Profiles = profiles if profiles is not None else import_profiles()
    return int(getattr(Profiles, "MODE_FULL_DUPLEX", MODE_FULL_DUPLEX))


def mode_half_duplex(profiles=None) -> int:
    Profiles = profiles if profiles is not None else import_profiles()
    return int(getattr(Profiles, "MODE_HALF_DUPLEX", MODE_HALF_DUPLEX))


def default_mode(profiles=None) -> int:
    Profiles = profiles if profiles is not None else import_profiles()
    return int(getattr(Profiles, "DEFAULT_MODE", DEFAULT_MODE))


def available_modes(profiles=None) -> list[int]:
    """Return duplex mode ids supported by the installed LXST build."""
    Profiles = profiles if profiles is not None else import_profiles()
    native = getattr(Profiles, "available_modes", None)
    if callable(native):
        return list(native())
    # Pre-duplex LXST: full duplex only. Half duplex needs switch_mode / squelch.
    return [mode_full_duplex(Profiles)]


def mode_name(mode_id, profiles=None) -> str:
    Profiles = profiles if profiles is not None else import_profiles()
    native = getattr(Profiles, "mode_name", None)
    if callable(native):
        return str(native(mode_id))
    return _MODE_NAMES.get(int(mode_id), "Default")


def mode_abbreviation(mode_id, profiles=None) -> str:
    Profiles = profiles if profiles is not None else import_profiles()
    native = getattr(Profiles, "mode_abbrevation", None)
    if callable(native):
        return str(native(mode_id))
    return _MODE_ABBREVS.get(int(mode_id), "DFLT")
