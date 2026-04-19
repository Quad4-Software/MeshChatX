# SPDX-License-Identifier: 0BSD
"""Pure-Python audio decode/encode helpers used across MeshChatX.

This module replaces the previous ffmpeg subprocess pipelines used for
voicemail greetings, ringtones and browser-recorded voice messages. It
exposes a small API that decodes user-supplied audio into ``float32`` PCM
frames and encodes PCM frames into LXMF-compatible OGG/Opus files using
``LXST.Sinks.OpusFileSink``.

Decoders, in priority order:

1. ``wave`` (built-in) for ``RIFF/WAVE`` containers.
2. `miniaudio <https://pypi.org/project/miniaudio/>`_ for WAV, MP3, FLAC
   and OGG/Vorbis. Bundled as a runtime dependency on every supported
   target (including Android via the Chaquopy recipe under
   ``android/chaquopy-recipes/miniaudio-1.70``).
3. LXST/pyogg ``OpusFile`` for OGG/Opus payloads.

Encoder: ``LXST.Sinks.OpusFileSink`` configured with a voice-friendly
Opus profile so the output is a valid OGG/Opus file that Sideband and
the rest of the LXMF ecosystem can play.
"""

from __future__ import annotations

import io
import os
import tempfile
import wave
from dataclasses import dataclass


@dataclass(frozen=True)
class DecodedAudio:
    """A decoded audio buffer.

    Attributes:
        samples: ``float32`` numpy array shaped ``(frames, channels)`` with
            values in ``[-1.0, 1.0]``.
        samplerate: PCM sample rate in Hz.
        channels: Channel count.

    """

    samples: object
    samplerate: int
    channels: int


def _read_bytes(source) -> bytes:
    """Return the bytes for ``source`` (path, file-like or bytes)."""
    if isinstance(source, (bytes, bytearray, memoryview)):
        return bytes(source)
    if hasattr(source, "read"):
        data = source.read()
        return data if isinstance(data, bytes) else bytes(data)
    if isinstance(source, (str, os.PathLike)):
        with open(os.fspath(source), "rb") as f:
            return f.read()
    msg = f"Unsupported audio source type: {type(source)!r}"
    raise TypeError(msg)


def _decode_with_wave(data: bytes):
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    try:
        import numpy as np

        with wave.open(io.BytesIO(data), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            raw = wf.readframes(wf.getnframes())

        if channels < 1 or framerate <= 0 or len(raw) == 0:
            return None

        if sample_width == 2:
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 1:
            samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif sample_width == 4:
            samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            return None

        return DecodedAudio(
            samples=samples.reshape(-1, channels),
            samplerate=framerate,
            channels=channels,
        )
    except Exception:
        return None


def _decode_with_miniaudio(data: bytes):
    try:
        import miniaudio
        import numpy as np
    except ImportError:
        return None
    try:
        decoded = miniaudio.decode(
            data,
            output_format=miniaudio.SampleFormat.SIGNED16,
        )
    except Exception:
        return None
    if decoded.num_frames <= 0 or decoded.nchannels <= 0:
        return None
    samples = (
        np.frombuffer(decoded.samples, dtype=np.int16).astype(np.float32) / 32768.0
    )
    return DecodedAudio(
        samples=samples.reshape(-1, decoded.nchannels),
        samplerate=decoded.sample_rate,
        channels=decoded.nchannels,
    )


def _decode_with_lxst_opus(data: bytes):
    if data[:4] != b"OggS":
        return None
    try:
        import numpy as np

        from LXST.Codecs.libs.pyogg import OpusFile
    except ImportError:
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".opus", delete=False)
    tmp.close()
    try:
        with open(tmp.name, "wb") as f:
            f.write(data)
        opus = OpusFile(tmp.name)
        type_max = float(np.iinfo(np.int16).max)
        samples = opus.as_array().astype(np.float32) / type_max
        if samples.ndim == 1:
            samples = samples.reshape(-1, opus.channels)
        return DecodedAudio(
            samples=samples,
            samplerate=int(opus.frequency),
            channels=int(opus.channels),
        )
    except Exception:
        return None
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def decode_audio(source) -> DecodedAudio:
    """Decode ``source`` into ``float32`` PCM frames.

    ``source`` may be a path (``str``/``os.PathLike``), a file-like object
    open in binary mode, or a ``bytes``/``bytearray`` payload.

    Raises:
        ValueError: If the payload could not be decoded by any backend.

    """
    data = _read_bytes(source)
    for decoder in (_decode_with_wave, _decode_with_miniaudio, _decode_with_lxst_opus):
        result = decoder(data)
        if result is not None:
            return result
    msg = "Unsupported audio format (could not decode with wave/miniaudio/LXST)"
    raise ValueError(msg)


def _opus_voice_profile():
    from LXST.Codecs import Opus

    return Opus.PROFILE_VOICE_HIGH


_OPUS_VALID_RATES = (8000, 12000, 16000, 24000, 48000)
_OPUS_TARGET_RATE = 48000


