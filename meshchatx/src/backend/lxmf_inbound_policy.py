# SPDX-License-Identifier: 0BSD

"""Pre-transfer inbound LXMF delivery resource policy.

LXMF 1.1 exposes delivery_resource_advertised on LXMRouter. Returning False
rejects the RNS resource before bytes are transferred. transfer_began cancels
as a fallback when peer identity was not available at advertise time.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import RNS

logger = logging.getLogger(__name__)

PolicyContextGetter = Callable[[], Any]


def source_hash_from_delivery_resource(resource) -> str | None:
    """Best-effort peer hash for an incoming LXMF delivery resource."""
    link = getattr(resource, "link", None)
    if link is None:
        return None

    identity = None
    if hasattr(link, "get_remote_identity"):
        try:
            identity = link.get_remote_identity()
        except Exception:
            identity = None

    if identity is None:
        destination = getattr(link, "destination", None)
        if destination is not None:
            identity = getattr(destination, "identity", None)

    if identity is None or not hasattr(identity, "hash"):
        return None

    raw_hash = identity.hash
    if isinstance(raw_hash, (bytes, bytearray)):
        return bytes(raw_hash).hex()
    return str(raw_hash)


def evaluate_inbound_delivery_resource_policy(
    app,
    ctx,
    resource,
) -> tuple[bool, str | None]:
    """Return (reject, reason). reject True means do not accept the transfer."""
    if ctx is None or not getattr(ctx, "config", None):
        return False, None

    source_hash = source_hash_from_delivery_resource(resource)

    if source_hash:
        try:
            if app.is_destination_blocked(source_hash, context=ctx):
                return True, "blocked"
        except Exception:
            logger.debug(
                "Inbound delivery resource blocklist check failed",
                exc_info=True,
            )

    is_contact = False
    if source_hash:
        try:
            is_contact = bool(app._is_contact(source_hash, context=ctx))
        except Exception:
            logger.debug(
                "Inbound delivery resource contact check failed",
                exc_info=True,
            )

    if ctx.config.block_all_from_strangers.get():
        if not source_hash or not is_contact:
            return True, "block_all_strangers"

    if ctx.config.block_attachments_from_strangers.get():
        if not source_hash or not is_contact:
            # Resource transfers carry whole LXMF payloads. Reject before download
            # because attachment fields are not visible in the advertisement.
            return True, "block_stranger_attachments"

    return False, None


def _cancel_resource(resource) -> None:
    try:
        if resource.status < RNS.Resource.COMPLETE:
            resource.cancel()
    except Exception:
        logger.debug("Failed to cancel inbound delivery resource", exc_info=True)


def install_lxmf_inbound_delivery_policy(
    router,
    app,
    context_getter: PolicyContextGetter,
) -> None:
    """Wrap LXMRouter delivery resource callbacks with MeshChatX inbound policy."""
    if router is None:
        return
    if not hasattr(router, "delivery_resource_advertised"):
        return
    if getattr(router, "_meshchatx_inbound_policy_installed", False) is True:
        return

    original_advertised = router.delivery_resource_advertised
    original_began = getattr(router, "delivery_resource_transfer_began", None)

    def delivery_resource_advertised(resource):
        ctx = context_getter()
        reject, reason = evaluate_inbound_delivery_resource_policy(app, ctx, resource)
        if reject:
            source_hash = source_hash_from_delivery_resource(resource)
            logger.info(
                "Rejecting inbound LXMF delivery resource before transfer (%s) from %s",
                reason,
                source_hash or "unknown",
            )
            return False
        return original_advertised(resource)

    def delivery_resource_transfer_began(resource):
        ctx = context_getter()
        reject, reason = evaluate_inbound_delivery_resource_policy(app, ctx, resource)
        if reject:
            source_hash = source_hash_from_delivery_resource(resource)
            logger.info(
                "Cancelling inbound LXMF delivery resource after transfer began (%s) from %s",
                reason,
                source_hash or "unknown",
            )
            _cancel_resource(resource)
            return
        if original_began is not None:
            original_began(resource)

    router.delivery_resource_advertised = delivery_resource_advertised
    if original_began is not None:
        router.delivery_resource_transfer_began = delivery_resource_transfer_began
    router._meshchatx_inbound_policy_installed = True
