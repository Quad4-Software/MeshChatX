# SPDX-License-Identifier: 0BSD

"""Encrypt RRC room keys at rest with AES-GCM.

Wrapping keys are derived from the active Reticulum identity private key via
HKDF so secrets stay identity-scoped and become unreadable after an identity
switch without copying the private key material into the database.
"""

from __future__ import annotations

import hmac
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_HKDF_SALT = b"meshchatx-rrc-room-keys-v1"
_HKDF_INFO = b"rrc-room-key-wrap"
_NONCE_LEN = 12
_KEY_LEN = 32
MAX_ROOM_KEY_BYTES = 256


def normalize_room_key(room_key: str) -> str:
    """Strip and validate a room key string for storage or JOIN compare."""
    if not isinstance(room_key, str):
        msg = "room key must be a string"
        raise TypeError(msg)
    key = room_key.strip()
    if not key:
        msg = "room key must not be empty"
        raise ValueError(msg)
    encoded = key.encode("utf-8")
    if len(encoded) > MAX_ROOM_KEY_BYTES:
        msg = f"room key must be at most {MAX_ROOM_KEY_BYTES} bytes"
        raise ValueError(msg)
    return key


def room_keys_equal(provided: str | None, expected: str) -> bool:
    """Constant-time compare of stripped JOIN body against stored hub key."""
    if not isinstance(expected, str) or not expected:
        return False
    if not isinstance(provided, str):
        return False
    try:
        left = normalize_room_key(provided).encode("utf-8")
    except (TypeError, ValueError):
        return False
    right = expected.encode("utf-8")
    if len(left) != len(right):
        hmac.compare_digest(left, left)
        return False
    return hmac.compare_digest(left, right)


def derive_wrap_key(identity_private_key: bytes) -> bytes:
    if not isinstance(identity_private_key, (bytes, bytearray)):
        msg = "identity private key must be bytes"
        raise TypeError(msg)
    if not identity_private_key:
        msg = "identity private key must not be empty"
        raise ValueError(msg)
    return HKDF(
        algorithm=hashes.SHA256(),
        length=_KEY_LEN,
        salt=_HKDF_SALT,
        info=_HKDF_INFO,
    ).derive(bytes(identity_private_key))


def encrypt_room_key(identity_private_key: bytes, room_key: str) -> tuple[bytes, bytes]:
    """Return (nonce, ciphertext) for a room key."""
    plaintext = normalize_room_key(room_key).encode("utf-8")
    wrap_key = derive_wrap_key(identity_private_key)
    nonce = os.urandom(_NONCE_LEN)
    ciphertext = AESGCM(wrap_key).encrypt(nonce, plaintext, None)
    return nonce, ciphertext


def decrypt_room_key(
    identity_private_key: bytes,
    nonce: bytes,
    ciphertext: bytes,
) -> str:
    if not isinstance(nonce, (bytes, bytearray)) or len(nonce) != _NONCE_LEN:
        msg = "invalid room key nonce"
        raise ValueError(msg)
    if not isinstance(ciphertext, (bytes, bytearray)) or not ciphertext:
        msg = "invalid room key ciphertext"
        raise ValueError(msg)
    wrap_key = derive_wrap_key(identity_private_key)
    plaintext = AESGCM(wrap_key).decrypt(bytes(nonce), bytes(ciphertext), None)
    return plaintext.decode("utf-8")
