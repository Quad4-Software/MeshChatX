# SPDX-License-Identifier: 0BSD
"""Exploratory fuzzing and light oracles for hardened security surfaces.

Oracles are intentional invariants (not full differential testing):
  - WebAudioSource never raises on arbitrary PCM and drops oversized frames
  - call timeout parse always lands in [1, 120]
  - attachment-like field shapes never crash normalize helpers
"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.call_timeout import (
    MAX_CALL_TIMEOUT_SECONDS,
    MIN_CALL_TIMEOUT_SECONDS,
    clamp_call_timeout_seconds,
)
from meshchatx.src.backend.web_audio_bridge import WebAudioSource


class _Sink:
    def __init__(self):
        self.frames = []

    def can_receive(self, from_source=None):
        return True

    def handle_frame(self, frame, source=None):
        self.frames.append(frame)


# ---------------------------------------------------------------------------
# Light oracles: call timeout
# ---------------------------------------------------------------------------


@settings(deadline=None, max_examples=80, suppress_health_check=[HealthCheck.too_slow])
@given(
    raw=st.one_of(
        st.none(),
        st.integers(min_value=-10_000, max_value=10_000),
        st.text(max_size=40),
        st.sampled_from(
            ["", "15", "0", "-1", "999999", "1.5", "nan", "0x10", "timeout"],
        ),
    ),
)
def test_oracle_call_timeout_always_in_bounds(raw):
    """Oracle: every parseable/unparseable input clamps into the safe window."""
    out = clamp_call_timeout_seconds(raw)
    assert MIN_CALL_TIMEOUT_SECONDS <= out <= MAX_CALL_TIMEOUT_SECONDS


def test_oracle_call_timeout_known_cases():
    assert clamp_call_timeout_seconds(None) == 15
    assert clamp_call_timeout_seconds("15") == 15
    assert clamp_call_timeout_seconds("1") == 1
    assert clamp_call_timeout_seconds("120") == 120
    assert clamp_call_timeout_seconds("0") == 1
    assert clamp_call_timeout_seconds("-5") == 1
    assert clamp_call_timeout_seconds("99999") == 120
    assert clamp_call_timeout_seconds("nope") == 15


# ---------------------------------------------------------------------------
# Exploratory + oracle: web audio PCM
# ---------------------------------------------------------------------------


@settings(deadline=None, max_examples=60, suppress_health_check=[HealthCheck.too_slow])
@given(pcm=st.binary(min_size=0, max_size=WebAudioSource.MAX_PCM_BYTES + 4096))
def test_exploratory_web_audio_source_never_raises(pcm):
    """Exploratory: arbitrary PCM must not crash push_pcm."""
    sink = _Sink()
    src = WebAudioSource(target_frame_ms=60, sink=sink)
    try:
        src.push_pcm(pcm)
    except Exception as exc:
        pytest.fail(f"push_pcm raised: {exc}")


@settings(
    deadline=None,
    max_examples=30,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.large_base_example],
)
@given(extra=st.integers(min_value=1, max_value=4096))
def test_oracle_web_audio_drops_oversized_pcm(extra):
    """Oracle: frames above MAX_PCM_BYTES never reach the sink."""
    pcm = b"\x00" * (WebAudioSource.MAX_PCM_BYTES + extra)
    sink = _Sink()
    src = WebAudioSource(target_frame_ms=60, sink=sink)
    src.push_pcm(pcm)
    assert sink.frames == []


def test_oracle_web_audio_drops_exact_oversize_boundary():
    sink = _Sink()
    src = WebAudioSource(target_frame_ms=60, sink=sink)
    src.push_pcm(b"\x00" * (WebAudioSource.MAX_PCM_BYTES + 1))
    assert sink.frames == []
    src.push_pcm(np.zeros(160, dtype=np.int16).tobytes())
    assert len(sink.frames) == 1


# ---------------------------------------------------------------------------
# Light oracles: attachment-like field shapes (mirror serve guards)
# ---------------------------------------------------------------------------


def _safe_image_type(raw) -> str:
    allowed = {"png", "jpeg", "jpg", "gif", "webp", "bmp"}
    image_type = raw if isinstance(raw, str) else "png"
    image_type = image_type.lower().replace("image/", "").strip() or "png"
    if image_type not in allowed:
        image_type = "png"
    return image_type


def _resolve_served_image_type(image_data: bytes, declared=None) -> str | None:
    """Mirror meshchat LXMF image serve: Content-Type from magic only."""
    from meshchatx.src.backend.sticker_utils import detect_image_format_from_magic

    allowed = {"png", "jpeg", "jpg", "gif", "webp", "bmp"}
    detected = detect_image_format_from_magic(image_data)
    if detected is None or detected not in allowed:
        return None
    return "jpeg" if detected == "jpeg" else detected


def _try_b64(raw):
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return base64.b64decode(raw)
    except Exception:
        return None


@settings(deadline=None, max_examples=80, suppress_health_check=[HealthCheck.too_slow])
@given(
    image_type=st.one_of(
        st.none(),
        st.integers(),
        st.booleans(),
        st.lists(st.text(max_size=8), max_size=3),
        st.text(max_size=40),
        st.sampled_from(
            ["png", "PNG", "image/jpeg", "svg", "svg+xml", "webm", "", " "],
        ),
    ),
)
def test_oracle_image_type_always_allowlisted(image_type):
    """Oracle: served image types collapse to the raster allowlist."""
    out = _safe_image_type(image_type)
    assert out in {"png", "jpeg", "jpg", "gif", "webp", "bmp"}


@settings(deadline=None, max_examples=60, suppress_health_check=[HealthCheck.too_slow])
@given(
    raw=st.one_of(
        st.none(),
        st.binary(max_size=64).map(lambda b: base64.b64encode(b).decode("ascii")),
        st.text(max_size=80),
        st.integers(),
        st.sampled_from(["", "====", "not-base64!!!", "A", "QQ=="]),
    ),
)
def test_exploratory_b64_decode_never_raises(raw):
    """Exploratory: attachment base64 decode path must not throw."""
    try:
        _try_b64(raw)
    except Exception as exc:
        pytest.fail(f"b64 helper raised: {exc}")


def test_oracle_known_bad_attachment_shapes_rejected():
    assert _try_b64(None) is None
    assert _try_b64(123) is None
    assert _try_b64("") is None
    assert _safe_image_type(None) == "png"
    assert _safe_image_type(99) == "png"
    assert _safe_image_type("svg") == "png"
    assert _safe_image_type("image/webp") == "webp"
    assert _resolve_served_image_type(b"<html>") is None
    assert _resolve_served_image_type(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8) == "png"


# ---------------------------------------------------------------------------
# Exploratory: bridge still never crashes with mocked sink under fuzz PCM
# ---------------------------------------------------------------------------


@settings(deadline=None, max_examples=40, suppress_health_check=[HealthCheck.too_slow])
@given(pcm=st.binary(min_size=0, max_size=WebAudioSource.MAX_PCM_BYTES + 2048))
def test_exploratory_bridge_push_with_real_source(pcm):
    from meshchatx.src.backend.web_audio_bridge import WebAudioBridge

    tele_mgr = MagicMock()
    tele_mgr.is_voicemail_session_active = False
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    sink = _Sink()
    bridge.tx_source = WebAudioSource(target_frame_ms=60, sink=sink)
    try:
        bridge.push_client_frame(pcm)
    except Exception as exc:
        pytest.fail(f"push_client_frame raised: {exc}")
    if len(pcm) > WebAudioSource.MAX_PCM_BYTES:
        assert sink.frames == []
