import asyncio
import json
import threading
from typing import Optional

import numpy as np
import RNS
from LXST.Codecs import Null, Raw
from LXST.Mixer import Mixer
from LXST.Pipeline import Pipeline
from LXST.Sinks import LocalSink
from LXST.Sources import LocalSource

from .telephone_manager import Tee


def _log_debug(msg: str):
    RNS.log(msg, RNS.LOG_DEBUG)


class WebAudioSource(LocalSource):
    """Injects PCM frames (int16 little-endian) received over websocket into the transmit mixer."""

    def __init__(self, target_frame_ms: int, sink: Mixer):
        self.target_frame_ms = target_frame_ms or 60
        self.sink = sink
        self.codec = Raw(channels=1, bitdepth=16)
        self.channels = 1
        self.samplerate = 48000
        self.bitdepth = 16

    def start(self):
        # Nothing to start; frames are pushed from the websocket thread.
        pass

    def stop(self):
        # Nothing to stop; kept for interface compatibility.
        pass

    def can_receive(self, from_source=None):
        return True

    def handle_frame(self, frame, source=None):
        # Not used; frames are pushed via push_pcm.
        pass

    def push_pcm(self, pcm_bytes: bytes):
        try:
            samples = (
                np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            )
            if samples.size == 0:
                return
            samples = samples.reshape(-1, 1)
            frame = self.codec.encode(samples)
            if self.sink and self.sink.can_receive(from_source=self):
                self.sink.handle_frame(frame, self)
        except Exception as exc:  # noqa: BLE001
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
        except Exception as exc:  # noqa: BLE001
            RNS.log(f"WebAudioSink: failed to handle frame: {exc}", RNS.LOG_ERROR)


class WebAudioBridge:
    """Coordinates websocket audio transport with an active LXST telephone call."""

    def __init__(self, telephone_manager, config_manager):
        self.telephone_manager = telephone_manager
        self.config_manager = config_manager
        self.clients = set()
        self.tx_source: Optional[WebAudioSource] = None
        self.rx_sink: Optional[WebAudioSink] = None
        self.rx_tee: Optional[Tee] = None
        self.loop = asyncio.get_event_loop()
        self.lock = threading.Lock()

    def _tele(self):
        return getattr(self.telephone_manager, "telephone", None)

    def config_enabled(self):
        return (
            self.config_manager
            and hasattr(self.config_manager, "telephone_web_audio_enabled")
            and self.config_manager.telephone_web_audio_enabled.get()
        )

    def allow_fallback(self):
        return (
            self.config_manager
            and hasattr(self.config_manager, "telephone_web_audio_allow_fallback")
            and self.config_manager.telephone_web_audio_allow_fallback.get()
        )

    def attach_client(self, client):
        with self.lock:
            self.clients.add(client)
            tele = self._tele()
            if not tele or not tele.active_call:
                return False
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
                }
            )
        )

    def push_client_frame(self, pcm_bytes: bytes):
        with self.lock:
            if not self.tx_source:
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
        except Exception as exc:  # noqa: BLE001
            RNS.log(
                f"WebAudioBridge: failed to swap transmit path: {exc}", RNS.LOG_ERROR
            )

    def _ensure_rx_tee(self, tele):
        if self.rx_sink:
            return
        try:
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
        except Exception as exc:  # noqa: BLE001
            RNS.log(f"WebAudioBridge: failed to tee receive path: {exc}", RNS.LOG_ERROR)

    def _restore_host_audio(self):
        tele = self._tele()
        if not tele:
            return
        try:
            if hasattr(tele, "_Telephony__reconfigure_transmit_pipeline"):
                tele._Telephony__reconfigure_transmit_pipeline()
        except Exception:
            pass
        try:
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
        except Exception:
            pass
        self.tx_source = None
        self.rx_sink = None
        self.rx_tee = None

    def on_call_ended(self):
        with self.lock:
            self.tx_source = None
            self.rx_sink = None
            self.rx_tee = None
