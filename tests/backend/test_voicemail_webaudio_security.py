# SPDX-License-Identifier: 0BSD

"""Fuzzing and security tests for voicemail isolation and web audio guards."""

from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.web_audio_bridge import WebAudioBridge


@settings(deadline=None)
@given(pcm=st.binary(min_size=0, max_size=4096))
def test_web_audio_bridge_push_client_frame_never_crashes(pcm):
    """Random PCM bytes must not crash push_client_frame, even during voicemail."""
    tele_mgr = MagicMock()
    tele_mgr.is_voicemail_session_active = True
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    bridge.tx_source = MagicMock()
    try:
        bridge.push_client_frame(pcm)
    except Exception:
        pytest.fail("push_client_frame raised an exception")


@settings(deadline=None)
@given(pcm=st.binary(min_size=0, max_size=4096))
def test_web_audio_bridge_push_client_frame_forwards_when_not_voicemail(pcm):
    """PCM bytes must be forwarded when not in a voicemail session."""
    tele_mgr = MagicMock()
    tele_mgr.is_voicemail_session_active = False
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    mock_tx = MagicMock()
    bridge.tx_source = mock_tx
    try:
        bridge.push_client_frame(pcm)
    except Exception:
        pytest.fail("push_client_frame raised an exception")
    if pcm:
        mock_tx.push_pcm.assert_called_once_with(pcm)


def test_web_audio_bridge_attach_client_refuses_without_active_call():
    tele = MagicMock()
    tele.active_call = None
    tele_mgr = MagicMock()
    tele_mgr.telephone = tele
    tele_mgr.is_voicemail_session_active = False
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    assert bridge.attach_client(MagicMock()) is False


def test_web_audio_bridge_attach_client_refuses_during_voicemail():
    tele = MagicMock()
    tele.active_call = object()
    tele_mgr = MagicMock()
    tele_mgr.telephone = tele
    tele_mgr.is_voicemail_session_active = True
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    assert bridge.attach_client(MagicMock()) is False


def test_web_audio_bridge_ensure_remote_tx_skips_without_telephone():
    bridge = WebAudioBridge(MagicMock(), MagicMock())
    bridge._ensure_remote_tx(MagicMock())
    assert bridge.tx_source is None


def test_web_audio_bridge_ensure_remote_tx_skips_during_voicemail():
    tele = MagicMock()
    tele_mgr = MagicMock()
    tele_mgr.is_voicemail_session_active = True
    bridge = WebAudioBridge(tele_mgr, MagicMock())
    bridge._ensure_remote_tx(tele)
    assert bridge.tx_source is None
