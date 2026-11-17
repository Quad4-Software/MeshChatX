# SPDX-License-Identifier: 0BSD
"""Signed update-manifest envelope (rnid-compatible RSG).

The release pipeline signs a compact msgpack manifest into
"signature(64B) + umsgpack({hashtype, hash, meta:{signer, pubkey},
message})". Clients verify against a pinned or user-configured signer hash
set. The public key travels inside the envelope's meta block.

Schema 2 manifests carry channel, issued_at, valid_until,
min_supported_version and per-artifact blockmap metadata. The message
payload is umsgpack bytes, not JSON, to keep the signed object small.
update.json written next to update.rsm is a human-readable debug view.

Used by scripts/build/update_manifest.py (signing) and
meshchatx.src.backend.update_manager (verification).
"""

from __future__ import annotations

import hashlib
import json

SCHEMA = 2
APP_ID = "reticulum-meshchatx"


def canonical_json(manifest: dict) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_bytes(manifest: dict) -> bytes:
    """Compact wire encoding of the signed payload (msgpack)."""
    from RNS.vendor import umsgpack as mp

    return mp.packb(manifest, use_bin_type=True)


def manifest_from_bytes(data: bytes) -> dict:
    from RNS.vendor import umsgpack as mp

    obj = mp.unpackb(data)
    if not isinstance(obj, dict):
        raise ValueError("manifest payload is not a map")
    return obj


def sign_manifest(manifest: dict, identity) -> bytes:
    """Return rsm bytes for manifest signed by identity (holds private key)."""
    from RNS.vendor import umsgpack as mp

    if not identity.get_private_key() or not hasattr(identity, "sign"):
        raise ValueError("signing requires an RNS.Identity with a private key")

    message = manifest_bytes(manifest)
    signed_data = {
        "hashtype": "sha256",
        "hash": hashlib.sha256(message).digest(),
        "meta": {"signer": identity.hash, "pubkey": identity.get_public_key()},
        "message": message,
    }
    envelope = mp.packb(signed_data)
    return identity.sign(envelope) + envelope


def verify_rsm(rsm: bytes, *, required_signer_hashes=None) -> dict:
    """Verify an update.rsm blob and return the embedded manifest dict.

    required_signer_hashes accepts a single 32-byte hash or an iterable of
    hashes; the manifest is accepted when the signer matches any of them.
    None disables the pin check (tests and tooling only).

    Raises ValueError on any signature, signer, format or hash problem. The
    caller treats every ValueError as "untrusted".
    """
    import RNS
    from RNS.vendor import umsgpack as mp

    if required_signer_hashes is None:
        allowed = None
    elif isinstance(required_signer_hashes, (bytes, bytearray)):
        allowed = {bytes(required_signer_hashes)}
    else:
        allowed = {
            bytes(h)
            for h in required_signer_hashes
            if isinstance(h, (bytes, bytearray))
        }

    siglen = RNS.Identity.SIGLENGTH // 8
    if len(rsm) <= siglen:
        raise ValueError("rsm too short")
    signature, envelope = rsm[:siglen], rsm[siglen:]

    try:
        signed = mp.unpackb(envelope)
    except Exception as e:
        raise ValueError(f"envelope decode failed: {e}") from e
    if not isinstance(signed, dict):
        raise ValueError("envelope is not a map")

    if signed.get("hashtype") != "sha256":
        raise ValueError("unsupported hashtype")
    meta = signed.get("meta")
    message = signed.get("message")
    if not isinstance(meta, dict) or not isinstance(message, bytes):
        raise ValueError("missing meta or message")
    if hashlib.sha256(message).digest() != signed.get("hash"):
        raise ValueError("message hash mismatch")

    pubkey = meta.get("pubkey")
    if not isinstance(pubkey, bytes):
        raise ValueError("missing signer pubkey")
    try:
        identity = RNS.Identity(create_keys=False)
        identity.load_public_key(pubkey)
    except Exception as e:
        raise ValueError(f"bad signer pubkey: {e}") from e

    # A pin may be the 16-byte identity hash or the 32-byte full pubkey
    # hash; accept either representation.
    candidates = {identity.hash, RNS.Identity.full_hash(pubkey)}
    if allowed and not (allowed & candidates):
        raise ValueError("signer hash mismatch")
    meta_signer = meta.get("signer")
    if meta_signer is not None and bytes(meta_signer) not in candidates:
        raise ValueError("meta signer mismatch")

    if not identity.validate(signature, envelope):
        raise ValueError("signature invalid")

    try:
        manifest = manifest_from_bytes(message)
    except Exception as e:
        raise ValueError(f"manifest decode failed: {e}") from e
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unrecognized manifest schema")
    if manifest.get("app") != APP_ID:
        raise ValueError("manifest is not for this application")
    return manifest
