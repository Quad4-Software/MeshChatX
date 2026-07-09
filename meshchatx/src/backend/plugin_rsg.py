# SPDX-License-Identifier: 0BSD

"""Reticulum Signature (.rsg) verification for MeshChatX plugins."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import RNS
from RNS.vendor import umsgpack

ED25519_SIG_LEN = 64
TRUNCATED_HASH_LEN = RNS.Identity.TRUNCATED_HASHLENGTH // 8
PUBLIC_KEY_LEN = RNS.Identity.KEYSIZE // 8
SHA256_HASH_LEN = 32


class RSGError(ValueError):
    """Raised when RSG data fails validation."""


@dataclass
class SignatureInfo:
    present: bool = False
    valid: bool = False
    signer: str = ""
    signer_name: str = ""
    trusted: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "present": self.present,
            "valid": self.valid,
            "trusted": self.trusted,
        }
        if self.signer:
            out["signer"] = self.signer
        if self.signer_name:
            out["signer_name"] = self.signer_name
        if self.error:
            out["error"] = self.error
        return out


def _meta_bytes(meta: dict, key: str) -> bytes | None:
    raw = meta.get(key)
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, bytearray):
        return bytes(raw)
    if isinstance(raw, str):
        return raw.encode("utf-8")
    return None


def validate_rsg(
    rsg_data: bytes,
    message: bytes,
    required_signer: bytes | None = None,
) -> str:
    """Verify RSG bytes against message. Returns lowercase signer hex hash."""
    if not message:
        raise RSGError("no message for rsg validation")
    if not rsg_data or len(rsg_data) < ED25519_SIG_LEN + 1:
        raise RSGError("rsg data too short")
    signature = rsg_data[:ED25519_SIG_LEN]
    envelope_bytes = rsg_data[ED25519_SIG_LEN:]
    try:
        envelope = umsgpack.unpackb(envelope_bytes)
    except Exception as exc:
        raise RSGError(f"invalid rsg envelope: {exc}") from exc
    if not isinstance(envelope, dict):
        raise RSGError("invalid rsg envelope")
    if envelope.get("hashtype") != "sha256":
        raise RSGError("unsupported rsg hash type")
    envelope_hash = envelope.get("hash")
    if (
        not isinstance(envelope_hash, (bytes, bytearray))
        or len(envelope_hash) != SHA256_HASH_LEN
    ):
        raise RSGError("rsg hash mismatch")
    if bytes(envelope_hash) != RNS.Identity.full_hash(message):
        raise RSGError("rsg hash mismatch")
    meta = envelope.get("meta")
    if not isinstance(meta, dict):
        raise RSGError("invalid rsg envelope")
    signer_raw = _meta_bytes(meta, "signer")
    if signer_raw is None or len(signer_raw) != TRUNCATED_HASH_LEN:
        raise RSGError("rsg signer mismatch")
    pub_key_raw = _meta_bytes(meta, "pubkey")
    if pub_key_raw is None or len(pub_key_raw) != PUBLIC_KEY_LEN:
        raise RSGError("invalid rsg public key")
    signing_identity = RNS.Identity(create_keys=False)
    try:
        signing_identity.load_public_key(pub_key_raw)
    except Exception as exc:
        raise RSGError("invalid rsg public key") from exc
    if signing_identity.hash != signer_raw:
        raise RSGError("rsg signer mismatch")
    if required_signer and signing_identity.hash != required_signer:
        raise RSGError("rsg signer mismatch")
    if not signing_identity.validate(signature, envelope_bytes):
        raise RSGError("invalid rsg signature")
    return signing_identity.hash.hex()


def create_rsg(message: bytes, identity: RNS.Identity) -> bytes:
    if not message:
        raise RSGError("no message for rsg creation")
    if identity.sig_prv is None:
        raise RSGError("identity has no private key")
    signed_data = {
        "hashtype": "sha256",
        "hash": RNS.Identity.full_hash(message),
        "meta": {
            "signer": identity.hash,
            "pubkey": identity.get_public_key(),
        },
    }
    envelope = umsgpack.packb(signed_data)
    return identity.sign(envelope) + envelope


def verify_rsg_payload(rsg_data: bytes, payload: bytes) -> SignatureInfo:
    try:
        signer_hex = validate_rsg(rsg_data, payload)
    except Exception as exc:
        return SignatureInfo(present=True, error=str(exc))
    return SignatureInfo(present=True, valid=True, signer=signer_hex)
