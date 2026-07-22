"""CBOR envelope helpers for Reticulum Relay Chat."""

from __future__ import annotations

import os
import time
from typing import Any

import cbor2

from .constants import (
    K_BODY,
    K_ID,
    K_NICK,
    K_ROOM,
    K_SRC,
    K_T,
    K_TS,
    K_V,
    RRC_VERSION,
)


def now_ms() -> int:
    """Return milliseconds since the Unix epoch."""
    return int(time.time() * 1000)


def msg_id() -> bytes:
    """Return an 8-byte cryptographically random message id."""
    return os.urandom(8)


def normalize_room(room: str | None) -> str:
    """Normalize a room name for case-insensitive matching."""
    if not isinstance(room, str):
        raise ValueError("room must be a non-empty string")
    normalized = room.strip().lower()
    if not normalized:
        raise ValueError("room must not be empty")
    return normalized


def make_envelope(
    msg_type: int,
    src: bytes,
    room: str | None = None,
    body: Any = None,
    nick: str | None = None,
    mid: bytes | None = None,
    ts: int | None = None,
) -> dict[int, Any]:
    """Build a canonical RRC envelope map with integer keys."""
    if not isinstance(src, (bytes, bytearray)) or len(src) != 16:
        raise ValueError("src must be a 16-byte identity hash")
    env: dict[int, Any] = {
        K_V: RRC_VERSION,
        K_T: int(msg_type),
        K_ID: mid or msg_id(),
        K_TS: ts if ts is not None else now_ms(),
        K_SRC: bytes(src),
    }
    if room is not None:
        env[K_ROOM] = room
    if body is not None:
        env[K_BODY] = body
    if nick is not None and nick != "":
        env[K_NICK] = nick
    return env


def encode_envelope(env: dict[int, Any]) -> bytes:
    """Encode an RRC envelope to CBOR bytes."""
    return cbor2.dumps(env)


def decode_envelope(data: bytes | bytearray) -> dict[int, Any] | None:
    """Decode CBOR bytes into an RRC envelope map.

    Returns None for malformed payloads. Unknown keys are preserved so
    callers can ignore them per forward-compatibility rules.
    """
    try:
        env = cbor2.loads(bytes(data))
    except Exception:
        return None
    if not isinstance(env, dict):
        return None
    return env


def envelope_type(env: dict[int, Any]) -> int | None:
    """Return the message type from an envelope, or None if missing."""
    value = env.get(K_T)
    return int(value) if isinstance(value, int) else None


def envelope_room(env: dict[int, Any]) -> str | None:
    """Return a normalized room name from an envelope, if present."""
    room = env.get(K_ROOM)
    if not isinstance(room, str) or not room.strip():
        return None
    return room.strip().lower()


def envelope_src(env: dict[int, Any]) -> bytes | None:
    """Return the sender identity hash from an envelope, if present."""
    src = env.get(K_SRC)
    if isinstance(src, (bytes, bytearray)) and len(src) == 16:
        return bytes(src)
    return None


def envelope_nick(env: dict[int, Any]) -> str | None:
    """Return the advisory nickname from an envelope, if present."""
    nick = env.get(K_NICK)
    return nick if isinstance(nick, str) and nick else None


def envelope_body(env: dict[int, Any]) -> Any:
    """Return the body field from an envelope."""
    return env.get(K_BODY)


def validate_envelope(env: dict[int, Any]) -> bool:
    """Return True when required envelope fields are present and well-formed."""
    if not isinstance(env, dict):
        return False
    version = env.get(K_V)
    if version is not None and version != RRC_VERSION:
        return False
    if not isinstance(env.get(K_T), int):
        return False
    mid = env.get(K_ID)
    if not isinstance(mid, (bytes, bytearray)) or len(mid) != 8:
        return False
    ts = env.get(K_TS)
    if ts is not None and not isinstance(ts, int):
        return False
    src = env.get(K_SRC)
    if not isinstance(src, (bytes, bytearray)) or len(src) != 16:
        return False
    room = env.get(K_ROOM)
    if room is not None and not isinstance(room, str):
        return False
    nick = env.get(K_NICK)
    if nick is not None and not isinstance(nick, str):
        return False
    return True
