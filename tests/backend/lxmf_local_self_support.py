# SPDX-License-Identifier: 0BSD

from unittest.mock import AsyncMock, MagicMock

import LXMF
import pytest

LOCAL_LXMF = "a1" * 16
REMOTE_PEER = "c3" * 16


def fake_lxmf_message():
    fake_lxm = MagicMock()
    fake_lxm.fields = {}
    fake_lxm.hash = MagicMock(hex=lambda: "d4" * 16)
    fake_lxm.source_hash = MagicMock(hex=lambda: LOCAL_LXMF)
    fake_lxm.destination_hash = MagicMock(hex=lambda: LOCAL_LXMF)
    fake_lxm.incoming = False
    fake_lxm.progress = 0
    fake_lxm.delivery_attempts = 0
    fake_lxm.next_delivery_attempt = None
    fake_lxm.rssi = None
    fake_lxm.snr = None
    fake_lxm.q = None
    fake_lxm.title = b""
    fake_lxm.timestamp = 1_700_000_000
    fake_lxm.state = LXMF.LXMessage.OUTBOUND
    fake_lxm.method = LXMF.LXMessage.DIRECT
    fake_lxm.get_fields = MagicMock(return_value={})
    fake_lxm.content = ""
    fake_lxm.include_ticket = False
    return fake_lxm


def lxmf_message_factory(*args, **kwargs):
    msg = fake_lxmf_message()
    if len(args) >= 3:
        raw = args[2]
        if isinstance(raw, bytes):
            msg.content = raw
        else:
            msg.content = (raw or "").encode("utf-8")
    return msg


@pytest.fixture
def local_self_app(mock_app):
    ctx = mock_app.current_context
    ctx.config.auto_send_failed_messages_to_propagation_node.set(False)
    ctx.message_router.delivery_link_available.return_value = True
    ctx.message_router.handle_outbound = MagicMock()
    ctx.local_lxmf_destination = MagicMock()
    ctx.local_lxmf_destination.hexhash = LOCAL_LXMF
    ctx.local_lxmf_destination.hash = bytes.fromhex(LOCAL_LXMF)
    mock_app.recall_identity = MagicMock(return_value=ctx.identity)
    mock_app.get_current_icon_hash = MagicMock(return_value=None)
    mock_app._await_transport_path = AsyncMock()
    mock_app._convert_webm_opus_to_ogg = MagicMock(side_effect=lambda b: b)
    mock_app.websocket_broadcast = AsyncMock()
    if getattr(mock_app, "reticulum", None) is not None:
        mock_app.reticulum.get_packet_rssi = MagicMock(return_value=None)
        mock_app.reticulum.get_packet_snr = MagicMock(return_value=None)
        mock_app.reticulum.get_packet_q = MagicMock(return_value=None)
    return mock_app
