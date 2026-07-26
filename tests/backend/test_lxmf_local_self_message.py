# SPDX-License-Identifier: 0BSD

from unittest.mock import AsyncMock, MagicMock, patch

import LXMF
import pytest

LOCAL_LXMF = "a1" * 16
REMOTE_PEER = "c3" * 16


def _fake_lxmf_message():
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


def _lxmf_message_factory(*args, **kwargs):
    msg = _fake_lxmf_message()
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


def test_is_self_lxmf_destination_by_lxmf_hash(local_self_app):
    app = local_self_app
    assert app._is_self_lxmf_destination(LOCAL_LXMF) is True
    assert app._is_self_lxmf_destination(LOCAL_LXMF.upper()) is True
    assert app._is_self_lxmf_destination(REMOTE_PEER) is False


def test_is_self_lxmf_destination_by_identity_hash(local_self_app):
    app = local_self_app
    identity_hex = app.current_context.identity.hash.hex()
    assert app._is_self_lxmf_destination(identity_hex) is True


@pytest.mark.asyncio
async def test_send_to_self_persists_delivered_local_without_router(local_self_app):
    app = local_self_app
    fake_destination = MagicMock()
    fake_destination.hash = bytes.fromhex(LOCAL_LXMF)
    app.db_upsert_lxmf_message = MagicMock()

    with (
        patch("meshchatx.meshchat.RNS.Destination", return_value=fake_destination),
        patch("meshchatx.meshchat.LXMF.LXMessage", side_effect=_lxmf_message_factory),
        patch(
            "meshchatx.src.backend.lxmf_utils.lxmf_message_solving_stamps",
            return_value=False,
        ),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        await app.send_message(
            destination_hash=LOCAL_LXMF,
            content="note to self",
        )

    app._await_transport_path.assert_not_called()
    app.current_context.message_router.handle_outbound.assert_not_called()
    app.db_upsert_lxmf_message.assert_called_once()
    upsert_kw = app.db_upsert_lxmf_message.call_args.kwargs
    assert upsert_kw.get("state_override") == "delivered"
    assert upsert_kw.get("method_override") == "local"
    app.websocket_broadcast.assert_awaited()
    payload = app.websocket_broadcast.await_args[0][0]
    assert "local" in payload and "delivered" in payload


@pytest.mark.asyncio
async def test_send_to_self_by_identity_hash(local_self_app):
    app = local_self_app
    identity_hex = app.current_context.identity.hash.hex()
    app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=LOCAL_LXMF)
    fake_destination = MagicMock()
    fake_destination.hash = bytes.fromhex(LOCAL_LXMF)
    app.db_upsert_lxmf_message = MagicMock()

    with (
        patch("meshchatx.meshchat.RNS.Destination", return_value=fake_destination),
        patch("meshchatx.meshchat.LXMF.LXMessage", side_effect=_lxmf_message_factory),
        patch(
            "meshchatx.src.backend.lxmf_utils.lxmf_message_solving_stamps",
            return_value=False,
        ),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        await app.send_message(
            destination_hash=identity_hex,
            content="via identity hash",
        )

    app.current_context.message_router.handle_outbound.assert_not_called()
    assert app.db_upsert_lxmf_message.call_args.kwargs.get("method_override") == "local"


@pytest.mark.asyncio
async def test_send_to_self_rejects_propagated(local_self_app):
    app = local_self_app
    with pytest.raises(ValueError, match="yourself"):
        await app.send_message(
            destination_hash=LOCAL_LXMF,
            content="nope",
            delivery_method="propagated",
        )
