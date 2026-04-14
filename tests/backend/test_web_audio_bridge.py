import asyncio
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

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


def test_web_audio_source_pushes_frames():
    sink = _DummySink()
    src = WebAudioSource(target_frame_ms=60, sink=sink)
    zeros = np.zeros(160, dtype=np.int16)
    src.push_pcm(zeros.tobytes())
    assert len(sink.frames) == 1


def test_web_audio_sink_encodes_and_sends_bytes():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    sent = []

    async def _send_bytes(data):
        sent.append(data)

    sink = WebAudioSink(loop, _send_bytes)
    sink.handle_frame(np.zeros((160, 1), dtype=np.float32), None)
    loop.run_until_complete(asyncio.sleep(0.01))
    loop.close()
    assert sent, "expected audio bytes to be queued for sending"


@pytest.mark.asyncio
async def test_web_audio_bridge_lazy_loop():
    """Test that WebAudioBridge retrieves the loop lazily to avoid startup crashes."""
    mock_tele_mgr = MagicMock()
    mock_config_mgr = MagicMock()

    # Mock get_event_loop to simulate it not being available during init
    with patch("asyncio.get_event_loop", side_effect=RuntimeError("No running loop")):
        bridge = WebAudioBridge(mock_tele_mgr, mock_config_mgr)
        assert bridge._loop is None

        # Simulate a running loop
        current_loop = asyncio.get_running_loop()
        assert bridge.loop == current_loop
        assert bridge._loop == current_loop


def test_web_audio_bridge_asyncutils_fallback():
    """Test that WebAudioBridge falls back to AsyncUtils.main_loop if no loop is running."""
    from meshchatx.src.backend.async_utils import AsyncUtils

    AsyncUtils.main_loop = None
    AsyncUtils._pending_coroutines.clear()

    mock_loop = MagicMock(spec=asyncio.AbstractEventLoop)
    mock_loop.is_running.return_value = False
    AsyncUtils.set_main_loop(mock_loop)

    mock_tele_mgr = MagicMock()
    mock_config_mgr = MagicMock()

    with patch("asyncio.get_running_loop", side_effect=RuntimeError):
        bridge = WebAudioBridge(mock_tele_mgr, mock_config_mgr)
        assert bridge.loop == mock_loop
        assert bridge._loop == mock_loop
