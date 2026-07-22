# SPDX-License-Identifier: 0BSD

"""Telephone audio profile selection and Codec2 readiness."""

from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.telephone_manager import TelephoneManager

pytest.importorskip("LXST")
from LXST.Primitives.Telephony import Profiles


@pytest.fixture
def tm():
    manager = TelephoneManager(identity=MagicMock())
    manager.telephone = MagicMock()
    manager.telephone.busy = False
    manager.telephone.call_status = 3
    manager.telephone.active_call = None
    manager._path_poll_interval_s = 0.005
    manager._path_retry_interval_s = 0.01
    manager._status_poll_interval_s = 0.01
    return manager


def test_resolve_invalid_profile_falls_back_to_default(tm):
    assert tm.resolve_audio_profile_id(2) == Profiles.DEFAULT_PROFILE
    assert tm.resolve_audio_profile_id(999) == Profiles.DEFAULT_PROFILE


def test_resolve_codec2_profile_when_available(tm):
    with patch.object(TelephoneManager, "codec2_available", return_value=True):
        assert (
            tm.resolve_audio_profile_id(Profiles.BANDWIDTH_LOW)
            == Profiles.BANDWIDTH_LOW
        )


def test_resolve_codec2_profile_falls_back_when_unavailable(tm):
    with patch.object(TelephoneManager, "codec2_available", return_value=False):
        assert (
            tm.resolve_audio_profile_id(Profiles.BANDWIDTH_ULTRA_LOW)
            == Profiles.DEFAULT_PROFILE
        )


def test_apply_preferred_profile_stores_without_idle_switch(tm):
    tm.telephone.call_status = 3
    tm.telephone.active_call = None
    resolved = tm.apply_preferred_profile(Profiles.QUALITY_HIGH)
    assert resolved == Profiles.QUALITY_HIGH
    assert tm.preferred_profile_id == Profiles.QUALITY_HIGH
    tm.telephone.switch_profile.assert_not_called()


def test_apply_preferred_profile_switches_when_established(tm):
    tm.telephone.call_status = 6
    tm.telephone.active_call = MagicMock()
    tm.apply_preferred_profile(Profiles.QUALITY_HIGH)
    tm.telephone.switch_profile.assert_called_once_with(Profiles.QUALITY_HIGH)


@pytest.mark.asyncio
async def test_initiate_passes_preferred_profile_to_lxst_call(tm):
    destination_hash = bytes.fromhex("aa" * 16)
    tm.preferred_profile_id = Profiles.BANDWIDTH_LOW
    seen = {}

    def capture_call(identity, profile=None, mode=None):
        seen["identity"] = identity
        seen["profile"] = profile
        seen["mode"] = mode
        tm.telephone.call_status = 0

    tm.telephone.call.side_effect = capture_call

    with (
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Identity.recall",
            return_value=MagicMock(),
        ),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Transport.has_path",
            return_value=True,
        ),
        patch.object(TelephoneManager, "codec2_available", return_value=True),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Destination",
        ) as dest_cls,
    ):
        dest_cls.return_value.hash = destination_hash
        await tm.initiate(destination_hash, timeout_seconds=1)

    assert seen["profile"] == Profiles.BANDWIDTH_LOW
    assert seen["mode"] == Profiles.MODE_FULL_DUPLEX


def test_init_telephone_stores_preferred_profile_not_idle_switch(tmp_path):
    cfg = MagicMock()
    cfg.telephone_enabled.get.return_value = True
    cfg.telephone_audio_profile_id.get.return_value = Profiles.QUALITY_MAX

    with patch(
        "meshchatx.src.backend.telephone_manager.Telephone",
    ) as telephone_cls:
        telephone = telephone_cls.return_value
        manager = TelephoneManager(
            identity=MagicMock(),
            config_manager=cfg,
            storage_dir=str(tmp_path),
        )
        manager.init_telephone()
        assert manager.preferred_profile_id == Profiles.QUALITY_MAX
        telephone.switch_profile.assert_not_called()


def test_pycodec2_encode_decode_for_lxst_codec2_profiles():
    """Live validation that Codec2 profiles used on Android calls actually work."""
    import numpy as np
    from LXST.Codecs import Codec2

    assert TelephoneManager.codec2_available() is True
    for pid in (
        Profiles.BANDWIDTH_ULTRA_LOW,
        Profiles.BANDWIDTH_VERY_LOW,
        Profiles.BANDWIDTH_LOW,
    ):
        codec = Profiles.get_codec(pid)
        assert isinstance(codec, Codec2)
        spf = codec.c2.samples_per_frame()
        pcm = (0.1 * np.sin(np.linspace(0, 8 * np.pi, spf))).astype(np.float32)
        pcm_i16 = (pcm * 32767).astype(np.int16)
        encoded = codec.c2.encode(pcm_i16)
        decoded = codec.c2.decode(encoded)
        assert len(encoded) == codec.c2.bytes_per_frame()
        assert len(decoded) == spf
