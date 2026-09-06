# SPDX-License-Identifier: 0BSD
"""Structured delivery diagnostics for LXMF send and delivery failure helptips."""

from __future__ import annotations

import contextlib
import time
from datetime import UTC, datetime
from typing import Any

import RNS

from meshchatx.src.backend import reticulum_pathfinding as rp
from meshchatx.src.backend.meshchat_utils import parse_lxmf_stamp_cost


def _lxmf_delivery_hash_bytes_for_path(app, destination_hash_hex: str) -> bytes:
    fallback = bytes.fromhex(destination_hash_hex)
    with contextlib.suppress(Exception):
        resolved_hex = app.get_lxmf_destination_hash_for_identity_hash(
            destination_hash_hex
        )
        if isinstance(resolved_hex, str):
            stripped = resolved_hex.strip()
            if len(stripped) == 32:
                return bytes.fromhex(stripped)
    return fallback


def _lxmf_delivery_hash_hex_for_path(app, destination_hash_hex: str) -> str:
    return _lxmf_delivery_hash_bytes_for_path(app, destination_hash_hex).hex()


def _announce_age_seconds(updated_at) -> int | None:
    if updated_at is None:
        return None
    try:
        if isinstance(updated_at, (int, float)):
            ts = float(updated_at)
        elif isinstance(updated_at, str):
            text = updated_at.strip()
            if not text:
                return None
            if text.isdigit():
                ts = float(text)
            else:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                ts = dt.timestamp()
        else:
            return None
        return max(0, int(time.time() - ts))
    except (TypeError, ValueError, OSError):
        return None


def _identity_hash_hex(app, input_hash_hex: str, delivery_hash_hex: str) -> str | None:
    identity = app.recall_identity(input_hash_hex)
    if identity is None and delivery_hash_hex != input_hash_hex:
        identity = app.recall_identity(delivery_hash_hex)
    if identity is None or not getattr(identity, "hash", None):
        return None
    try:
        return identity.hash.hex()
    except Exception:
        return None


def _peer_lxmf_announce(app, delivery_hash_hex: str, identity_hash_hex: str | None):
    announce = None
    with contextlib.suppress(Exception):
        announce = app.database.announces.get_announce_by_hash(delivery_hash_hex)
    if announce is None and identity_hash_hex:
        rows = app.database.announces.get_filtered_announces(
            aspect="lxmf.delivery",
            identity_hash=identity_hash_hex,
            limit=1,
        )
        if rows:
            announce = rows[0]
    if announce is None:
        return None
    return dict(announce)


