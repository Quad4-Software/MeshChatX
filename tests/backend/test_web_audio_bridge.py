import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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


def test_web_audio_config_enabled_follows_telephone_web_audio_flag():
    cfg = MagicMock()
    cfg.telephone_web_audio_enabled.get.return_value = True
    bridge = WebAudioBridge(None, cfg)
    assert bridge.config_enabled() is True
    cfg.telephone_web_audio_enabled.get.return_value = False
    assert bridge.config_enabled() is False


def test_web_audio_config_disabled_without_config_manager():
    bridge = WebAudioBridge(None, None)
    assert not bridge.config_enabled()


def test_web_audio_allow_fallback_follows_config():
    cfg = MagicMock()
    cfg.telephone_web_audio_allow_fallback.get.return_value = True
    bridge = WebAudioBridge(None, cfg)
    assert bridge.allow_fallback() is True
    cfg.telephone_web_audio_allow_fallback.get.return_value = False
    assert bridge.allow_fallback() is False


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


def test_attach_client_returns_false_without_active_call():
    tele_mgr = MagicMock()
    tele_mgr.telephone = MagicMock()
    tele_mgr.telephone.active_call = None
    bridge = WebAudioBridge(tele_mgr, MagicMock())

    attached = bridge.attach_client(MagicMock())

    assert attached is False


@pytest.mark.asyncio
async def test_send_bytes_to_all_detaches_stale_clients():
    bridge = WebAudioBridge(MagicMock(), MagicMock())
    healthy_client = MagicMock()
    healthy_client.send_bytes = AsyncMock(return_value=None)

    stale_client = MagicMock()
    stale_client.send_bytes = AsyncMock(side_effect=RuntimeError("socket closed"))
    bridge.clients = {healthy_client, stale_client}

    await bridge._send_bytes_to_all(b"pcm")

    healthy_client.send_bytes.assert_awaited_once_with(b"pcm")
    stale_client.send_bytes.assert_awaited_once_with(b"pcm")
    assert stale_client not in bridge.clients
