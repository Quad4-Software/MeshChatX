# SPDX-License-Identifier: 0BSD

"""Half-duplex mode and PTT squelch controls for LXST telephony."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from LXST.Primitives.Telephony import Profiles

from meshchatx.src.backend.telephone_manager import TelephoneManager


def _manager_with_call(mode=Profiles.MODE_HALF_DUPLEX):
    tm = TelephoneManager(identity=MagicMock())
    packetizer = SimpleNamespace(squelched=mode == Profiles.MODE_HALF_DUPLEX)
    active_call = SimpleNamespace(call_mode=mode, packetizer=packetizer)
    telephone = MagicMock()
    telephone.active_call = active_call
    telephone.call_status = 6
    telephone.active_mode = mode
    tm.telephone = telephone
    tm.preferred_mode_id = mode
    return tm, telephone, packetizer


def test_resolve_call_mode_defaults_to_full_duplex():
    tm = TelephoneManager(identity=MagicMock())
    assert tm.resolve_call_mode_id(None) == Profiles.MODE_FULL_DUPLEX
    assert tm.resolve_call_mode_id(999) == Profiles.MODE_FULL_DUPLEX
    assert (
        tm.resolve_call_mode_id(Profiles.MODE_HALF_DUPLEX) == Profiles.MODE_HALF_DUPLEX
    )


def test_switch_mode_half_duplex_squelches_and_clears_ptt():
    tm, telephone, _packetizer = _manager_with_call(Profiles.MODE_FULL_DUPLEX)
    tm.ptt_active = True

    resolved = tm.switch_mode(Profiles.MODE_HALF_DUPLEX)

    assert resolved == Profiles.MODE_HALF_DUPLEX
    telephone.switch_mode.assert_called_once_with(Profiles.MODE_HALF_DUPLEX)
    telephone.squelch_transmit.assert_called_once_with(True)
    assert tm.ptt_active is False
    assert tm.is_half_duplex() is True


def test_set_ptt_active_unsquelches_only_in_half_duplex():
    tm, telephone, packetizer = _manager_with_call(Profiles.MODE_HALF_DUPLEX)

    assert tm.set_ptt_active(True) is True
    telephone.unsquelch_transmit.assert_called_once_with(True)
    assert tm.ptt_active is True

    packetizer.squelched = False
    assert tm.is_transmit_squelched() is False

    assert tm.set_ptt_active(False) is True
    telephone.squelch_transmit.assert_called_once_with(True)
    assert tm.ptt_active is False


def test_set_ptt_active_rejected_in_full_duplex():
    tm, telephone, _packetizer = _manager_with_call(Profiles.MODE_FULL_DUPLEX)

    assert tm.set_ptt_active(True) is False
    telephone.unsquelch_transmit.assert_not_called()
    assert tm.ptt_active is False


def test_call_end_resets_mute_and_ptt_state():
    tm, _telephone, _packetizer = _manager_with_call(Profiles.MODE_HALF_DUPLEX)
    tm.transmit_muted = True
    tm.receive_muted = True
    tm.ptt_active = True
    tm.call_stats = {"link": object()}

    tm.on_telephone_call_ended(MagicMock())

    assert tm.transmit_muted is False
    assert tm.receive_muted is False
    assert tm.ptt_active is False
    assert tm.call_stats == {}
