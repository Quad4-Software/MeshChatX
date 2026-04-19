# SPDX-License-Identifier: 0BSD
"""Tests for the in-process audio decode/encode helpers.

These tests stand in for the previous ffmpeg subprocess pipeline.
Coverage is targeted at the public ``audio_codec`` API:

* ``decode_audio`` for WAV (built-in), miniaudio formats and OGG/Opus
* ``encode_pcm_to_ogg_opus`` round-trips
* ``encode_audio_to_ogg_opus`` for arbitrary inputs
* ``write_silence_ogg_opus`` for empty greetings/voicemails
* ``encode_audio_bytes_to_ogg_opus`` passthrough + decode-and-reencode
"""

import io
import math
import os
import struct
import tempfile
import wave

import numpy as np
import pytest

from meshchatx.src.backend import audio_codec


def _build_wav_pcm16(
    samplerate: int = 48000,
    duration_seconds: float = 0.4,
    frequency: float = 440.0,
    channels: int = 1,
) -> bytes:
    n_samples = int(samplerate * duration_seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        frames = bytearray()
        for i in range(n_samples):
            sample = int(0.3 * 32767 * math.sin(2 * math.pi * frequency * (i / samplerate)))
            for _ in range(channels):
                frames.extend(struct.pack("<h", sample))
        wf.writeframes(bytes(frames))
    return buf.getvalue()


def _tmp_opus_path() -> str:
    tf = tempfile.NamedTemporaryFile(suffix=".opus", delete=False)
    tf.close()
    return tf.name


def test_decode_audio_wav_via_builtin_wave():
    wav = _build_wav_pcm16(samplerate=48000, duration_seconds=0.2)
    decoded = audio_codec.decode_audio(wav)
    assert decoded.samplerate == 48000
    assert decoded.channels == 1
    assert decoded.samples.dtype == np.float32
    assert decoded.samples.shape[1] == 1
    assert decoded.samples.shape[0] == int(48000 * 0.2)


def test_decode_audio_accepts_path_and_filelike(tmp_path):
    wav = _build_wav_pcm16()
    path = tmp_path / "x.wav"
    path.write_bytes(wav)
    from_path = audio_codec.decode_audio(str(path))
    from_filelike = audio_codec.decode_audio(io.BytesIO(wav))
    assert from_path.samples.shape == from_filelike.samples.shape


def test_decode_audio_invalid_payload_raises():
    with pytest.raises(ValueError):
        audio_codec.decode_audio(b"not audio at all")


def test_encode_pcm_to_ogg_opus_writes_valid_container():
    out = _tmp_opus_path()
    try:
        samples = np.zeros((48000, 1), dtype=np.float32)
        audio_codec.encode_pcm_to_ogg_opus(samples, 48000, 1, out)
        with open(out, "rb") as f:
            assert f.read(4) == b"OggS"
        assert os.path.getsize(out) > 0
    finally:
        os.unlink(out)


def test_encode_pcm_to_ogg_opus_resamples_arbitrary_rate():
    """Inputs at any rate (here 22050 stereo) must be normalized before encode."""
    out = _tmp_opus_path()
    try:
        samplerate = 22050
        channels = 2
        n = samplerate
        samples = np.zeros((n, channels), dtype=np.float32)
        for i in range(n):
            v = 0.2 * math.sin(2 * math.pi * 880.0 * (i / samplerate))
            samples[i, 0] = v
            samples[i, 1] = v
        audio_codec.encode_pcm_to_ogg_opus(samples, samplerate, channels, out)
        assert os.path.getsize(out) > 0
        with open(out, "rb") as f:
            assert f.read(4) == b"OggS"
    finally:
        os.unlink(out)


def test_encode_audio_to_ogg_opus_decodes_and_reencodes(tmp_path):
    wav = _build_wav_pcm16(duration_seconds=0.3)
    src = tmp_path / "in.wav"
    src.write_bytes(wav)
    dst = tmp_path / "out.opus"
    audio_codec.encode_audio_to_ogg_opus(str(src), str(dst))
    assert dst.exists()
    assert dst.read_bytes()[:4] == b"OggS"


def test_encode_audio_bytes_to_ogg_opus_returns_passthrough_for_ogg():
    ogg = b"OggS" + b"\x00" * 32
    assert audio_codec.encode_audio_bytes_to_ogg_opus(ogg) is ogg


def test_encode_audio_bytes_to_ogg_opus_decodes_wav():
    wav = _build_wav_pcm16()
    encoded = audio_codec.encode_audio_bytes_to_ogg_opus(wav)
    assert encoded is not None
    assert encoded[:4] == b"OggS"
    assert len(encoded) < len(wav)


def test_encode_audio_bytes_to_ogg_opus_returns_none_for_garbage():
    assert audio_codec.encode_audio_bytes_to_ogg_opus(b"\x00" * 32) is None


def test_write_silence_ogg_opus(tmp_path):
    dst = tmp_path / "silence.opus"
    audio_codec.write_silence_ogg_opus(str(dst), seconds=0.5)
    assert dst.exists()
    assert dst.read_bytes()[:4] == b"OggS"
    assert dst.stat().st_size > 0


def test_is_ogg_opus_bytes_helper():
    assert audio_codec.is_ogg_opus_bytes(b"OggS\x01\x02\x03\x04")
    assert not audio_codec.is_ogg_opus_bytes(b"RIFFsomething")
    assert not audio_codec.is_ogg_opus_bytes(b"")


def _ogg_opus_duration_seconds(path: str) -> float:
    """Compute encoded duration from the Ogg granule positions and Opus pre-skip.

    Lets us assert the encoded file is exactly as long as the input PCM
    without depending on libopusfile being installed for decode.
    """
    with open(path, "rb") as f:
        data = f.read()
    last_gp = 0
    i = 0
    while i + 27 <= len(data):
        if data[i : i + 4] != b"OggS":
            i += 1
            continue
        gp = struct.unpack("<q", data[i + 6 : i + 14])[0]
        nsegs = data[i + 26]
        if i + 27 + nsegs > len(data):
            break
        body = sum(data[i + 27 : i + 27 + nsegs])
        i += 27 + nsegs + body
        if gp > 0:
            last_gp = gp
    head = data.find(b"OpusHead")
    pre_skip = struct.unpack("<H", data[head + 10 : head + 12])[0] if head >= 0 else 0
    return max(0.0, (last_gp - pre_skip) / 48000.0)


@pytest.mark.parametrize("duration_seconds", [0.3, 1.0, 5.0, 10.0])
def test_encode_pcm_to_ogg_opus_preserves_duration(duration_seconds):
    """Regression test: encoded length must match the input length.

    The previous OpusFileSink-based path silently dropped frames once the
    threaded sink's bounded deque overflowed (any clip >~3.8s came out
    truncated to ~4.5s) and tacked 600 ms of silence onto the tail of
    every clip. A trimmed ringtone therefore never matched the user's
    selection. The synchronous OggOpusWriter path must be exact.
    """
    out = _tmp_opus_path()
    try:
        sr = 48000
        n = int(sr * duration_seconds)
        t = np.arange(n, dtype=np.float32) / sr
        samples = (0.3 * np.sin(2 * math.pi * 440.0 * t)).astype(np.float32).reshape(-1, 1)
        audio_codec.encode_pcm_to_ogg_opus(samples, sr, 1, out)
        encoded = _ogg_opus_duration_seconds(out)
        assert abs(encoded - duration_seconds) < 0.001, (
            f"expected {duration_seconds}s, got {encoded}s"
        )
    finally:
        os.unlink(out)


def test_encode_pcm_to_ogg_opus_audio_profile_keeps_stereo():
    """``PROFILE_AUDIO_MAX`` must keep stereo input as stereo, not collapse to mono."""
    out = _tmp_opus_path()
    try:
        from LXST.Codecs import Opus

        sr = 48000
        n = sr  # 1 second
        samples = np.zeros((n, 2), dtype=np.float32)
        t = np.arange(n, dtype=np.float32) / sr
        samples[:, 0] = 0.3 * np.sin(2 * math.pi * 440.0 * t)
        samples[:, 1] = 0.3 * np.sin(2 * math.pi * 660.0 * t)
        audio_codec.encode_pcm_to_ogg_opus(
            samples, sr, 2, out, profile=Opus.PROFILE_AUDIO_MAX
        )
        with open(out, "rb") as f:
            data = f.read()
        head = data.find(b"OpusHead")
        assert head >= 0
        channels = data[head + 9]
        assert channels == 2
        assert _ogg_opus_duration_seconds(out) == pytest.approx(1.0, abs=0.001)
    finally:
        os.unlink(out)
