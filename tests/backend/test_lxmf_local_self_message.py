# SPDX-License-Identifier: 0BSD

from unittest.mock import MagicMock, patch

import pytest

from tests.backend.lxmf_local_self_support import (
    LOCAL_LXMF,
    REMOTE_PEER,
    lxmf_message_factory,
)


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
        patch("meshchatx.meshchat.LXMF.LXMessage", side_effect=lxmf_message_factory),
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
        patch("meshchatx.meshchat.LXMF.LXMessage", side_effect=lxmf_message_factory),
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
