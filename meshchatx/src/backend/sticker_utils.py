# SPDX-License-Identifier: 0BSD

"""Validation, hashing, and metadata extraction for user sticker payloads.

MeshChatX aligns with the Telegram sticker specification while keeping the
historical "saved image" formats supported as a separate ``legacy`` class so
existing libraries continue to work after migration.

Sticker classes:

``static``
    PNG or WebP. Telegram-strict: max 512 KB, max 512x512 px and at least one
    side must be exactly 512 px.

``animated``
    TGS (gzipped Lottie JSON). Telegram-strict: max 64 KB, canvas 512x512,
    30-60 FPS, max 3 s, looped (loop attribute is informational only).

``video``
    WebM/VP9 with no audio. Telegram-strict: max 256 KB, max 512x512 with at
    least one side exactly 512 px, max 30 FPS, max 3 s.

``legacy``
    PNG/JPEG/GIF/WebP/BMP without dimension/duration enforcement. Capped at
    512 KB. Used for the historical free-form sticker library and for save
    images coming from chats. Not exportable as part of a Telegram-style pack.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import struct

# Telegram-aligned size limits.
MAX_STATIC_BYTES = 512 * 1024
MAX_ANIMATED_BYTES = 64 * 1024
MAX_VIDEO_BYTES = 256 * 1024

# Backwards-compatible alias used by the legacy upload path.
MAX_STICKER_BYTES = MAX_STATIC_BYTES

MAX_STICKERS_PER_IDENTITY = 2000
MAX_STICKER_PACKS_PER_IDENTITY = 200
MAX_STICKERS_PER_PACK = 120

STICKER_CANVAS = 512
ANIMATED_FPS_MIN = 30
ANIMATED_FPS_MAX = 60
VIDEO_FPS_MAX = 30
MAX_DURATION_MS = 3000

_LEGACY_TYPES = frozenset({"png", "jpeg", "jpg", "gif", "webp", "bmp"})
_TELEGRAM_STATIC_TYPES = frozenset({"png", "webp"})
_ALLOWED_TYPES = frozenset(
    _LEGACY_TYPES | {"tgs", "webm"},
)

_TYPE_ALIASES = {
    "jpeg": "jpeg",
    "jpg": "jpeg",
    "pjpeg": "jpeg",
    "png": "png",
    "gif": "gif",
    "webp": "webp",
    "bmp": "bmp",
    "tgs": "tgs",
    "webm": "webm",
    "x-tgsticker": "tgs",
    "tgsticker": "tgs",
    "video/webm": "webm",
}


def normalize_image_type(image_type: str | None) -> str | None:
    """Map a user-supplied MIME or extension to a normalized sticker type key."""
    if not image_type:
        return None
    t = str(image_type).strip().lower()
    t = t.removeprefix("image/")
    t = t.removeprefix("video/")
    t = t.removeprefix("application/")
    t = _TYPE_ALIASES.get(t, t)
    return t if t in _ALLOWED_TYPES else None


def content_hash_hex(image_bytes: bytes) -> str:
    """SHA-256 hex digest of raw sticker bytes; used for deduplication."""
    return hashlib.sha256(image_bytes).hexdigest()


def detect_image_format_from_magic(image_bytes: bytes) -> str | None:
    """Detect a sticker payload format from its magic bytes.

    Recognises PNG, JPEG, GIF, WebP, BMP, gzipped TGS (Lottie), and EBML/WebM
    containers. Returns a normalized type key or ``None`` for unknown input.
    """
    if not isinstance(image_bytes, (bytes, bytearray)) or len(image_bytes) < 4:
        return None
    b = bytes(image_bytes)
    if len(b) >= 8 and b[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(b) >= 3 and b[0:3] == b"\xff\xd8\xff":
        return "jpeg"
    if len(b) >= 6 and b[0:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if len(b) >= 12 and b[0:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "webp"
    if len(b) >= 2 and b[0:2] == b"BM":
        return "bmp"
    if len(b) >= 4 and b[0:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    if len(b) >= 2 and b[0:2] == b"\x1f\x8b":
        return "tgs"
    return None


def _read_png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[12:16] != b"IHDR":
        return None
    try:
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)
    except struct.error:
        return None


def _read_webp_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 30:
        return None
    chunk = data[12:16]
    try:
        if chunk == b"VP8 ":
            w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
            h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
            return int(w), int(h)
        if chunk == b"VP8L":
            b1, b2, b3, b4 = data[21], data[22], data[23], data[24]
            w = ((b2 & 0x3F) << 8 | b1) + 1
            h = ((b4 & 0x0F) << 10 | b3 << 2 | (b2 & 0xC0) >> 6) + 1
            return int(w), int(h)
        if chunk == b"VP8X":
            w = (data[24] | data[25] << 8 | data[26] << 16) + 1
            h = (data[27] | data[28] << 8 | data[29] << 16) + 1
            return int(w), int(h)
    except (IndexError, struct.error):
        return None
    return None


def _read_gif_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 10:
        return None
    try:
        w, h = struct.unpack("<HH", data[6:10])
        return int(w), int(h)
    except struct.error:
        return None


def _read_bmp_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 26:
        return None
    try:
        w, h = struct.unpack("<ii", data[18:26])
        return int(abs(w)), int(abs(h))
    except struct.error:
        return None


def detect_image_dimensions(image_type: str, data: bytes) -> tuple[int, int] | None:
    """Return ``(width, height)`` for a static sticker payload, or ``None``.

    Works for PNG, WebP (lossy/lossless/extended), GIF, and BMP without any
    third-party imaging dependency.
    """
    if not isinstance(data, (bytes, bytearray)):
        return None
    raw = bytes(data)
    if image_type == "png":
        return _read_png_dimensions(raw)
    if image_type == "webp":
        return _read_webp_dimensions(raw)
    if image_type == "gif":
        return _read_gif_dimensions(raw)
    if image_type == "bmp":
        return _read_bmp_dimensions(raw)
    if image_type == "jpeg":
        return _read_jpeg_dimensions(raw)
    return None


def _read_jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    i = 2
    n = len(data)
    while i + 9 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        i += 2
        if marker in (0xD8, 0xD9):
            continue
        if 0xD0 <= marker <= 0xD7:
            continue
        if i + 2 > n:
            return None
        seg_len = struct.unpack(">H", data[i : i + 2])[0]
        if seg_len < 2 or i + seg_len > n:
            return None
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if i + 7 > n:
                return None
            try:
                h, w = struct.unpack(">HH", data[i + 3 : i + 7])
                return int(w), int(h)
            except struct.error:
                return None
        i += seg_len
    return None


def parse_tgs(data: bytes) -> dict:
    """Decompress a TGS payload and parse the Lottie JSON inside.

    Returns a dict with ``width``, ``height``, ``fps``, ``duration_ms`` and the
    raw lottie ``data``. Raises ``ValueError`` if the file is not a valid
    Lottie animation.
    """
    if not isinstance(data, (bytes, bytearray)) or len(data) < 2:
        msg = "invalid_tgs"
        raise ValueError(msg)
    try:
        decompressed = gzip.decompress(bytes(data))
    except (OSError, EOFError, gzip.BadGzipFile) as exc:
        msg = "invalid_tgs_gzip"
        raise ValueError(msg) from exc
    if len(decompressed) > 4 * 1024 * 1024:
        msg = "invalid_tgs_too_large_decompressed"
        raise ValueError(msg)
    try:
        lottie = json.loads(decompressed)
    except (ValueError, json.JSONDecodeError) as exc:
        msg = "invalid_tgs_json"
        raise ValueError(msg) from exc
    if not isinstance(lottie, dict):
        msg = "invalid_tgs_root"
        raise ValueError(msg)
    try:
        width = int(lottie.get("w") or 0)
        height = int(lottie.get("h") or 0)
        fps = float(lottie.get("fr") or 0)
        in_point = float(lottie.get("ip") or 0)
        out_point = float(lottie.get("op") or 0)
    except (TypeError, ValueError) as exc:
        msg = "invalid_tgs_metadata"
        raise ValueError(msg) from exc
    if width <= 0 or height <= 0 or fps <= 0 or out_point <= in_point:
        msg = "invalid_tgs_metadata"
        raise ValueError(msg)
    duration_ms = int(round(((out_point - in_point) / fps) * 1000.0))
    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration_ms": duration_ms,
        "lottie": lottie,
    }


def _ebml_read_vint(
    buf: bytes, pos: int, *, mask_marker: bool = True
) -> tuple[int, int] | None:
    """Read an EBML variable-length integer at ``pos``; returns ``(value, next_pos)``."""
    if pos >= len(buf):
        return None
    first = buf[pos]
    if first == 0:
        return None
    length = 1
    mask = 0x80
    while length <= 8 and not (first & mask):
        length += 1
        mask >>= 1
    if length > 8 or pos + length > len(buf):
        return None
    value = first & (mask - 1) if mask_marker else first
    for i in range(1, length):
        value = (value << 8) | buf[pos + i]
    return value, pos + length


def _ebml_iter_elements(buf: bytes, start: int, end: int):
    pos = start
    while pos < end:
        id_res = _ebml_read_vint(buf, pos, mask_marker=False)
        if id_res is None:
            return
        elem_id, after_id = id_res
        size_res = _ebml_read_vint(buf, after_id)
        if size_res is None:
            return
        size, after_size = size_res
        body_end = min(after_size + size, end)
        yield elem_id, after_size, body_end
        pos = body_end


def _ebml_read_uint(buf: bytes, start: int, end: int) -> int:
    val = 0
    for b in buf[start:end]:
        val = (val << 8) | b
    return val


def _ebml_read_float(buf: bytes, start: int, end: int) -> float | None:
    size = end - start
    try:
        if size == 4:
            return struct.unpack(">f", buf[start:end])[0]
        if size == 8:
            return struct.unpack(">d", buf[start:end])[0]
    except struct.error:
        return None
    return None


def parse_webm(data: bytes) -> dict:
    """Parse a WebM container header to extract sticker-relevant metadata.

    Returns ``width``, ``height``, ``fps`` (best-effort), ``duration_ms``, the
    detected video ``codec_id`` and ``has_audio`` flag. Raises ``ValueError``
    when the container is not a valid WebM file.
    """
    if not isinstance(data, (bytes, bytearray)) or len(data) < 32:
        msg = "invalid_webm"
        raise ValueError(msg)
    raw = bytes(data)
    if raw[0:4] != b"\x1a\x45\xdf\xa3":
        msg = "invalid_webm_header"
        raise ValueError(msg)
    width = 0
    height = 0
    duration_ms = 0
    timecode_scale = 1_000_000
    duration_ticks = 0.0
    codec_id = ""
    has_audio = False
    track_default_duration_ns: list[int] = []

    for elem_id, body_start, body_end in _ebml_iter_elements(raw, 0, len(raw)):
        if elem_id == 0x18538067:
            for seg_id, sb, se in _ebml_iter_elements(raw, body_start, body_end):
                if seg_id == 0x1654AE6B:
                    for tr_id, tb, te in _ebml_iter_elements(raw, sb, se):
                        if tr_id == 0xAE:
                            track_codec = ""
                            track_type = 0
                            track_def_dur = 0
                            t_w = t_h = 0
                            for f_id, fb, fe in _ebml_iter_elements(raw, tb, te):
                                if f_id == 0x83:
                                    track_type = _ebml_read_uint(raw, fb, fe)
                                elif f_id == 0x86:
                                    track_codec = raw[fb:fe].decode(
                                        "ascii", errors="replace"
                                    )
                                elif f_id == 0x23E383:
                                    track_def_dur = _ebml_read_uint(raw, fb, fe)
                                elif f_id == 0xE0:
                                    for v_id, vb, ve in _ebml_iter_elements(
                                        raw, fb, fe
                                    ):
                                        if v_id == 0xB0:
                                            t_w = _ebml_read_uint(raw, vb, ve)
                                        elif v_id == 0xBA:
                                            t_h = _ebml_read_uint(raw, vb, ve)
                            if track_type == 1:
                                width = t_w or width
                                height = t_h or height
                                codec_id = track_codec or codec_id
                                if track_def_dur:
                                    track_default_duration_ns.append(track_def_dur)
                            elif track_type == 2:
                                has_audio = True
                elif seg_id == 0x1549A966:
                    for inf_id, ib, ie in _ebml_iter_elements(raw, sb, se):
                        if inf_id == 0x2AD7B1:
                            timecode_scale = (
                                _ebml_read_uint(raw, ib, ie) or timecode_scale
                            )
                        elif inf_id == 0x4489:
                            d = _ebml_read_float(raw, ib, ie)
                            if d is not None:
                                duration_ticks = d
    if width <= 0 or height <= 0:
        msg = "invalid_webm_no_video"
        raise ValueError(msg)
    if duration_ticks > 0:
        duration_ms = int(round(duration_ticks * timecode_scale / 1_000_000.0))
    fps = 0.0
    if track_default_duration_ns:
        fps = 1_000_000_000.0 / float(track_default_duration_ns[0])
    return {
        "width": int(width),
        "height": int(height),
        "duration_ms": int(duration_ms),
        "fps": fps,
        "codec_id": codec_id,
        "has_audio": has_audio,
    }


def _validate_dimensions_telegram_static(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        msg = "invalid_dimensions"
        raise ValueError(msg)
    if width > STICKER_CANVAS or height > STICKER_CANVAS:
        msg = "dimensions_too_large"
        raise ValueError(msg)
    if width != STICKER_CANVAS and height != STICKER_CANVAS:
        msg = "dimensions_not_512_on_one_side"
        raise ValueError(msg)


def validate_sticker_payload(
    image_bytes: bytes,
    image_type: str | None,
    *,
    strict: bool = False,
) -> tuple[str, str]:
    """Validate a sticker payload against the legacy or strict Telegram rules.

    When ``strict`` is False the validator preserves the historical behaviour
    of the MeshChatX library (PNG/JPEG/GIF/WebP/BMP up to 512 KB, no dimension
    enforcement). When ``strict`` is True the validator additionally enforces
    Telegram-aligned size, dimension, FPS and duration limits per format.

    Returns ``(normalized_image_type, content_hash_hex)``. Raises ``ValueError``
    with a short machine-readable reason on invalid input.
    """
    if not isinstance(image_bytes, (bytes, bytearray)):
        msg = "invalid_image_bytes"
        raise ValueError(msg)
    if len(image_bytes) == 0:
        msg = "empty_image"
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

    raw = bytes(image_bytes)

    if not strict:
        if nt not in _LEGACY_TYPES:
            msg = "invalid_image_type"
            raise ValueError(msg)
        if len(raw) > MAX_STATIC_BYTES:
            msg = "image_too_large"
            raise ValueError(msg)
    else:
        _validate_strict_payload(nt, raw)

    return detected, content_hash_hex(raw)


def _validate_strict_payload(nt: str, raw: bytes) -> None:
    if nt == "tgs":
        if len(raw) > MAX_ANIMATED_BYTES:
            msg = "animated_too_large"
            raise ValueError(msg)
        meta = parse_tgs(raw)
        if meta["width"] != STICKER_CANVAS or meta["height"] != STICKER_CANVAS:
            msg = "animated_dimensions_invalid"
            raise ValueError(msg)
        if not (ANIMATED_FPS_MIN <= meta["fps"] <= ANIMATED_FPS_MAX):
            msg = "animated_fps_out_of_range"
            raise ValueError(msg)
        if meta["duration_ms"] > MAX_DURATION_MS:
            msg = "animated_duration_too_long"
            raise ValueError(msg)
        return

    if nt == "webm":
        if len(raw) > MAX_VIDEO_BYTES:
            msg = "video_too_large"
            raise ValueError(msg)
        meta = parse_webm(raw)
        if meta["has_audio"]:
            msg = "video_has_audio"
            raise ValueError(msg)
        codec = (meta.get("codec_id") or "").upper()
        if codec and "VP9" not in codec and "V_VP9" not in codec:
            msg = "video_codec_not_vp9"
            raise ValueError(msg)
        _validate_dimensions_telegram_static(meta["width"], meta["height"])
        if meta["fps"] and meta["fps"] > VIDEO_FPS_MAX + 0.5:
            msg = "video_fps_too_high"
            raise ValueError(msg)
        if meta["duration_ms"] > MAX_DURATION_MS:
            msg = "video_duration_too_long"
            raise ValueError(msg)
        return

    if nt in _TELEGRAM_STATIC_TYPES:
        if len(raw) > MAX_STATIC_BYTES:
            msg = "static_too_large"
            raise ValueError(msg)
        dims = detect_image_dimensions(nt, raw)
        if dims is None:
            msg = "static_dimensions_unknown"
            raise ValueError(msg)
        _validate_dimensions_telegram_static(*dims)
        return

    msg = "strict_format_not_supported"
    raise ValueError(msg)


def extract_metadata(image_type: str, raw: bytes) -> dict:
    """Best-effort extraction of width/height/fps/duration_ms for storage."""
    nt = normalize_image_type(image_type) or image_type
    out = {
        "width": None,
        "height": None,
        "fps": None,
        "duration_ms": None,
        "is_animated": nt == "tgs",
        "is_video": nt == "webm",
    }
    try:
        if nt == "tgs":
            m = parse_tgs(raw)
            out.update(
                {
                    "width": m["width"],
                    "height": m["height"],
                    "fps": m["fps"],
                    "duration_ms": m["duration_ms"],
                },
            )
        elif nt == "webm":
            m = parse_webm(raw)
            out.update(
                {
                    "width": m["width"],
                    "height": m["height"],
                    "fps": m["fps"] or None,
                    "duration_ms": m["duration_ms"] or None,
                },
            )
        else:
            dims = detect_image_dimensions(nt, raw)
            if dims is not None:
                out["width"], out["height"] = dims
    except ValueError:
        pass
    return out


_EXPORT_FORMAT = "meshchatx-stickers"
_EXPORT_VERSION = 1


def validate_export_document(data: object) -> list[dict]:
    """Parse and validate a single-sticker export JSON document.

    Each sticker dict has ``name``, ``image_type``, ``image_bytes`` (base64),
    optional ``source_message_hash``, and optional ``emoji`` (sticker tag).
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
    stickers = data.get("stickers")
    if not isinstance(stickers, list):
        msg = "invalid_stickers_array"
        raise ValueError(msg)
    out: list[dict] = []
    for i, item in enumerate(stickers):
        if not isinstance(item, dict):
            msg = f"invalid_sticker_at_{i}"
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
        emoji = item.get("emoji")
        out.append(
            {
                "name": name if isinstance(name, str) else None,
                "image_type": image_type,
                "image_bytes_b64": image_b64.strip(),
                "source_message_hash": src if isinstance(src, str) else None,
                "emoji": emoji if isinstance(emoji, str) else None,
            },
        )
    return out


