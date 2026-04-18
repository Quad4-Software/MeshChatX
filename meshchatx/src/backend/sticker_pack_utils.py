# SPDX-License-Identifier: 0BSD

"""Validation and (de)serialization for MeshChatX sticker packs.

A sticker pack is a named collection of stickers. Packs use the
``meshchatx-stickerpack`` JSON document format so they can be exported to a
local file, attached to an LXMF message for peer sharing, or installed back
into another identity's library.
"""

from __future__ import annotations

import base64

PACK_FORMAT = "meshchatx-stickerpack"
PACK_VERSION = 1
PACK_FILENAME_SUFFIX = ".meshchatxpack.json"

_VALID_PACK_TYPES = frozenset({"static", "animated", "video", "mixed"})


def sanitize_pack_title(title: str | None) -> str:
    """Return a printable title for a pack, defaulting to ``"Untitled pack"``."""
    if title is None:
        return "Untitled pack"
    s = "".join(ch for ch in str(title).strip() if ch.isprintable())
    return s[:80] if s else "Untitled pack"


def sanitize_pack_short_name(name: str | None) -> str | None:
    """Return a slug-compatible short name (alnum/underscore/dash) or ``None``."""
    if name is None:
        return None
    s = str(name).strip().lower()
    out = "".join(ch for ch in s if ch.isalnum() or ch in {"_", "-"})
    return out[:32] if out else None


def sanitize_pack_description(description: str | None) -> str | None:
    """Trim and clamp the optional pack description to 280 characters."""
    if description is None:
        return None
    s = "".join(ch for ch in str(description).strip() if ch.isprintable() or ch == "\n")
    return s[:280] if s else None


def sanitize_pack_type(pack_type: str | None) -> str:
    """Normalize a pack type to one of ``static|animated|video|mixed``."""
    if not pack_type:
        return "mixed"
    s = str(pack_type).strip().lower()
    return s if s in _VALID_PACK_TYPES else "mixed"


def build_pack_document(
    pack: dict,
    stickers: list[dict],
    exported_at_iso: str,
) -> dict:
    """Build a ``meshchatx-stickerpack`` document from a pack and its stickers.

    ``pack`` is a row from ``user_sticker_packs``. ``stickers`` is a list of
    rows containing ``name``, ``emoji``, ``image_type``, ``image_bytes`` (base64
    string), and optional metadata fields.
    """
    return {
        "format": PACK_FORMAT,
        "version": PACK_VERSION,
        "exported_at": exported_at_iso,
        "pack": {
            "title": sanitize_pack_title(pack.get("title")),
            "short_name": sanitize_pack_short_name(pack.get("short_name")),
            "description": sanitize_pack_description(pack.get("description")),
            "type": sanitize_pack_type(pack.get("pack_type")),
            "author": (pack.get("author") or "")[:80] or None,
            "is_strict": bool(pack.get("is_strict", True)),
        },
        "stickers": stickers,
    }


def validate_pack_document(data: object) -> dict:
    """Parse and validate a ``meshchatx-stickerpack`` document.

    Returns a dict with normalized ``pack`` and ``stickers`` lists. Raises
    ``ValueError`` with a short reason on invalid input.
    """
    if not isinstance(data, dict):
        msg = "invalid_pack_document"
        raise ValueError(msg)
    if data.get("format") != PACK_FORMAT:
        msg = "invalid_pack_format"
        raise ValueError(msg)
    try:
        ver = int(data["version"])
    except (KeyError, TypeError, ValueError) as exc:
        msg = "unsupported_pack_version"
        raise ValueError(msg) from exc
    if ver != PACK_VERSION:
        msg = "unsupported_pack_version"
        raise ValueError(msg)
    pack_meta = data.get("pack")
    if not isinstance(pack_meta, dict):
        msg = "invalid_pack_meta"
        raise ValueError(msg)
    stickers = data.get("stickers")
    if not isinstance(stickers, list):
        msg = "invalid_pack_stickers"
        raise ValueError(msg)
    out_stickers: list[dict] = []
    for i, item in enumerate(stickers):
        if not isinstance(item, dict):
            msg = f"invalid_pack_sticker_at_{i}"
            raise ValueError(msg)
        b64 = item.get("image_bytes")
        if not isinstance(b64, str) or not b64.strip():
            msg = f"missing_pack_sticker_bytes_at_{i}"
            raise ValueError(msg)
        try:
            base64.b64decode(b64.strip(), validate=False)
        except (ValueError, TypeError) as exc:
            msg = f"invalid_pack_sticker_base64_at_{i}"
            raise ValueError(msg) from exc
        out_stickers.append(
            {
                "name": item.get("name") if isinstance(item.get("name"), str) else None,
                "emoji": item.get("emoji")
                if isinstance(item.get("emoji"), str)
                else None,
                "image_type": item.get("image_type"),
                "image_bytes_b64": b64.strip(),
            },
        )
    return {
        "pack": {
            "title": sanitize_pack_title(pack_meta.get("title")),
            "short_name": sanitize_pack_short_name(pack_meta.get("short_name")),
            "description": sanitize_pack_description(pack_meta.get("description")),
            "pack_type": sanitize_pack_type(pack_meta.get("type")),
            "author": pack_meta.get("author")
            if isinstance(pack_meta.get("author"), str)
            else None,
            "is_strict": bool(pack_meta.get("is_strict", True)),
        },
        "stickers": out_stickers,
    }
