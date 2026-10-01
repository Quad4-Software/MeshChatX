# SPDX-License-Identifier: 0BSD

"""Signed update-manifest envelope (rnid-compatible RSG).

The release pipeline signs a canonical JSON manifest into
"signature(64B) + umsgpack({hashtype, hash, meta:{signer, pubkey},
message})". Clients verify against a pinned signer identity hash. The
public key travels inside the envelope's meta block.

Used by scripts/build/update_manifest.py (signing) and
meshchatx.src.backend.update_manager (verification).
"""

from __future__ import annotations

import hashlib
import json

SCHEMA = 1
APP_ID = "reticulum-meshchatx"


def canonical_json(manifest: dict) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_manifest(manifest: dict, identity) -> bytes:
    """Return rsm bytes for manifest signed by identity (holds private key)."""
    from RNS.vendor import umsgpack as mp

    if not identity.get_private_key() or not hasattr(identity, "sign"):
        raise ValueError("signing requires an RNS.Identity with a private key")

    message = canonical_json(manifest)
    signed_data = {
        "hashtype": "sha256",
        "hash": hashlib.sha256(message).digest(),
        "meta": {"signer": identity.hash, "pubkey": identity.get_public_key()},
        "message": message,
    }
    envelope = mp.packb(signed_data)
    return identity.sign(envelope) + envelope


def verify_rsm(rsm: bytes, *, required_signer_hash: bytes | None = None) -> dict:
    """Verify an update.rsm blob and return the embedded manifest dict.

    Raises ValueError on any signature, signer, format or hash problem. The
    caller treats every ValueError as "untrusted".
    """
    import RNS
    from RNS.vendor import umsgpack as mp

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

    if required_signer_hash is not None:
        if identity.hash != required_signer_hash:
            raise ValueError("signer hash mismatch")
        if meta.get("signer") != required_signer_hash:
            raise ValueError("meta signer mismatch")

    if not identity.validate(signature, envelope):
        raise ValueError("signature invalid")

    try:
        manifest = json.loads(message.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"manifest JSON decode failed: {e}") from e
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise ValueError("unrecognized manifest schema")
    if manifest.get("app") != APP_ID:
        raise ValueError("manifest is not for this application")
    return manifest
