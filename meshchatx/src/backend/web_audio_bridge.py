# SPDX-License-Identifier: 0BSD

import asyncio
import contextlib
import json
import threading

import numpy as np
import RNS
from LXST.Codecs import Null, Raw
from LXST.Mixer import Mixer
from LXST.Pipeline import Pipeline
from LXST.Sinks import LocalSink
from LXST.Sources import LocalSource

from .telephone_manager import Tee

_HOSTLESS_AUDIO_INSTALLED = False
_ORIG_LINE_SOURCE = None
_ORIG_LINE_SINK = None


def _log_debug(msg: str):
    RNS.log(msg, RNS.LOG_DEBUG)


class HostlessAudioSource(LocalSource):
    """LineSource stand-in that never opens PulseAudio / host capture devices.

    Docker headless and other web deployments have no usable host mic. LXST still
    constructs LineSource during call setup before the websocket bridge attaches.
    This class accepts the LineSource constructor shape and later yields to
    WebAudioSource once a browser client connects.
    """

    def __init__(
        self,
        preferred_device=None,
        target_frame_ms=60,
        codec=None,
        sink=None,
        filters=None,
        gain=0.0,
        ease_in=0.0,
        skip=0.0,
    ):
        self.preferred_device = preferred_device
        self.target_frame_ms = target_frame_ms or 60
        self.sink = sink
        self.filters = filters
        self.gain = gain
        self.ease_in = ease_in
        self.skip = skip
        self.codec = codec or Raw(channels=1, bitdepth=16)
        self.channels = 1
        self.samplerate = 48000
        self.bitdepth = 16
        self.should_run = False
        self.samples_per_frame = max(
            1,
            int(round((self.target_frame_ms / 1000.0) * self.samplerate)),
        )

    def start(self):
        self.should_run = True

    def stop(self):
        self.should_run = False

    def can_receive(self, from_source=None):
        return True

    def handle_frame(self, frame, source=None):
        pass

    def push_pcm(self, pcm_bytes: bytes):
        # Used if a bridge client attaches before WebAudioSource swap.
        if not pcm_bytes or not self.sink:
            return
        try:
            samples = (
                np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            )
            if samples.size == 0:
                return
            samples = samples.reshape(-1, 1)
            frame = Raw(channels=1, bitdepth=16).encode(samples)
            if self.sink.can_receive(from_source=self):
                self.sink.handle_frame(frame, self)
        except Exception as exc:
            RNS.log(f"HostlessAudioSource: push_pcm failed: {exc}", RNS.LOG_ERROR)


class HostlessAudioSink(LocalSink):
    """LineSink stand-in that discards PCM when no host speaker exists."""

    def __init__(self, preferred_device=None, autodigest=True, low_latency=False):
        self.preferred_device = preferred_device
        self.autodigest = autodigest
        self.low_latency = low_latency
        self.should_run = False
        self.samplerate = 48000
        self.channels = 1
        self._wants_low_latency = False

    def can_receive(self, from_source=None):
        return True

    def handle_frame(self, frame, source=None):
        pass

    def start(self):
        self.should_run = True

    def stop(self):
        self.should_run = False

    def enable_low_latency(self):
        self._wants_low_latency = True


def install_hostless_lxst_audio() -> bool:
    """Replace LXST LineSource/LineSink with hostless stand-ins (idempotent)."""
    global _HOSTLESS_AUDIO_INSTALLED, _ORIG_LINE_SOURCE, _ORIG_LINE_SINK
    if _HOSTLESS_AUDIO_INSTALLED:
        return True
    try:
        from LXST.Primitives import Telephony as lxst_telephony
    except Exception as exc:
        RNS.log(
            f"WebAudioBridge: cannot install hostless audio backends: {exc}",
            RNS.LOG_ERROR,
        )
        return False

    _ORIG_LINE_SOURCE = getattr(lxst_telephony, "LineSource", None)
    _ORIG_LINE_SINK = getattr(lxst_telephony, "LineSink", None)
    lxst_telephony.LineSource = HostlessAudioSource
    lxst_telephony.LineSink = HostlessAudioSink
    _HOSTLESS_AUDIO_INSTALLED = True
    RNS.log(
        "WebAudioBridge: installed hostless LXST audio backends (no PulseAudio)",
        RNS.LOG_INFO,
    )
    return True


def hostless_lxst_audio_installed() -> bool:
    return _HOSTLESS_AUDIO_INSTALLED


