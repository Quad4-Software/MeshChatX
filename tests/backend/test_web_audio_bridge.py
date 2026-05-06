# SPDX-License-Identifier: 0BSD

import asyncio
import json
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


def test_web_audio_source_empty_pcm_does_not_push():
    sink = _DummySink()
    src = WebAudioSource(target_frame_ms=60, sink=sink)
    src.push_pcm(b"")
    assert len(sink.frames) == 0


def test_web_audio_source_respects_sink_can_receive_false():
    sink = MagicMock()
    sink.can_receive.return_value = False
    src = WebAudioSource(target_frame_ms=60, sink=sink)
    src.push_pcm(np.zeros(8, dtype=np.int16).tobytes())
    sink.handle_frame.assert_not_called()


def test_web_audio_source_can_receive_and_handle_frame_are_safe():
    sink = _DummySink()
    src = WebAudioSource(target_frame_ms=0, sink=sink)
    assert src.can_receive() is True
    src.handle_frame(None, None)


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
async def test_web_audio_sink_forwards_non_numpy_frame_unchanged():
    sent = []

    async def _send_bytes(data):
        sent.append(data)

    sink = WebAudioSink(asyncio.get_running_loop(), _send_bytes)
    sink.handle_frame(b"\xff\x00", MagicMock())
    await asyncio.sleep(0.02)
    assert sent == [b"\xff\x00"]


@pytest.mark.asyncio
async def test_web_audio_sink_numpy_frame_clips_to_int16_range():
    sent = []

    async def _send_bytes(data):
        sent.append(data)

    sink = WebAudioSink(asyncio.get_running_loop(), _send_bytes)
    arr = np.array([[2.0], [-2.0]], dtype=np.float32)
    sink.handle_frame(arr, None)
    await asyncio.sleep(0.02)
    assert len(sent) == 1
    out = np.frombuffer(sent[0], dtype=np.int16)
    assert out[0] == 32767
    assert out[1] == -32767


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


def test_web_audio_config_enabled_false_without_flag_attribute():
    class _Cfg:
        pass

    bridge = WebAudioBridge(None, _Cfg())
    assert bridge.config_enabled() is False


def test_web_audio_allow_fallback_follows_config():
    cfg = MagicMock()
    cfg.telephone_web_audio_allow_fallback.get.return_value = True
    bridge = WebAudioBridge(None, cfg)
    assert bridge.allow_fallback() is True
    cfg.telephone_web_audio_allow_fallback.get.return_value = False
    assert bridge.allow_fallback() is False


def test_web_audio_allow_fallback_false_without_flag_attribute():
    class _Cfg:
        pass

    bridge = WebAudioBridge(None, _Cfg())
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

    mock_client = MagicMock()
    attached = bridge.attach_client(mock_client)

    assert attached is False
    assert mock_client not in bridge.clients


class _TeleMgrNoTelephone:
    """Telephone manager shape without a ``telephone`` attribute (edge case)."""


def test_tele_returns_none_when_manager_has_no_telephone():
    bridge = WebAudioBridge(_TeleMgrNoTelephone(), MagicMock())
    assert bridge._tele() is None


def test_push_client_frame_no_op_without_tx_source():
    bridge = WebAudioBridge(MagicMock(), MagicMock())
    bridge.tx_source = None
    bridge.push_client_frame(b"ignored")


def test_push_client_frame_forwards_to_tx_source():
    tele_mgr = MagicMock()
    tele_mgr.is_voicemail_session_active = False
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    mock_tx = MagicMock()
    bridge.tx_source = mock_tx
    bridge.push_client_frame(b"\x01\x02")
    mock_tx.push_pcm.assert_called_once_with(b"\x01\x02")


def test_push_client_frame_drops_during_voicemail():
    tele_mgr = MagicMock()
    tele_mgr.is_voicemail_session_active = True
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    mock_tx = MagicMock()
    bridge.tx_source = mock_tx
    bridge.push_client_frame(b"\x01\x02")
    mock_tx.push_pcm.assert_not_called()


def test_attach_client_returns_false_during_voicemail():
    tele = MagicMock()
    tele.active_call = object()
    tele_mgr = MagicMock()
    tele_mgr.telephone = tele
    tele_mgr.is_voicemail_session_active = True
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    assert bridge.attach_client(MagicMock()) is False


def test_ensure_remote_tx_skips_during_voicemail():
    tele = MagicMock()
    tele_mgr = MagicMock()
    tele_mgr.telephone = tele
    tele_mgr.is_voicemail_session_active = True
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    bridge._ensure_remote_tx(tele)
    assert bridge.tx_source is None


