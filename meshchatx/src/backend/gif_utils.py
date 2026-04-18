# SPDX-License-Identifier: 0BSD

"""Validation, hashing, and export/import helpers for user GIF library entries.

GIFs are stored per identity in the ``user_gifs`` table. Compared to stickers,
the library is intended for animated content shared in chats, so:

* Only animated-friendly formats are accepted (``gif`` and ``webp``).
* The per-file byte limit is larger.
* A ``usage_count`` is tracked at the DAO level so the picker can surface
  most-used GIFs first.
"""

from __future__ import annotations

import base64
import hashlib

MAX_GIF_BYTES = 5 * 1024 * 1024
MAX_GIFS_PER_IDENTITY = 1000

_ALLOWED_TYPES = frozenset({"gif", "webp"})

_TYPE_ALIASES = {
    "gif": "gif",
    "webp": "webp",
}


def normalize_image_type(image_type: str | None) -> str | None:
    if not image_type:
        return None
    t = str(image_type).strip().lower()
    t = t.removeprefix("image/")
    t = _TYPE_ALIASES.get(t, t)
    return t if t in _ALLOWED_TYPES else None


def content_hash_hex(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def detect_image_format_from_magic(image_bytes: bytes) -> str | None:
    """Detect a GIF-library compatible image format from magic bytes.

    Returns a normalized type key (``gif`` or ``webp``), or ``None``.
    """
    if not isinstance(image_bytes, (bytes, bytearray)) or len(image_bytes) < 4:
        return None
    b = bytes(image_bytes)
    if len(b) >= 6 and b[0:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if len(b) >= 12 and b[0:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "webp"
    return None


def validate_gif_payload(
    image_bytes: bytes,
    image_type: str | None,
) -> tuple[str, str]:
    """Returns ``(normalized_image_type, content_hash_hex)``.

    The declared ``image_type`` must match the format detected from magic
    bytes; the stored type is the normalized detected format.

    Raises ``ValueError`` with a short reason on invalid input.
    """
    if not isinstance(image_bytes, (bytes, bytearray)):
        msg = "invalid_image_bytes"
        raise ValueError(msg)
    if len(image_bytes) == 0:
        msg = "empty_image"
        raise ValueError(msg)
    if len(image_bytes) > MAX_GIF_BYTES:
        msg = "image_too_large"
        raise ValueError(msg)

    nt = normalize_image_type(image_type)
    if not nt:
        msg = "invalid_image_type"
        raise ValueError(msg)

    detected = detect_image_format_from_magic(image_bytes)
    if not detected:
        msg = "invalid_image_signature"
        raise ValueError(msg)
    if detected != nt:
        msg = "magic_type_mismatch"
        raise ValueError(msg)

    h = content_hash_hex(bytes(image_bytes))
    return detected, h


_EXPORT_FORMAT = "meshchatx-gifs"
_EXPORT_VERSION = 1


def validate_export_document(data: object) -> list[dict]:
    """Parse and validate a GIF library export JSON document.

    Each entry has ``name``, ``image_type``, ``image_bytes`` (base64), and
    optional ``source_message_hash`` and ``usage_count``.
    """
    if not isinstance(data, dict):
        msg = "invalid_document"
        raise ValueError(msg)
    if data.get("format") != _EXPORT_FORMAT:
        msg = "invalid_format"
        raise ValueError(msg)
    try:
        ver = int(data["version"])
    except (KeyError, TypeError, ValueError) as exc:
        msg = "unsupported_version"
        raise ValueError(msg) from exc
    if ver != _EXPORT_VERSION:
        msg = "unsupported_version"
        raise ValueError(msg)
    gifs = data.get("gifs")
    if not isinstance(gifs, list):
        msg = "invalid_gifs_array"
        raise ValueError(msg)
    out: list[dict] = []
    for i, item in enumerate(gifs):
        if not isinstance(item, dict):
            msg = f"invalid_gif_at_{i}"
            raise ValueError(msg)
        name = item.get("name")
        image_type = item.get("image_type")
        image_b64 = item.get("image_bytes")
        if not isinstance(image_b64, str) or not image_b64.strip():
            msg = f"missing_image_bytes_at_{i}"
            raise ValueError(msg)
        try:
            base64.b64decode(image_b64.strip(), validate=False)
        except (ValueError, TypeError) as exc:
            msg = f"invalid_base64_at_{i}"
            raise ValueError(msg) from exc
        src = item.get("source_message_hash")
        usage = item.get("usage_count")
        try:
            usage_int = int(usage) if usage is not None else 0
        except (TypeError, ValueError):
            usage_int = 0
        if usage_int < 0:
            usage_int = 0
        out.append(
            {
                "name": name if isinstance(name, str) else None,
                "image_type": image_type,
                "image_bytes_b64": image_b64.strip(),
                "source_message_hash": src if isinstance(src, str) else None,
                "usage_count": usage_int,
            },
        )
    return out


def build_export_document(gifs: list[dict], exported_at_iso: str) -> dict:
    """Build the GIF export document.

    ``gifs``: rows with ``name``, ``image_type``, ``image_bytes`` (base64 str),
    ``source_message_hash``, and ``usage_count``.
    """
    return {
        "format": _EXPORT_FORMAT,
        "version": _EXPORT_VERSION,
        "exported_at": exported_at_iso,
        "gifs": gifs,
    }


def mime_for_image_type(normalized_type: str) -> str:
    return {
        "gif": "image/gif",
        "webp": "image/webp",
    }.get(normalized_type, "application/octet-stream")


def sanitize_gif_name(name: str | None) -> str | None:
    if name is None:
        return None
    s = "".join(ch for ch in str(name).strip() if ch.isprintable())
    if not s:
        return None
    return s[:128]