def reset_hostless_lxst_audio_for_tests() -> None:
    """Restore original LXST LineSource/LineSink (tests only)."""
    global _HOSTLESS_AUDIO_INSTALLED, _ORIG_LINE_SOURCE, _ORIG_LINE_SINK
    if not _HOSTLESS_AUDIO_INSTALLED:
        return
    with contextlib.suppress(Exception):
        from LXST.Primitives import Telephony as lxst_telephony

        if _ORIG_LINE_SOURCE is not None:
            lxst_telephony.LineSource = _ORIG_LINE_SOURCE
        if _ORIG_LINE_SINK is not None:
            lxst_telephony.LineSink = _ORIG_LINE_SINK
    _HOSTLESS_AUDIO_INSTALLED = False
    _ORIG_LINE_SOURCE = None
    _ORIG_LINE_SINK = None


class WebAudioSource(LocalSource):
    """Injects PCM frames (int16 little-endian) received over websocket into the transmit mixer."""

    # ~2.7s of 48 kHz mono int16; normal frames are tens of ms.
    MAX_PCM_BYTES = 256 * 1024

    def __init__(self, target_frame_ms: int, sink: Mixer):
        self.target_frame_ms = target_frame_ms or 60
        self.sink = sink
        self.codec = Raw(channels=1, bitdepth=16)
        self.channels = 1
        self.samplerate = 48000
        self.bitdepth = 16

    def start(self):
        # Nothing to start, as frames are pushed from the websocket thread.
        pass

    def stop(self):
        # Nothing to stop, but kept for interface compatibility.
        pass

    def can_receive(self, from_source=None):
        return True

    def handle_frame(self, frame, source=None):
        # Not used, as frames are pushed via push_pcm.
        pass

    def push_pcm(self, pcm_bytes: bytes):
        try:
            if pcm_bytes is None:
                return
            if len(pcm_bytes) > self.MAX_PCM_BYTES:
                RNS.log(
                    f"WebAudioSource: dropping oversized pcm frame ({len(pcm_bytes)} bytes)",
                    RNS.LOG_WARNING,
                )
                return
            samples = (
                np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            )
            if samples.size == 0:
                return
            samples = samples.reshape(-1, 1)
            frame = self.codec.encode(samples)
            if self.sink and self.sink.can_receive(from_source=self):
                self.sink.handle_frame(frame, self)
        except Exception as exc:
            RNS.log(f"WebAudioSource: failed to push pcm: {exc}", RNS.LOG_ERROR)


class WebAudioSink(LocalSink):
    """Pushes received PCM frames to websocket clients."""

    def __init__(self, loop: asyncio.AbstractEventLoop, send_bytes):
        self.loop = loop
        self.send_bytes = send_bytes

    def can_receive(self, from_source=None):
        return True

    def handle_frame(self, frame, source):
        try:
            # frame is expected to be numpy float PCM from receive mixer
            if hasattr(frame, "astype"):
                samples = np.clip(frame, -1.0, 1.0).astype(np.float32)
                pcm = (samples * 32767.0).astype(np.int16).tobytes()
            else:
                pcm = frame
            self.loop.call_soon_threadsafe(asyncio.create_task, self.send_bytes(pcm))
        except Exception as exc:
            RNS.log(f"WebAudioSink: failed to handle frame: {exc}", RNS.LOG_ERROR)