@pytest.mark.asyncio
async def test_send_status_uses_tele_frame_ms():
    tele = MagicMock()
    tele.target_frame_time_ms = 52
    tele_mgr = MagicMock()
    tele_mgr.telephone = tele
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    client = AsyncMock()
    await bridge.send_status(client)
    payload = json.loads(client.send_str.await_args.args[0])
    assert payload == {"type": "web_audio.ready", "frame_ms": 52}


@pytest.mark.asyncio
async def test_send_status_defaults_frame_ms_when_missing():
    tele = MagicMock(spec=["active_call"])
    tele_mgr = MagicMock()
    tele_mgr.telephone = tele
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    client = AsyncMock()
    await bridge.send_status(client)
    payload = json.loads(client.send_str.await_args.args[0])
    assert payload["type"] == "web_audio.ready"
    assert payload["frame_ms"] == 60


@pytest.mark.asyncio
async def test_send_status_defaults_when_no_telephone():
    bridge = WebAudioBridge(_TeleMgrNoTelephone(), MagicMock())
    client = AsyncMock()
    await bridge.send_status(client)
    payload = json.loads(client.send_str.await_args.args[0])
    assert payload == {"type": "web_audio.ready", "frame_ms": 60}


@patch("meshchatx.src.backend.web_audio_bridge.Pipeline")
def test_attach_client_success_wires_telephony_and_dedupes_client(mock_pipeline_cls):
    """LXST ``Pipeline`` validates sources; mock it so we only assert bridge wiring."""
    mock_receive_pipeline = MagicMock()
    mock_pipeline_cls.return_value = mock_receive_pipeline
    tele = MagicMock()
    tele.active_call = object()
    tele.target_frame_time_ms = 48
    tele.audio_input = MagicMock()
    tele.transmit_mixer = MagicMock()
    tele.transmit_mixer.should_run = False
    tele.audio_output = MagicMock()
    tele.receive_mixer = MagicMock()
    tele.receive_pipeline = None
    tele_mgr = MagicMock()
    tele_mgr.telephone = tele
    tele_mgr.is_voicemail_session_active = False
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    client = MagicMock()

    assert bridge.attach_client(client) is True
    assert client in bridge.clients
    assert isinstance(bridge.tx_source, WebAudioSource)
    assert tele.audio_input is bridge.tx_source
    tele.transmit_mixer.start.assert_called_once()
    assert bridge.rx_tee is not None
    assert tele.audio_output is bridge.rx_tee
    assert tele.receive_pipeline is mock_receive_pipeline
    mock_receive_pipeline.start.assert_called_once()
    mock_pipeline_cls.assert_called_once()
    call_kw = mock_pipeline_cls.call_args.kwargs
    assert call_kw["source"] is tele.receive_mixer
    assert call_kw["sink"] is bridge.rx_tee

    assert bridge.attach_client(client) is True
    assert len(bridge.clients) == 1
    mock_pipeline_cls.assert_called_once()


@patch("meshchatx.src.backend.web_audio_bridge.Pipeline")
def test_attach_rx_tee_includes_base_sink_when_audio_output_exists(mock_pipeline_cls):
    mock_pipeline_cls.return_value = MagicMock()
    base_out = MagicMock()
    tele = MagicMock()
    tele.active_call = object()
    tele.target_frame_time_ms = 60
    tele.audio_input = None
    tele.transmit_mixer = MagicMock()
    tele.transmit_mixer.should_run = True
    tele.audio_output = base_out
    tele.receive_mixer = MagicMock()
    tele.receive_pipeline = None
    tele_mgr = MagicMock()
    tele_mgr.telephone = tele
    tele_mgr.is_voicemail_session_active = False
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    assert bridge.attach_client(MagicMock()) is True
    assert len(bridge.rx_tee.sinks) == 2
    assert bridge.rx_tee.sinks[0] is base_out
    assert bridge.rx_tee.sinks[1] is bridge.rx_sink


@patch("meshchatx.src.backend.web_audio_bridge.Pipeline")
def test_attach_rx_tee_single_sink_when_no_base_audio_output(mock_pipeline_cls):
    mock_pipeline_cls.return_value = MagicMock()
    tele = MagicMock()
    tele.active_call = object()
    tele.target_frame_time_ms = 60
    tele.audio_input = None
    tele.transmit_mixer = MagicMock()
    tele.transmit_mixer.should_run = True
    tele.audio_output = None
    tele.receive_mixer = MagicMock()
    tele.receive_pipeline = None
    tele_mgr = MagicMock()
    tele_mgr.telephone = tele
    tele_mgr.is_voicemail_session_active = False
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    assert bridge.attach_client(MagicMock()) is True
    assert len(bridge.rx_tee.sinks) == 1
    assert bridge.rx_tee.sinks[0] is bridge.rx_sink


