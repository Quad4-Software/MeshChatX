# SPDX-License-Identifier: 0BSD
"""Parse lxma:// contact URIs and bind destination hash to the public key."""

from __future__ import annotations

import RNS

_LXMA_PREFIX = "lxma://"
_DEST_HASH_HEX_LEN = 32
_PUBKEY_HEX_LENS = (64, 128)


def parse_lxma_uri(uri: str) -> tuple[str, bytes]:
    """Return destination hash hex and public-key bytes, or raise ValueError."""
    if not isinstance(uri, str):
        raise ValueError(
            "Invalid LXMA URI format, expected lxma://<destination_hash>:<public_key>",
        )
    raw = uri.strip()
    if not raw.lower().startswith(_LXMA_PREFIX):
        raise ValueError(
            "Invalid LXMA URI format, expected lxma://<destination_hash>:<public_key>",
        )
    payload = raw[len(_LXMA_PREFIX) :]
    if ":" not in payload:
        raise ValueError(
            "Invalid LXMA URI format, expected lxma://<destination_hash>:<public_key>",
        )
    destination_hash_hex, public_key_hex = payload.split(":", 1)
    destination_hash_hex = destination_hash_hex.strip().lower()
    public_key_hex = public_key_hex.strip().lower()
    if len(destination_hash_hex) != _DEST_HASH_HEX_LEN:
        raise ValueError(
            "Invalid LXMA destination hash length, expected 32 hex characters",
        )
    if len(public_key_hex) not in _PUBKEY_HEX_LENS:
        raise ValueError(
            "Invalid LXMA public key length, expected 64 or 128 hex characters",
        )
    try:
        bytes.fromhex(destination_hash_hex)
        public_key = bytes.fromhex(public_key_hex)
    except ValueError as exc:
        raise ValueError("Invalid LXMA URI hex encoding") from exc
    return destination_hash_hex, public_key


def lxmf_delivery_destination_hex(identity) -> str:
    """Return the lxmf.delivery destination hash for an identity."""
    return RNS.Destination.hash(identity, "lxmf", "delivery").hex()


def bind_lxma_contact(uri: str, identity_from_public_key) -> tuple[str, object]:
    """Load the URI public key and require dest hash to be its lxmf.delivery dest.

    Does not retry a truncated 32-byte prefix. Truncated material is not a
    valid RNS public key.
    """
    destination_hash_hex, public_key = parse_lxma_uri(uri)
    identity = identity_from_public_key(public_key)
    if identity is None:
        raise ValueError("Invalid LXMA public key")
    expected = lxmf_delivery_destination_hex(identity)
    if expected != destination_hash_hex:
        raise ValueError("LXMA destination hash does not match public key")
    return destination_hash_hex, identity
