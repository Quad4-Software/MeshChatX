# SPDX-License-Identifier: 0BSD

"""Pre-transfer inbound LXMF delivery resource policy.

LXMF 1.1 exposes delivery_resource_advertised on LXMRouter. Returning False
rejects the RNS resource before bytes are transferred. transfer_began cancels
as a fallback when peer identity becomes known after advertise.

LXMF senders typically identify only after a successful delivery (backchannel).
On a fresh inbound delivery link, get_remote_identity() is often None when the
resource is advertised. Treating unknown identity as stranger rejects contact
attachments and marks the sender REJECTED even though smaller packet messages
still land. Only reject when the peer identity is known and fails policy.
Unknown peers are accepted here and handled in on_lxmf_delivery (strip or drop).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import RNS

logger = logging.getLogger(__name__)

PolicyContextGetter = Callable[[], Any]


def source_hash_from_delivery_resource(resource) -> str | None:
    """Best-effort peer hash for an incoming LXMF delivery resource.

    Only the remote-identified initiator counts. On an inbound link,
    link.destination is the local lxmf.delivery destination, so
    destination.identity is our own identity. Treating it as the peer makes
    every unidentified sender look like a known stranger and rejects all
    resource-carried messages.
    """
    link = getattr(resource, "link", None)
    if link is None:
        return None

    identity = None
    if hasattr(link, "get_remote_identity"):
        try:
            identity = link.get_remote_identity()
        except Exception:
            identity = None

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
    """Return (reject, reason). reject True means do not accept the transfer.

    Unknown peer identity never rejects. LXMF often has no remote identity on
    the first resource advertise of a new delivery link. Post-delivery policy
    in on_lxmf_delivery still strips stranger attachments and drops block_all.
    """
    if ctx is None or not getattr(ctx, "config", None):
        return False, None

    source_hash = source_hash_from_delivery_resource(resource)
    if not source_hash:
        return False, None

    # fail_closed=False: a lookup error must never emit a positive block
    # verdict here. A false reject marks the sender REJECTED on a transient
    # database error, which is the false-rejection class this policy exists
    # to prevent. Dropping delivered payloads stays covered downstream.
    try:
        if app.is_destination_blocked(source_hash, context=ctx, fail_closed=False):
            return True, "blocked"
    except Exception:
        logger.debug(
            "Inbound delivery resource blocklist check failed",
            exc_info=True,
        )

    # A failed contact lookup leaves stranger status unknown. Stranger
    # rules reject on a positive verdict only. an unknown verdict falls
    # through so a transient error cannot bounce contact attachments.
    is_contact = None
    try:
        is_contact = bool(app._is_contact(source_hash, context=ctx))
    except Exception:
        logger.debug(
            "Inbound delivery resource contact check failed",
            exc_info=True,
        )

    if is_contact is None:
        return False, None

    if ctx.config.block_all_from_strangers.get() and not is_contact:
        return True, "block_all_strangers"

    if ctx.config.block_attachments_from_strangers.get() and not is_contact:
        # Resource transfers carry whole LXMF payloads. Reject known strangers
        # before download. Attachment fields are not visible in the advertisement.
        return True, "block_stranger_attachments"

    return False, None


def _cancel_resource(resource) -> None:
    try:
        if resource.status < RNS.Resource.COMPLETE:
            resource.cancel()
    except Exception:
        logger.debug("Failed to cancel inbound delivery resource", exc_info=True)


def _cancel_identified_link_resources(app, ctx, router, link) -> None:
    """Cancel this link's unfinished delivery resources that fail policy.

    Backchannel identification can resolve the sender after a resource was
    accepted while the peer was still unidentified. Re-run the policy over
    both the router's transfer-began resources and the link's RNS-level
    incoming resources (which also covers accepted-but-not-yet-begun
    transfers) so a now-known stranger's delivery is still cancelled before
    completion. Receiver-side cancel sends RESOURCE_RCL, which the sender's
    LXMF stack maps to a terminal REJECTED state, not a retry.
    """
    candidates = []
    resources = getattr(router, "incoming_delivery_resources", None)
    if isinstance(resources, dict):
        lock = getattr(router, "incoming_delivery_resource_lock", None)
        try:
            if lock is not None:
                with lock:
                    candidates.extend(resources.values())
            else:
                candidates.extend(list(resources.values()))
        except Exception:
            logger.debug(
                "Failed to snapshot inbound delivery resources",
                exc_info=True,
            )
    link_resources = getattr(link, "incoming_resources", None)
    if isinstance(link_resources, (list, tuple)):
        try:
            candidates.extend(link_resources)
        except Exception:
            logger.debug(
                "Failed to read link incoming resources",
                exc_info=True,
            )

    seen = set()
    complete_status = getattr(RNS.Resource, "COMPLETE", None)
    for resource in candidates:
        try:
            if resource is None or id(resource) in seen:
                continue
            seen.add(id(resource))
            if getattr(resource, "link", None) is not link:
                continue
            if complete_status is not None:
                status = getattr(resource, "status", None)
                if status is not None and status >= complete_status:
                    continue
            reject, reason = evaluate_inbound_delivery_resource_policy(
                app,
                ctx,
                resource,
            )
            if reject:
                source_hash = source_hash_from_delivery_resource(resource)
                logger.info(
                    "Cancelling inbound LXMF delivery resource after "
                    "identification (%s) from %s",
                    reason,
                    source_hash or "unknown",
                )
                _cancel_resource(resource)
        except Exception:
            # One malformed resource must not skip the rest of the scan.
            logger.debug(
                "Post-identification resource policy check failed",
                exc_info=True,
            )


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
    original_identified = getattr(router, "delivery_remote_identified", None)

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

    def delivery_remote_identified(link, identity):
        # Backchannel identification resolves the sender after resources
        # may already have been accepted while the peer was unidentified.
        # Re-run the policy over this link's unfinished transfers so a
        # now-known stranger's delivery is still cancelled before it
        # completes; a completed transfer can no longer be recalled and
        # stays covered by the post-delivery strip path.
        try:
            ctx = context_getter()
            if ctx is not None and getattr(ctx, "config", None):
                _cancel_identified_link_resources(app, ctx, router, link)
        except Exception:
            logger.debug(
                "Post-identification delivery policy check failed",
                exc_info=True,
            )
        if original_identified is not None:
            original_identified(link, identity)

    router.delivery_resource_advertised = delivery_resource_advertised
    if original_began is not None:
        router.delivery_resource_transfer_began = delivery_resource_transfer_began
    router.delivery_remote_identified = delivery_remote_identified
    router._meshchatx_inbound_policy_installed = True