def test_attach_client_returns_false_when_telephone_is_none():
    tele_mgr = MagicMock()
    tele_mgr.telephone = None
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    c = MagicMock()
    assert bridge.attach_client(c) is False
    assert c not in bridge.clients


def test_detach_client_ignores_unknown_client():
    bridge = WebAudioBridge(MagicMock(), MagicMock())
    bridge.clients.add(MagicMock())
    with patch.object(bridge, "_restore_host_audio") as restore:
        bridge.detach_client(MagicMock())
        restore.assert_not_called()


def test_detach_non_last_client_does_not_restore_host_audio():
    cfg = MagicMock()
    cfg.telephone_web_audio_allow_fallback.get.return_value = True
    bridge = WebAudioBridge(MagicMock(), cfg)
    c1, c2 = MagicMock(), MagicMock()
    bridge.clients.update({c1, c2})
    with patch.object(bridge, "_restore_host_audio") as restore:
        bridge.detach_client(c1)
        restore.assert_not_called()
        assert c2 in bridge.clients


def test_detach_last_client_restores_when_allow_fallback_enabled():
    cfg = MagicMock()
    cfg.telephone_web_audio_allow_fallback.get.return_value = True
    bridge = WebAudioBridge(MagicMock(), cfg)
    c = MagicMock()
    bridge.clients.add(c)
    with patch.object(bridge, "_restore_host_audio") as restore:
        bridge.detach_client(c)
        restore.assert_called_once()
    assert len(bridge.clients) == 0


def test_detach_last_client_skips_restore_when_allow_fallback_disabled():
    cfg = MagicMock()
    cfg.telephone_web_audio_allow_fallback.get.return_value = False
    bridge = WebAudioBridge(MagicMock(), cfg)
    c = MagicMock()
    bridge.clients.add(c)
    with patch.object(bridge, "_restore_host_audio") as restore:
        bridge.detach_client(c)
        restore.assert_not_called()


def test_on_call_ended_clears_clients_and_pipeline_handles():
    bridge = WebAudioBridge(MagicMock(), MagicMock())
    bridge.clients.update({MagicMock(), MagicMock()})
    bridge.tx_source = MagicMock()
    bridge.rx_sink = MagicMock()
    bridge.rx_tee = MagicMock()
    bridge.on_call_ended()
    assert len(bridge.clients) == 0
    assert bridge.tx_source is None
    assert bridge.rx_sink is None
    assert bridge.rx_tee is None


def test_restore_host_audio_no_telephone_is_safe():
    bridge = WebAudioBridge(MagicMock(), MagicMock())
    bridge.telephone_manager = MagicMock()
    bridge.telephone_manager.telephone = None
    bridge.rx_tee = MagicMock()
    bridge._restore_host_audio()


@patch("meshchatx.src.backend.web_audio_bridge.RNS.log")
def test_ensure_remote_tx_swallows_source_init_failure(mock_log):
    tele = MagicMock()
    tele.transmit_mixer = MagicMock()
    tele.transmit_mixer.should_run = True
    tele_mgr = MagicMock()
    tele_mgr.is_voicemail_session_active = False
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    bridge.tx_source = None
    with patch(
        "meshchatx.src.backend.web_audio_bridge.WebAudioSource",
        side_effect=RuntimeError("init failed"),
    ):
        bridge._ensure_remote_tx(tele)
    assert bridge.tx_source is None
    mock_log.assert_called()


@patch("meshchatx.src.backend.web_audio_bridge.RNS.log")
def test_ensure_rx_tee_swallows_web_audio_sink_init_failure(mock_log):
    tele = MagicMock()
    tele.audio_output = None
    tele.receive_mixer = MagicMock()
    tele.receive_pipeline = None
    bridge = WebAudioBridge(MagicMock(), MagicMock())
    bridge.rx_sink = None
    with patch(
        "meshchatx.src.backend.web_audio_bridge.WebAudioSink",
        side_effect=RuntimeError("sink init failed"),
    ):
        bridge._ensure_rx_tee(tele)
    assert bridge.rx_sink is None
    mock_log.assert_called()


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
