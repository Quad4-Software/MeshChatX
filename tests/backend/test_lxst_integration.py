"""Integration-oriented tests for real LXST telephony classes.

These tests intentionally use LXST's real ``Telephone`` implementation while stubbing
RNS/network/audio backends, so we validate LXST behavior without requiring hardware.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("LXST")

from LXST.Primitives import Telephony as LXSTTelephony

from meshchatx.src.backend.telephone_manager import TelephoneManager


class _DummyThread:
    def __init__(self, target=None, daemon=None):
        self.target = target
        self.daemon = daemon

    def start(self):
        return None


class _DummyDestination:
    IN = 0
    OUT = 1
    SINGLE = 2
    PROVE_NONE = 3

    def __init__(self, identity, *_args, **_kwargs):
        self.identity = identity
        self.hash = b"\xaa" * 16

    def set_proof_strategy(self, *_args, **_kwargs):
        return None

    def set_link_established_callback(self, *_args, **_kwargs):
        return None

    def announce(self, *_args, **_kwargs):
        return None


def _install_lxst_stubs(monkeypatch):
    monkeypatch.setattr(LXSTTelephony.RNS, "log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(LXSTTelephony.RNS, "Destination", _DummyDestination)
    monkeypatch.setattr(
        LXSTTelephony.RNS,
        "Transport",
        SimpleNamespace(
            deregister_destination=MagicMock(),
            has_path=lambda *_args, **_kwargs: True,
            request_path=lambda *_args, **_kwargs: None,
        ),
    )
    monkeypatch.setattr(LXSTTelephony.threading, "Thread", _DummyThread)


def _mock_identity():
    return SimpleNamespace(hash=b"\x01" * 16)


def test_lxst_telephone_lifecycle_and_timeouts(monkeypatch):
    _install_lxst_stubs(monkeypatch)
    identity = _mock_identity()

    telephone = LXSTTelephony.Telephone(identity)
    assert telephone.call_status == LXSTTelephony.Signalling.STATUS_AVAILABLE
    assert telephone.destination is not None

    telephone.set_connect_timeout(37)
    assert telephone.establishment_timeout == 37

    telephone.set_busy_tone_time(0)
    assert telephone.busy_tone_seconds == 0

    telephone.teardown()
    assert telephone.destination is None


def test_lxst_switch_profile_updates_codec_and_frame_time(monkeypatch):
    _install_lxst_stubs(monkeypatch)
    identity = _mock_identity()

    class _FakeMixer:
        def __init__(self, target_frame_ms=None, gain=0.0):
            self.target_frame_ms = target_frame_ms
            self.gain = gain
            self.muted = False

        def stop(self):
            return None

        def start(self):
            return None

        def mute(self, muted):
            self.muted = muted

        def unmute(self, unmuted):
            self.muted = not unmuted

    class _FakeLineSource:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def stop(self):
            return None

        def start(self):
            return None

    class _FakePipeline:
        def __init__(self, source=None, codec=None, sink=None):
            self.source = source
            self.codec = codec
            self.sink = sink

        def stop(self):
            return None

        def start(self):
            return None

    monkeypatch.setattr(LXSTTelephony, "Mixer", _FakeMixer)
    monkeypatch.setattr(LXSTTelephony, "LineSource", _FakeLineSource)
    monkeypatch.setattr(LXSTTelephony, "Pipeline", _FakePipeline)

    telephone = LXSTTelephony.Telephone(identity)
    telephone.call_status = LXSTTelephony.Signalling.STATUS_ESTABLISHED
    telephone.active_call = SimpleNamespace(
        profile=LXSTTelephony.Profiles.QUALITY_MEDIUM,
        filters=[],
        packetizer=MagicMock(),
    )
    telephone.transmit_mixer = _FakeMixer(target_frame_ms=60, gain=0.0)
    telephone.audio_input = _FakeLineSource()
    telephone.transmit_pipeline = _FakePipeline()

    telephone.switch_profile(LXSTTelephony.Profiles.QUALITY_HIGH, from_signalling=True)

    assert telephone.active_call.profile == LXSTTelephony.Profiles.QUALITY_HIGH
    assert telephone.target_frame_time_ms == LXSTTelephony.Profiles.get_frame_time(
        LXSTTelephony.Profiles.QUALITY_HIGH
    )
    assert telephone.transmit_codec is not None

    telephone.active_call = None
    telephone.teardown()


def test_telephone_manager_init_uses_real_lxst_telephone(monkeypatch, tmp_path):
    _install_lxst_stubs(monkeypatch)
    cfg = MagicMock()
    cfg.telephone_audio_profile_id.get.return_value = LXSTTelephony.Profiles.QUALITY_MAX
    tm = TelephoneManager(
        identity=_mock_identity(),
        config_manager=cfg,
        storage_dir=str(tmp_path),
    )

    tm.init_telephone()

    assert isinstance(tm.telephone, LXSTTelephony.Telephone)
    assert tm.telephone.establishment_timeout == 30
    assert tm.telephone.busy_tone_seconds == 0

    tm.teardown()