class WebAudioBridge:
    """Coordinates websocket audio transport with an active LXST telephone call."""

    def __init__(self, telephone_manager, config_manager, force_enabled: bool = False):
        self.telephone_manager = telephone_manager
        self.config_manager = config_manager
        self.force_enabled = bool(force_enabled)
        self.clients = set()
        self.tx_source: WebAudioSource | None = None
        self.rx_sink: WebAudioSink | None = None
        self.rx_tee: Tee | None = None
        self._loop = None
        self.lock = threading.Lock()

    @property
    def loop(self):
        if self._loop:
            return self._loop

        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            # Fallback to finding it via AsyncUtils if possible
            from .async_utils import AsyncUtils

            self._loop = AsyncUtils.main_loop

        return self._loop

    def _tele(self):
        return getattr(self.telephone_manager, "telephone", None)

    def config_enabled(self):
        if self.force_enabled:
            return True
        return (
            self.config_manager
            and hasattr(self.config_manager, "telephone_web_audio_enabled")
            and self.config_manager.telephone_web_audio_enabled.get()
        )

    def allow_fallback(self):
        if self.force_enabled:
            # Never restore PulseAudio host paths on headless/web-required hosts.
            return False
        return (
            self.config_manager
            and hasattr(self.config_manager, "telephone_web_audio_allow_fallback")
            and self.config_manager.telephone_web_audio_allow_fallback.get()
        )

    def get_diagnostics(self):
        """Return a small status snapshot for /api/v1/telephone/status."""
        tele = self._tele()
        return {
            "force_enabled": self.force_enabled,
            "config_enabled": bool(self.config_enabled()),
            "hostless_backends": hostless_lxst_audio_installed(),
            "client_count": len(self.clients),
            "has_tx_source": self.tx_source is not None,
            "has_rx_sink": self.rx_sink is not None,
            "has_active_call": bool(tele and getattr(tele, "active_call", None)),
        }

    def attach_client(self, client):
        with self.lock:
            tele = self._tele()
            if not tele or not tele.active_call:
                return False
            # Do not attach during voicemail
            if getattr(self.telephone_manager, "is_voicemail_session_active", False):
                return False
            self.clients.add(client)
            self._ensure_remote_tx(tele)
            self._ensure_rx_tee(tele)
            return True

    def detach_client(self, client):
        with self.lock:
            if client in self.clients:
                self.clients.remove(client)
            if not self.clients and self.allow_fallback():
                self._restore_host_audio()

    async def send_status(self, client):
        tele = self._tele()
        frame_ms = getattr(tele, "target_frame_time_ms", None) or 60
        await client.send_str(
            json.dumps(
                {
                    "type": "web_audio.ready",
                    "frame_ms": frame_ms,
                    "required": self.force_enabled,
                },
            ),
        )

    def push_client_frame(self, pcm_bytes: bytes):
        with self.lock:
            tele = self._tele()
            if not tele or not getattr(tele, "active_call", None):
                return
            if getattr(self.telephone_manager, "is_voicemail_session_active", False):
                return
            if not self.tx_source:
                # Hostless LineSource stand-in still accepts PCM until swap.
                audio_in = getattr(tele, "audio_input", None)
                if audio_in is not None and hasattr(audio_in, "push_pcm"):
                    audio_in.push_pcm(pcm_bytes)
                return
            self.tx_source.push_pcm(pcm_bytes)

    async def _send_bytes_to_all(self, pcm_bytes: bytes):
        stale = []
        for ws in list(self.clients):
            try:
                await ws.send_bytes(pcm_bytes)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.detach_client(ws)

    def _ensure_remote_tx(self, tele):
        # Rebuild transmit path with websocket-backed source
        if self.tx_source:
            return
        # Do not create transmit source during voicemail
        if getattr(self.telephone_manager, "is_voicemail_session_active", False):
            return
        try:
            if hasattr(tele, "audio_input") and tele.audio_input:
                tele.audio_input.stop()
            self.tx_source = WebAudioSource(
                target_frame_ms=getattr(tele, "target_frame_time_ms", 60),
                sink=tele.transmit_mixer,
            )
            tele.audio_input = self.tx_source
            if tele.transmit_mixer and not tele.transmit_mixer.should_run:
                tele.transmit_mixer.start()
        except Exception as exc:
            RNS.log(
                f"WebAudioBridge: failed to swap transmit path: {exc}",
                RNS.LOG_ERROR,
            )

    def _ensure_rx_tee(self, tele):
        if self.rx_sink:
            return
        try:
            if not self.loop:
                return
            send_fn = lambda pcm: self._send_bytes_to_all(pcm)  # noqa: E731
            self.rx_sink = WebAudioSink(self.loop, send_fn)
            # Build tee with existing audio_output as first sink to preserve speaker
            base_sink = tele.audio_output
            self.rx_tee = Tee(base_sink) if base_sink else Tee(self.rx_sink)
            if base_sink:
                self.rx_tee.add_sink(self.rx_sink)
            tele.audio_output = self.rx_tee
            if tele.receive_pipeline:
                tele.receive_pipeline.stop()
            tele.receive_pipeline = Pipeline(
                source=tele.receive_mixer,
                codec=Null(),
                sink=self.rx_tee,
            )
            tele.receive_pipeline.start()
        except Exception as exc:
            RNS.log(f"WebAudioBridge: failed to tee receive path: {exc}", RNS.LOG_ERROR)

    def _restore_host_audio(self):
        tele = self._tele()
        if not tele:
            return
        with contextlib.suppress(Exception):
            with contextlib.suppress(Exception):
                if hasattr(tele, "_Telephony__reconfigure_transmit_pipeline"):
                    tele._Telephony__reconfigure_transmit_pipeline()
            if tele.receive_pipeline:
                tele.receive_pipeline.stop()
            if tele.audio_output and self.rx_tee:
                # If tee had original sink as first element, revert
                primary = self.rx_tee.sinks[0] if self.rx_tee.sinks else None
                if primary is not None:
                    tele.audio_output = primary
            if tele.receive_mixer:
                tele.receive_pipeline = Pipeline(
                    source=tele.receive_mixer,
                    codec=Null(),
                    sink=tele.audio_output,
                )
                tele.receive_pipeline.start()
        self.tx_source = None
        self.rx_sink = None
        self.rx_tee = None

    def on_call_ended(self):
        with self.lock:
            self.clients.clear()
            self.tx_source = None
            self.rx_sink = None
            self.rx_tee = None
