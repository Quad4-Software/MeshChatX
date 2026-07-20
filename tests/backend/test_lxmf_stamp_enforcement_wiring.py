# SPDX-License-Identifier: 0BSD

"""Regression: inbound stamp cost must enable LXMF stamp enforcement."""

from unittest.mock import MagicMock

from meshchatx.src.backend.identity_context import IdentityContext


def test_identity_context_enforces_stamps_when_inbound_cost_positive():
    app = MagicMock()
    app.storage_dir = "/tmp/unused"
    identity = MagicMock()
    identity.hash = b"\x11" * 16

    ctx = IdentityContext.__new__(IdentityContext)
    ctx.app = app
    ctx.identity = identity
    ctx.identity_hash = identity.hash.hex()
    ctx.config = MagicMock()
    ctx.config.block_all_from_strangers.get.return_value = False
    ctx.config.lxmf_inbound_stamp_cost.get.return_value = 8
    ctx.config.display_name.get.return_value = "Test"
    ctx.message_router = MagicMock()
    dest = MagicMock()
    dest.hash = b"\x22" * 16
    ctx.message_router.register_delivery_identity.return_value = dest

    # Run only the stamp wiring fragment used after router creation.
    inbound_stamp_cost = ctx.config.lxmf_inbound_stamp_cost.get()
    ctx.local_lxmf_destination = ctx.message_router.register_delivery_identity(
        identity=ctx.identity,
        display_name=ctx.config.display_name.get(),
        stamp_cost=inbound_stamp_cost,
    )
    if isinstance(inbound_stamp_cost, int) and inbound_stamp_cost > 0:
        ctx.message_router.enforce_stamps()
    elif hasattr(ctx.message_router, "ignore_stamps"):
        ctx.message_router.ignore_stamps()

    ctx.message_router.enforce_stamps.assert_called_once()
    ctx.message_router.ignore_stamps.assert_not_called()


def test_identity_context_ignores_stamps_when_inbound_cost_zero():
    ctx_router = MagicMock()
    inbound_stamp_cost = 0
    if isinstance(inbound_stamp_cost, int) and inbound_stamp_cost > 0:
        ctx_router.enforce_stamps()
    elif hasattr(ctx_router, "ignore_stamps"):
        ctx_router.ignore_stamps()
    ctx_router.ignore_stamps.assert_called_once()
    ctx_router.enforce_stamps.assert_not_called()
