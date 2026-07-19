"""Peer link lifecycle helpers."""

from __future__ import annotations

import time
from collections.abc import Callable

import RNS

from rns_filesync.constants import (
    APP_NAME,
    ASPECT,
    LINK_TIMEOUT_DEFAULT,
    PATH_TIMEOUT_DEFAULT,
)


def parse_hash(value: str | bytes) -> bytes:
    if isinstance(value, bytes):
        if len(value) == RNS.Reticulum.TRUNCATED_HASHLENGTH // 8:
            return value
        raise ValueError("invalid identity/destination hash length")
    cleaned = value.lower().replace(":", "").strip()
    raw = bytes.fromhex(cleaned)
    expected = RNS.Reticulum.TRUNCATED_HASHLENGTH // 8
    if len(raw) != expected:
        raise ValueError(f"hash must be {expected} bytes")
    return raw


def hex_hash(value: bytes) -> str:
    return RNS.hexrep(value, delimit=False)


def resolve_peer_identity(peer_hash: bytes):
    """Resolve an identity from identity hash or destination hash."""
    identity = RNS.Identity.recall(peer_hash, from_identity_hash=True)
    if identity is not None:
        return identity, "identity"

    identity = RNS.Identity.recall(peer_hash, from_identity_hash=False)
    if identity is not None:
        return identity, "destination"

    # Same-process local destinations may not yet be in known_destinations.
    for destination in list(RNS.Transport.destinations):
        try:
            if destination.identity is None:
                continue
            if destination.identity.hash == peer_hash:
                identity = RNS.Identity(create_keys=False)
                identity.load_public_key(destination.identity.get_public_key())
                return identity, "local"
            if destination.hash == peer_hash:
                identity = RNS.Identity(create_keys=False)
                identity.load_public_key(destination.identity.get_public_key())
                return identity, "local_destination"
        except Exception:
            continue

    return None, None


def is_local_destination(destination_hash: bytes) -> bool:
    """Return True when the destination is registered on this Reticulum instance."""
    for destination in list(RNS.Transport.destinations):
        try:
            if destination.hash == destination_hash:
                return True
        except Exception:
            continue
    destinations_map = getattr(RNS.Transport, "destinations_map", None)
    if destinations_map is not None and destination_hash in destinations_map:
        return True
    return False


def wait_for_path(
    destination_hash: bytes,
    timeout: float = PATH_TIMEOUT_DEFAULT,
) -> bool:
    if RNS.Transport.has_path(destination_hash) or is_local_destination(
        destination_hash,
    ):
        return True
    RNS.Transport.request_path(destination_hash)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if RNS.Transport.has_path(destination_hash) or is_local_destination(
            destination_hash,
        ):
            return True
        time.sleep(0.2)
    return RNS.Transport.has_path(destination_hash) or is_local_destination(
        destination_hash,
    )


def create_outbound_destination(peer_identity):
    return RNS.Destination(
        peer_identity,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        APP_NAME,
        ASPECT,
    )


def establish_link(
    destination,
    *,
    established_callback: Callable | None = None,
    closed_callback: Callable | None = None,
    timeout: float = LINK_TIMEOUT_DEFAULT,
):
    link = RNS.Link(
        destination,
        established_callback=established_callback,
        closed_callback=closed_callback,
    )
    deadline = time.time() + timeout
    while link.status not in (RNS.Link.ACTIVE, RNS.Link.CLOSED):
        if time.time() > deadline:
            try:
                link.teardown()
            except Exception:
                pass
            return None
        time.sleep(0.05)
    if link.status != RNS.Link.ACTIVE:
        return None
    return link


def peer_id_from_link(link) -> str | None:
    try:
        remote = link.get_remote_identity()
        if remote is not None:
            return hex_hash(remote.hash)
    except Exception:
        pass
    return None


def destination_id_from_link(link) -> str | None:
    try:
        return hex_hash(link.destination.hash)
    except Exception:
        return None