def build_export_document(stickers: list[dict], exported_at_iso: str) -> dict:
    """Build a `meshchatx-stickers` JSON document for individual stickers."""
    return {
        "format": _EXPORT_FORMAT,
        "version": _EXPORT_VERSION,
        "exported_at": exported_at_iso,
        "stickers": stickers,
    }


def mime_for_image_type(normalized_type: str) -> str:
    """Return the HTTP ``Content-Type`` for a normalized sticker type key."""
    return {
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tgs": "application/x-tgsticker",
        "webm": "video/webm",
    }.get(normalized_type, "application/octet-stream")


def sanitize_sticker_name(name: str | None) -> str | None:
    """Trim, strip non-printable characters, and clamp a sticker name to 128 chars."""
    if name is None:
        return None
    s = "".join(ch for ch in str(name).strip() if ch.isprintable())
    if not s:
        return None
    return s[:128]


_EMOJI_MAX_LEN = 16


def sanitize_sticker_emoji(emoji: str | None) -> str | None:
    """Allow up to a small number of characters for a sticker emoji tag.

    The protocol does not enforce that stickers must carry an emoji (per user
    decision); this helper only ensures the value is short, printable and
    storable.
    """
    if emoji is None:
        return None
    s = str(emoji).strip()
    if not s:
        return None
    s = "".join(ch for ch in s if ch.isprintable())
    if not s:
        return None
    return s[:_EMOJI_MAX_LEN]