def _normalize_for_opus(
    samples,
    samplerate: int,
    channels: int,
    target_rate: int = _OPUS_TARGET_RATE,
    target_channels: int = 1,
):
    """Resample/remix ``samples`` to a layout the chosen Opus profile accepts.

    Returns ``float32`` frames at ``target_rate`` with ``target_channels``
    channels. Multi-channel input is downmixed to mono by averaging,
    mono input is duplicated when the profile expects stereo, and the
    rate is resampled via LXST's helper to stay consistent with the
    rest of the pipeline.
    """
    import numpy as np

    if samples.ndim == 1:
        samples = samples.reshape(-1, max(1, channels))
    if samples.dtype != np.float32:
        samples = samples.astype(np.float32)

    target_channels = max(1, int(target_channels))
    in_channels = samples.shape[1]
    if in_channels != target_channels:
        if target_channels == 1:
            samples = samples.mean(axis=1, keepdims=True).astype(np.float32)
        elif in_channels == 1:
            samples = np.repeat(samples, target_channels, axis=1)
        elif in_channels > target_channels:
            samples = samples[:, :target_channels]
        else:
            pad = np.repeat(samples[:, -1:], target_channels - in_channels, axis=1)
            samples = np.hstack([samples, pad])
        channels = target_channels

    if int(samplerate) != int(target_rate):
        from LXST.Codecs.Codec import resample

        samples = resample(
            samples,
            16,
            channels,
            int(samplerate),
            int(target_rate),
        )
        samplerate = int(target_rate)

    return samples, samplerate, channels


def encode_pcm_to_ogg_opus(
    samples,
    samplerate: int,
    channels: int,
    output_path: str,
    profile=None,
    frame_ms: int = 60,
) -> str:
    """Encode ``samples`` (``float32`` ``(frames, channels)``) to OGG/Opus.

    ``profile`` defaults to ``LXST.Codecs.Opus.PROFILE_VOICE_HIGH`` (48 kHz
    mono voip, ~16 kbps ceiling) which keeps voice payloads small while
    remaining intelligible. Inputs at any sample rate or channel count are
    transparently resampled/remixed to the profile's expected layout
    before encoding.

    Encoding is fully synchronous: PCM is fed straight into a
    ``OpusBufferedEncoder`` wrapped by an ``OggOpusWriter`` and flushed
    on close, so the encoded duration matches the input exactly with no
    frame loss and no trailing silence padding.
    """
    import numpy as np

    from LXST.Codecs import Opus
    from LXST.Codecs.libs.pyogg import OggOpusWriter, OpusBufferedEncoder

    if profile is None:
        profile = _opus_voice_profile()

    target_rate = int(Opus.profile_samplerate(profile))
    target_channels = Opus.profile_channels(profile)
    if not target_channels:
        target_channels = max(1, int(channels))
    application = Opus.profile_application(profile)
    bitrate_ceiling = Opus.profile_bitrate_ceiling(profile)

    samples, samplerate, channels = _normalize_for_opus(
        samples,
        samplerate,
        channels,
        target_rate=target_rate,
        target_channels=target_channels,
    )

    if os.path.exists(output_path):
        os.remove(output_path)

    encoder = OpusBufferedEncoder()
    encoder.set_application(application)
    encoder.set_sampling_frequency(int(samplerate))
    encoder.set_channels(int(channels))
    encoder.set_frame_size(int(frame_ms))
    if bitrate_ceiling:
        encoder.set_max_bytes_per_frame(
            Opus.max_bytes_per_frame(bitrate_ceiling, frame_ms),
        )

    type_max = np.iinfo(np.int16).max
    samples_per_frame = max(1, int(samplerate * frame_ms / 1000))

    writer = OggOpusWriter(output_path, encoder)
    try:
        if samples.shape[0] == 0:
            silence = np.zeros((samples_per_frame, channels), dtype=np.int16)
            writer.write(memoryview(bytearray(silence.tobytes())))
        else:
            clipped = np.clip(samples, -1.0, 1.0) * type_max
            int_samples = clipped.astype(np.int16)
            writer.write(memoryview(bytearray(int_samples.tobytes())))
    finally:
        writer.close()
    return output_path


def encode_audio_to_ogg_opus(source, output_path: str, profile=None) -> str:
    """Decode any supported ``source`` and re-encode it as OGG/Opus.

    Intended for converting user-uploaded greetings/ringtones (any format
    miniaudio can decode) into the OGG/Opus container required by the
    rest of the stack.
    """
    decoded = decode_audio(source)
    return encode_pcm_to_ogg_opus(
        decoded.samples,
        decoded.samplerate,
        decoded.channels,
        output_path,
        profile=profile,
    )


def write_silence_ogg_opus(
    output_path: str,
    seconds: float = 1.0,
    samplerate: int = 48000,
    channels: int = 1,
    profile=None,
) -> str:
    """Write a silent OGG/Opus file of ``seconds`` seconds to ``output_path``."""
    import numpy as np

    duration = max(0.05, float(seconds))
    n_frames = int(samplerate * duration)
    silence = np.zeros((n_frames, max(1, channels)), dtype=np.float32)
    return encode_pcm_to_ogg_opus(
        silence,
        samplerate,
        channels,
        output_path,
        profile=profile,
    )


def is_ogg_opus_bytes(data: bytes) -> bool:
    """Return ``True`` if ``data`` looks like an OGG container payload."""
    return len(data) >= 4 and data[:4] == b"OggS"


def encode_audio_bytes_to_ogg_opus(data: bytes, profile=None) -> bytes | None:
    """Decode ``data`` and return the corresponding OGG/Opus byte string.

    Returns ``None`` if the payload could not be decoded. If the payload
    is already an OGG container it is returned unchanged.
    """
    if is_ogg_opus_bytes(data):
        return data
    try:
        decoded = decode_audio(data)
    except (TypeError, ValueError):
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".opus", delete=False)
    tmp.close()
    try:
        encode_pcm_to_ogg_opus(
            decoded.samples,
            decoded.samplerate,
            decoded.channels,
            tmp.name,
            profile=profile,
        )
        with open(tmp.name, "rb") as f:
            return f.read()
    except Exception:
        return None
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
