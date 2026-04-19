# SPDX-License-Identifier: 0BSD
"""Tests for :mod:`meshchatx.src.backend.ringtone_manager`.

The manager performs conversion in-process via ``audio_codec``
(miniaudio + LXST). These tests pin the contract that
``convert_to_ringtone`` decodes any supported audio container and
produces a stored OGG/Opus ringtone.
"""

import io
import math
import os
import struct
import wave
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.ringtone_manager import RingtoneManager


def _build_wav_pcm16(duration_seconds: float = 0.4, samplerate: int = 48000) -> bytes:
    n_samples = int(samplerate * duration_seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        frames = bytearray()
        for i in range(n_samples):
            sample = int(0.3 * 32767 * math.sin(2 * math.pi * 440.0 * (i / samplerate)))
            frames.extend(struct.pack("<h", sample))
        wf.writeframes(bytes(frames))
    return buf.getvalue()


@pytest.fixture
def manager(tmp_path):
    config = MagicMock()
    return RingtoneManager(config, str(tmp_path))


def test_init_creates_storage_dir(manager, tmp_path):
    assert os.path.isdir(manager.storage_dir)
    assert manager.storage_dir == os.path.join(str(tmp_path), "ringtones")


def test_convert_to_ringtone_writes_ogg_opus(manager, tmp_path):
    src = tmp_path / "input.wav"
    src.write_bytes(_build_wav_pcm16())

    filename = manager.convert_to_ringtone(str(src))

    assert filename.endswith(".opus")
    out_path = os.path.join(manager.storage_dir, filename)
    assert os.path.exists(out_path)
    with open(out_path, "rb") as f:
        assert f.read(4) == b"OggS"


def test_convert_to_ringtone_uses_audio_codec(manager, tmp_path):
    src = tmp_path / "input.wav"
    src.write_bytes(_build_wav_pcm16())
    with patch(
        "meshchatx.src.backend.ringtone_manager.encode_audio_to_ogg_opus",
        return_value="ignored",
    ) as mock_encode:
        filename = manager.convert_to_ringtone(str(src))
    mock_encode.assert_called_once()
    args, _ = mock_encode.call_args
    assert args[0] == str(src)
    assert args[1].endswith(filename)


def test_remove_ringtone_deletes_file(manager, tmp_path):
    src = tmp_path / "input.wav"
    src.write_bytes(_build_wav_pcm16())
    filename = manager.convert_to_ringtone(str(src))
    out_path = manager.get_ringtone_path(filename)
    assert os.path.exists(out_path)
    assert manager.remove_ringtone(filename) is True
    assert not os.path.exists(out_path)


def test_remove_ringtone_missing_returns_true(manager):
    assert manager.remove_ringtone("does-not-exist.opus") is True
