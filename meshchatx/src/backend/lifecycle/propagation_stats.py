# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: propagation_stats."""

from __future__ import annotations

import contextlib
from typing import Any

from meshchatx.src.backend.meshchat_utils import list_inbound_deliveries

# ruff: noqa: F821


def get_local_propagation_node_stats(app: Any, context=None):
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v
    ctx = context or app.current_context
    if not ctx:
        return None

    router = ctx.message_router
    if not router:
        return None

    is_running = bool(getattr(router, "propagation_node", False))
    stats = None
    if is_running:
        with contextlib.suppress(Exception):
            stats = router.compile_stats()

    def _numeric(value, default=0):
        return value if isinstance(value, (int, float)) else default

    destination_hash_raw = getattr(
        router.propagation_destination,
        "hexhash",
        None,
    )
    if destination_hash_raw is None:
        destination_hash_raw = getattr(
            router.propagation_destination,
            "hash",
            None,
        )
    if isinstance(destination_hash_raw, bytes):
        destination_hash = destination_hash_raw.hex()
    elif isinstance(destination_hash_raw, str):
        destination_hash = destination_hash_raw
    else:
        destination_hash = None

    message_store = stats.get("messagestore", {}) if isinstance(stats, dict) else {}
    clients = stats.get("clients", {}) if isinstance(stats, dict) else {}
    peers = stats.get("peers", {}) if isinstance(stats, dict) else {}
    uptime = _numeric(stats.get("uptime", 0)) if isinstance(stats, dict) else 0
    peer_rx_bytes = 0
    peer_tx_bytes = 0
    if isinstance(peers, dict):
        for peer_stats in peers.values():
            if not isinstance(peer_stats, dict):
                continue
            peer_rx_bytes += int(_numeric(peer_stats.get("rx_bytes", 0)))
            peer_tx_bytes += int(_numeric(peer_stats.get("tx_bytes", 0)))
    unpeered_rx_bytes = (
        int(_numeric(stats.get("unpeered_propagation_rx_bytes", 0)))
        if isinstance(stats, dict)
        else 0
    )
    delivery_limit = (
        _numeric(stats.get("delivery_limit", 0))
        if isinstance(stats, dict)
        else _numeric(getattr(router, "delivery_per_transfer_limit", 0))
    )
    propagation_limit = (
        _numeric(stats.get("propagation_limit", 0))
        if isinstance(stats, dict)
        else _numeric(getattr(router, "propagation_per_transfer_limit", 0))
    )
    sync_limit = (
        _numeric(stats.get("sync_limit", 0))
        if isinstance(stats, dict)
        else _numeric(getattr(router, "propagation_per_sync_limit", 0))
    )
    result = {
        "is_running": is_running,
        "identity_hash": ctx.identity.hash.hex(),
        "destination_hash": destination_hash,
        "uptime_seconds": int(uptime) if uptime else 0,
        "messagestore_count": message_store.get("count", 0),
        "messagestore_bytes": message_store.get("bytes", 0),
        "messagestore_limit_bytes": message_store.get("limit"),
        "client_messages_received": clients.get(
            "client_propagation_messages_received",
            0,
        ),
        "client_messages_served": clients.get(
            "client_propagation_messages_served",
            0,
        ),
        "rx_bytes": peer_rx_bytes + unpeered_rx_bytes,
        "tx_bytes": peer_tx_bytes,
        "unpeered_rx_bytes": unpeered_rx_bytes,
        "static_peers": stats.get("static_peers", 0) if isinstance(stats, dict) else 0,
        "discovered_peers": (
            stats.get("discovered_peers", 0) if isinstance(stats, dict) else 0
        ),
        "total_peers": stats.get("total_peers", 0) if isinstance(stats, dict) else 0,
        "max_peers": stats.get("max_peers") if isinstance(stats, dict) else None,
        "delivery_limit_bytes": int(delivery_limit * 1000),
        "propagation_limit_bytes": int(propagation_limit * 1000),
        "sync_limit_bytes": int(sync_limit * 1000),
        "target_stamp_cost": _numeric(
            (
                stats.get("target_stamp_cost", 0)
                if isinstance(stats, dict)
                else getattr(router, "propagation_stamp_cost", 0)
            ),
        ),
        "inbound_delivery_count": 0,
        "inbound_deliveries": [],
        "max_inbound_syncs": int(
            getattr(router, "propagation_max_inbound_syncs", 0) or 0,
        ),
        "sequential_validation": bool(
            getattr(router, "propagation_sequential_validation", True),
        ),
        "static_peers_bypass_sequential": not bool(
            getattr(router, "propagation_static_peer_sequential", False),
        ),
    }
    inbound_deliveries = list_inbound_deliveries(router)
    result["inbound_deliveries"] = inbound_deliveries
    result["inbound_delivery_count"] = len(inbound_deliveries)
    return result