def build_delivery_diagnostics(
    app,
    destination_hash_hex: str,
    *,
    failure_hint: str | None = None,
) -> dict[str, Any]:
    """Return a stable JSON snapshot for delivery failure helptips."""
    input_hash = destination_hash_hex.strip().lower()
    delivery_hash_hex = _lxmf_delivery_hash_hex_for_path(app, input_hash)
    delivery_hash_bytes = _lxmf_delivery_hash_bytes_for_path(app, input_hash)
    identity_hash_hex = _identity_hash_hex(app, input_hash, delivery_hash_hex)

    ctx = app.current_context
    now = time.time()

    auto_announce_enabled = False
    auto_announce_interval_seconds = 0
    last_announced_at = None
    if ctx is not None and ctx.config is not None:
        with contextlib.suppress(Exception):
            auto_announce_enabled = bool(ctx.config.auto_announce_enabled.get())
        with contextlib.suppress(Exception):
            auto_announce_interval_seconds = int(
                ctx.config.auto_announce_interval_seconds.get() or 0,
            )
        with contextlib.suppress(Exception):
            last_announced_at = ctx.config.last_announced_at.get()

    seconds_since_last_announce = None
    if last_announced_at is not None:
        with contextlib.suppress(Exception):
            seconds_since_last_announce = max(0, int(now - int(last_announced_at)))

    announce = _peer_lxmf_announce(app, delivery_hash_hex, identity_hash_hex)
    peer_announce_known = announce is not None
    peer_announce_updated_at = None
    peer_announce_age_seconds = None
    stamp_cost = None
    if announce is not None:
        peer_announce_updated_at = announce.get("updated_at") or announce.get(
            "created_at",
        )
        peer_announce_age_seconds = _announce_age_seconds(peer_announce_updated_at)
        with contextlib.suppress(Exception):
            stamp_cost = parse_lxmf_stamp_cost(announce.get("app_data"))

    has_path = False
    hops = None
    path_meta = {"path_stale": True, "path_unresponsive": False}
    with contextlib.suppress(Exception):
        has_path = bool(RNS.Transport.has_path(delivery_hash_bytes))
    if has_path:
        with contextlib.suppress(Exception):
            hops = RNS.Transport.hops_to(delivery_hash_bytes)
            if not isinstance(hops, int):
                hops = None
    with contextlib.suppress(Exception):
        path_meta = rp.path_metadata_for_api(delivery_hash_bytes)

    identity_known = False
    with contextlib.suppress(Exception):
        identity_known = app.recall_identity(input_hash) is not None
    if not identity_known and delivery_hash_hex != input_hash:
        with contextlib.suppress(Exception):
            identity_known = app.recall_identity(delivery_hash_hex) is not None

    auto_resend_on_announce = True
    propagation_fallback = False
    if ctx is not None and ctx.config is not None:
        with contextlib.suppress(Exception):
            auto_resend_on_announce = bool(
                ctx.config.auto_resend_failed_messages_when_announce_received.get(),
            )
        with contextlib.suppress(Exception):
            propagation_fallback = bool(
                ctx.config.auto_send_failed_messages_to_propagation_node.get(),
            )

    outbound_ticket_expiry = None
    message_router = getattr(app, "message_router", None)
    if message_router is not None:
        with contextlib.suppress(Exception):
            outbound_ticket_expiry = message_router.get_outbound_ticket_expiry(
                delivery_hash_bytes,
            )
        if outbound_ticket_expiry is not None and not isinstance(
            outbound_ticket_expiry,
            (int, float),
        ):
            outbound_ticket_expiry = None

    prop_configured = False
    prop_hash_hex = None
    prop_has_path = False
    prop_hops = None
    prop_path_meta = {"path_stale": True, "path_unresponsive": False}
    prop_is_local = False
    if message_router is not None:
        prop_bytes = None
        with contextlib.suppress(Exception):
            prop_bytes = message_router.get_outbound_propagation_node()
        if isinstance(prop_bytes, (bytes, bytearray)) and prop_bytes:
            prop_configured = True
            prop_hash_hex = bytes(prop_bytes).hex()
            local_propagation_destination = getattr(
                message_router,
                "propagation_destination",
                None,
            )
            local_hash = getattr(local_propagation_destination, "hash", None)
            if isinstance(local_hash, (bytes, bytearray)) and bytes(
                local_hash
            ) == bytes(
                prop_bytes,
            ):
                prop_is_local = True
                prop_has_path = True
                prop_path_meta = {"path_stale": False, "path_unresponsive": False}
            else:
                with contextlib.suppress(Exception):
                    prop_has_path = bool(RNS.Transport.has_path(bytes(prop_bytes)))
                if prop_has_path:
                    with contextlib.suppress(Exception):
                        prop_hops = RNS.Transport.hops_to(bytes(prop_bytes))
                        if not isinstance(prop_hops, int):
                            prop_hops = None
                with contextlib.suppress(Exception):
                    prop_path_meta = rp.path_metadata_for_api(bytes(prop_bytes))

    return {
        "peer": {
            "input_hash": input_hash,
            "delivery_hash": delivery_hash_hex,
            "identity_hash": identity_hash_hex,
        },
        "self": {
            "auto_announce_enabled": auto_announce_enabled,
            "auto_announce_interval_seconds": auto_announce_interval_seconds,
            "last_announced_at": last_announced_at,
            "seconds_since_last_announce": seconds_since_last_announce,
        },
        "peer_announce": {
            "known": peer_announce_known,
            "delivery_hash": delivery_hash_hex if peer_announce_known else None,
            "updated_at": peer_announce_updated_at,
            "age_seconds": peer_announce_age_seconds,
            "stamp_cost": stamp_cost,
            "outbound_ticket_expiry": outbound_ticket_expiry,
        },
        "path": {
            "has_path": has_path,
            "hops": hops,
            "path_stale": bool(path_meta.get("path_stale", True)),
            "path_unresponsive": bool(path_meta.get("path_unresponsive", False)),
        },
        "propagation_node": {
            "configured": prop_configured,
            "destination_hash": prop_hash_hex,
            "is_local": prop_is_local,
            "has_path": prop_has_path,
            "hops": prop_hops,
            "path_stale": bool(prop_path_meta.get("path_stale", True)),
            "path_unresponsive": bool(prop_path_meta.get("path_unresponsive", False)),
        },
        "recall": {
            "identity_known": identity_known,
        },
        "delivery_prefs": {
            "auto_resend_on_announce": auto_resend_on_announce,
            "propagation_fallback": propagation_fallback,
        },
        "failure_hint": failure_hint,
    }
