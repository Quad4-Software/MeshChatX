# SPDX-License-Identifier: 0BSD

"""LXMF attachment image serving must trust magic bytes, not declared type."""

import base64

from meshchatx.src.backend.sticker_utils import detect_image_format_from_magic


_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_ALLOWED = {"png", "jpeg", "jpg", "gif", "webp", "bmp"}


def _resolve_served_image_type(image_data: bytes) -> str | None:
    detected = detect_image_format_from_magic(image_data)
    if detected is None or detected not in _ALLOWED:
        return None
    return "jpeg" if detected == "jpeg" else detected


def test_lxmf_image_serve_uses_png_magic_not_declared_html():
    assert _resolve_served_image_type(_PNG) == "png"
    assert _resolve_served_image_type(b"<html><script>x</script>") is None
    assert _resolve_served_image_type(b"") is None


def test_lxmf_image_send_rejects_non_image_payload():
    raw = b"not-an-image"
    detected = detect_image_format_from_magic(raw)
    assert detected is None or detected in {"webm", "tgs"}


def test_png_bytes_survive_b64_roundtrip_detection():
    b64 = base64.b64encode(_PNG).decode("ascii")
    assert detect_image_format_from_magic(base64.b64decode(b64)) == "png"
