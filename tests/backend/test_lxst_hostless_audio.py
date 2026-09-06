# SPDX-License-Identifier: 0BSD

"""Hostless audio oracles and property tests for LXST telephony / web audio.

Oracles (invariants that must always hold):
1. Hostless LineSource/LineSink construct without PulseAudio and never raise on start/stop.
2. WebAudioSource drops oversized frames.
3. When web_audio is required, bridge.config_enabled is True even if config is False.
4. Codec2-unavailable profile resolution never returns a Codec2 bandwidth profile.
5. install_hostless_lxst_audio is idempotent.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

pytest.importorskip("LXST")

from LXST.Primitives.Telephony import Profiles

from meshchatx.src.backend.telephone_manager import TelephoneManager
from meshchatx.src.backend.web_audio_bridge import (
    HostlessAudioSink,
    HostlessAudioSource,
    WebAudioBridge,
    WebAudioSource,
    hostless_lxst_audio_installed,
    install_hostless_lxst_audio,
    reset_hostless_lxst_audio_for_tests,
)

CODEC2_PROFILES = {
    Profiles.BANDWIDTH_ULTRA_LOW,
    Profiles.BANDWIDTH_VERY_LOW,
    Profiles.BANDWIDTH_LOW,
}


@pytest.fixture(autouse=True)
def _reset_hostless():
    reset_hostless_lxst_audio_for_tests()
    yield
    reset_hostless_lxst_audio_for_tests()


# ---------------------------------------------------------------------------
# Oracles: hostless backends
# ---------------------------------------------------------------------------


def test_oracle_hostless_source_matches_linesource_ctor_shape():
    sink = MagicMock()
    sink.can_receive.return_value = True
    src = HostlessAudioSource(
        preferred_device="default",
        target_frame_ms=60,
        codec=None,
        sink=sink,
        filters=[],
        gain=-3.0,
        ease_in=0.1,
        skip=0.05,
    )
    src.start()
    src.stop()
    src.handle_frame(None, None)
    assert src.samplerate == 48000
    assert src.channels == 1
    assert src.can_receive() is True


def test_oracle_hostless_sink_never_needs_pulse():
    sink = HostlessAudioSink(preferred_device=None)
    sink.start()
    sink.handle_frame(np.zeros((160, 1), dtype=np.float32), None)
    sink.enable_low_latency()
    sink.stop()
    assert sink.can_receive() is True


def test_oracle_install_hostless_is_idempotent():
    assert install_hostless_lxst_audio() is True
    assert hostless_lxst_audio_installed() is True
    assert install_hostless_lxst_audio() is True
    from LXST.Primitives import Telephony as T

    assert T.LineSource is HostlessAudioSource
    assert T.LineSink is HostlessAudioSink


def test_oracle_hostless_linesource_constructs_without_soundcard():
    assert install_hostless_lxst_audio() is True
    from LXST.Primitives import Telephony as T

    src = T.LineSource(target_frame_ms=60, codec=None, sink=MagicMock())
    assert isinstance(src, HostlessAudioSource)
    sink = T.LineSink()
    assert isinstance(sink, HostlessAudioSink)


# ---------------------------------------------------------------------------
# Oracles: web audio required / force_enabled
# ---------------------------------------------------------------------------


def test_oracle_force_enabled_overrides_config_false():
    cfg = MagicMock()
    cfg.telephone_web_audio_enabled.get.return_value = False
    bridge = WebAudioBridge(None, cfg, force_enabled=True)
    assert bridge.config_enabled() is True
    assert bridge.allow_fallback() is False
    diag = bridge.get_diagnostics()
    assert diag["force_enabled"] is True
    assert diag["config_enabled"] is True


def test_oracle_force_disabled_follows_config():
    cfg = MagicMock()
    cfg.telephone_web_audio_enabled.get.return_value = False
    bridge = WebAudioBridge(None, cfg, force_enabled=False)
    assert bridge.config_enabled() is False


@given(extra=st.integers(min_value=1, max_value=8192))
@settings(max_examples=20, deadline=None)
def test_oracle_web_audio_drops_oversized_pcm(extra):
    sink = MagicMock()
    sink.can_receive.return_value = True
    src = WebAudioSource(target_frame_ms=60, sink=sink)
    src.push_pcm(b"\x00" * (WebAudioSource.MAX_PCM_BYTES + extra))
    sink.handle_frame.assert_not_called()


# ---------------------------------------------------------------------------
# Oracles: Codec2 profile fallback
# ---------------------------------------------------------------------------


@given(
    pid=st.sampled_from(
        list(Profiles.available_profiles())
        + [0, 1, 2, 99, -1, 255, None, "64", "nope"],
    ),
)
@settings(max_examples=40, deadline=None)
def test_property_resolve_profile_never_returns_codec2_when_unavailable(pid):
    tm = TelephoneManager(identity=MagicMock())
    with patch.object(TelephoneManager, "codec2_available", return_value=False):
        resolved = tm.resolve_audio_profile_id(pid)
    assert resolved in Profiles.available_profiles()
    assert resolved not in CODEC2_PROFILES


def test_oracle_codec2_available_false_on_android_probe_fail():
    tm = TelephoneManager(identity=MagicMock())
    with (
        patch("meshchatx.android_codec2._is_chaquopy_android", return_value=True),
        patch(
            "meshchatx.android_codec2.probe_pycodec2",
            return_value=(False, "missing"),
        ),
    ):
        assert tm.codec2_available() is False


# ---------------------------------------------------------------------------
# Telephone init with web_audio_required
# ---------------------------------------------------------------------------


def test_init_telephone_installs_hostless_when_required(tmp_path):
    cfg = MagicMock()
    cfg.telephone_enabled.get.return_value = True
    cfg.telephone_audio_profile_id.get.return_value = Profiles.DEFAULT_PROFILE
    identity = MagicMock()
    identity.hash = b"\x11" * 16

    with patch("meshchatx.src.backend.telephone_manager.Telephone") as telephone_cls:
        telephone = telephone_cls.return_value
        tm = TelephoneManager(
            identity=identity,
            config_manager=cfg,
            storage_dir=str(tmp_path),
        )
        tm.web_audio_required = True
        tm.init_telephone()
        assert hostless_lxst_audio_installed() is True
        telephone.set_busy_tone_time.assert_called()
        telephone.set_connect_timeout.assert_called()


def test_init_telephone_skips_hostless_when_not_required(tmp_path):
    cfg = MagicMock()
    cfg.telephone_enabled.get.return_value = True
    cfg.telephone_audio_profile_id.get.return_value = Profiles.DEFAULT_PROFILE
    identity = MagicMock()
    identity.hash = b"\x22" * 16

    with patch("meshchatx.src.backend.telephone_manager.Telephone"):
        tm = TelephoneManager(
            identity=identity,
            config_manager=cfg,
            storage_dir=str(tmp_path),
        )
        tm.web_audio_required = False
        tm.init_telephone()
        assert hostless_lxst_audio_installed() is False


# ---------------------------------------------------------------------------
# MeshChatX web_audio_required helper
# ---------------------------------------------------------------------------


def test_oracle_meshchat_web_audio_required_host_audio_unavailable():
    from meshchatx.meshchat import ReticulumMeshChat

    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app._headless = True
    app._host_audio_unavailable_cached = None
    with (
        patch("meshchatx.meshchat._is_chaquopy_android", return_value=False),
        patch.object(
            ReticulumMeshChat,
            "_probe_host_audio_unavailable",
            return_value=True,
        ),
    ):
        assert app.web_audio_required() is True


def test_oracle_meshchat_web_audio_required_env(monkeypatch):
    from meshchatx.meshchat import ReticulumMeshChat

    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app._headless = False
    app._host_audio_unavailable_cached = False
    monkeypatch.setenv("MESHCHAT_FORCE_WEB_AUDIO", "1")
    with patch("meshchatx.meshchat._is_chaquopy_android", return_value=False):
        assert app.web_audio_required() is True
    monkeypatch.delenv("MESHCHAT_FORCE_WEB_AUDIO", raising=False)


def test_oracle_meshchat_web_audio_not_required_when_host_audio_ok():
    from meshchatx.meshchat import ReticulumMeshChat

    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app._headless = True
    app._host_audio_unavailable_cached = False
    os.environ.pop("MESHCHAT_FORCE_WEB_AUDIO", None)
    with patch("meshchatx.meshchat._is_chaquopy_android", return_value=False):
        assert app.web_audio_required() is False


def test_oracle_headless_alone_does_not_force_web_audio():
    """Frozen Electron uses --headless but still has host speakers/mic."""
    from meshchatx.meshchat import ReticulumMeshChat

    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app._headless = True
    app._host_audio_unavailable_cached = None
    os.environ.pop("MESHCHAT_FORCE_WEB_AUDIO", None)
    with (
        patch("meshchatx.meshchat._is_chaquopy_android", return_value=False),
        patch.object(
            ReticulumMeshChat,
            "_probe_host_audio_unavailable",
            return_value=False,
        ),
    ):
        assert app.web_audio_required() is False


# ---------------------------------------------------------------------------
# Android codec2 candidate discovery
# ---------------------------------------------------------------------------


def test_android_codec2_honours_explicit_path(tmp_path, monkeypatch):
    from meshchatx import android_codec2

    lib = tmp_path / "libcodec2.so"
    lib.write_bytes(b"\x7fELF")
    monkeypatch.setenv("MESHCHAT_LIBCODEC2_PATH", str(lib))
    candidates = android_codec2._libcodec2_candidates()
    assert lib.resolve() in [c.resolve() for c in candidates]


def test_android_codec2_native_lib_dir(tmp_path, monkeypatch):
    from meshchatx import android_codec2

    native = tmp_path / "arm64-v8a"
    native.mkdir()
    lib = native / "libcodec2.so"
    lib.write_bytes(b"\x7fELF")
    monkeypatch.setenv("MESHCHAT_NATIVE_LIB_DIR", str(native))
    candidates = android_codec2._libcodec2_candidates()
    assert lib.resolve() in [c.resolve() for c in candidates]


# ---------------------------------------------------------------------------
# Bridge push through hostless audio_input before WebAudioSource swap
# ---------------------------------------------------------------------------


def test_push_client_frame_uses_hostless_audio_input_before_swap():
    tele = MagicMock()
    tele.active_call = object()
    hostless = HostlessAudioSource(target_frame_ms=60, sink=MagicMock())
    hostless.sink.can_receive.return_value = True
    tele.audio_input = hostless
    tele_mgr = MagicMock()
    tele_mgr.telephone = tele
    tele_mgr.is_voicemail_session_active = False
    bridge = WebAudioBridge(tele_mgr, MagicMock(), force_enabled=True)
    bridge.tx_source = None
    pcm = np.zeros(80, dtype=np.int16).tobytes()
    bridge.push_client_frame(pcm)
    hostless.sink.handle_frame.assert_called()
