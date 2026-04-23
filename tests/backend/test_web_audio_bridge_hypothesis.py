# SPDX-License-Identifier: 0BSD

"""Property-based tests for Web Audio bridge PCM paths (robustness, no uncaught exceptions)."""

import asyncio
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.web_audio_bridge import (
    WebAudioBridge,
    WebAudioSink,
    WebAudioSource,
)


class _DummySink:
    def __init__(self):
        self.frames = []

    def can_receive(self, from_source=None):
        return True

    def handle_frame(self, frame, source):
        self.frames.append(frame)


@settings(max_examples=200, deadline=None)
@given(pcm=st.binary(max_size=8192))
def test_web_audio_source_push_pcm_never_propagates(pcm):
    sink = _DummySink()
    src = WebAudioSource(target_frame_ms=60, sink=sink)
    with patch("meshchatx.src.backend.web_audio_bridge.RNS.log"):
        src.push_pcm(pcm)


@settings(max_examples=120, deadline=None)
@given(pcm=st.binary(max_size=8192))
def test_web_audio_bridge_push_client_frame_never_propagates(pcm):
    bridge = WebAudioBridge(MagicMock(), MagicMock())
    sink = _DummySink()
    bridge.tx_source = WebAudioSource(target_frame_ms=60, sink=sink)
    with patch("meshchatx.src.backend.web_audio_bridge.RNS.log"):
        bridge.push_client_frame(pcm)


@settings(max_examples=120, deadline=None)
@given(pcm=st.binary(max_size=8192))
def test_web_audio_source_push_pcm_sink_can_receive_false_never_propagates(pcm):
    sink = MagicMock()
    sink.can_receive.return_value = False
    src = WebAudioSource(target_frame_ms=60, sink=sink)
    with patch("meshchatx.src.backend.web_audio_bridge.RNS.log"):
        src.push_pcm(pcm)
    sink.handle_frame.assert_not_called()


@settings(max_examples=150, deadline=None)
@given(
    values=st.lists(
        st.floats(min_value=-4.0, max_value=4.0, allow_nan=False, allow_infinity=False),
        max_size=2048,
    ),
    shape=st.sampled_from(["col", "row", "empty"]),
)
def test_web_audio_sink_numpy_frame_never_propagates(values, shape):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    sent = []

    async def _send_bytes(data):
        sent.append(data)

    sink = WebAudioSink(loop, _send_bytes)
    if shape == "empty":
        arr = np.zeros((0, 1), dtype=np.float32)
    elif shape == "row":
        arr = (
            np.array(values, dtype=np.float32).reshape(1, -1)
            if values
            else np.zeros((1, 0), dtype=np.float32)
        )
    else:
        arr = (
            np.array(values, dtype=np.float32).reshape(-1, 1)
            if values
            else np.zeros((0, 1), dtype=np.float32)
        )

    with patch("meshchatx.src.backend.web_audio_bridge.RNS.log"):
        sink.handle_frame(arr, None)
    loop.run_until_complete(asyncio.sleep(0.05))
    loop.close()


@settings(max_examples=100, deadline=None)
@given(raw=st.binary(max_size=1024))
def test_web_audio_sink_bytes_frame_never_propagates(raw):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    sent = []

    async def _send_bytes(data):
        sent.append(data)

    sink = WebAudioSink(loop, _send_bytes)
    with patch("meshchatx.src.backend.web_audio_bridge.RNS.log"):
        sink.handle_frame(raw, None)
    loop.run_until_complete(asyncio.sleep(0.05))
    loop.close()


@pytest.mark.asyncio
@settings(max_examples=80, deadline=None)
@given(
    values=st.lists(
        st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False),
        max_size=1024,
    ),
)
async def test_web_audio_sink_running_loop_numpy_never_propagates(values):
    sent = []

    async def _send_bytes(data):
        sent.append(data)

    sink = WebAudioSink(asyncio.get_running_loop(), _send_bytes)
    arr = (
        np.array(values, dtype=np.float32).reshape(-1, 1)
        if values
        else np.zeros((0, 1), dtype=np.float32)
    )
    with patch("meshchatx.src.backend.web_audio_bridge.RNS.log"):
        sink.handle_frame(arr, None)
    await asyncio.sleep(0.05)
