# SPDX-License-Identifier: 0BSD

"""Unit tests for gif validation and export/import document parsing."""

import base64

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend import gif_utils


def test_normalize_image_type():
    assert gif_utils.normalize_image_type("GIF") == "gif"
    assert gif_utils.normalize_image_type("image/webp") == "webp"
    assert gif_utils.normalize_image_type("png") is None
    assert gif_utils.normalize_image_type("jpeg") is None
    assert gif_utils.normalize_image_type("") is None
    assert gif_utils.normalize_image_type(None) is None


def test_validate_gif_payload_ok_gif():
    raw = b"GIF89a" + b"\x00" * 32
    nt, h = gif_utils.validate_gif_payload(raw, "gif")
    assert nt == "gif"
    assert len(h) == 64


def test_validate_gif_payload_ok_webp():
    raw = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 32
    nt, _ = gif_utils.validate_gif_payload(raw, "webp")
    assert nt == "webp"


def test_validate_gif_payload_too_large():
    raw = b"x" * (gif_utils.MAX_GIF_BYTES + 1)
    with pytest.raises(ValueError, match="image_too_large"):
        gif_utils.validate_gif_payload(raw, "gif")


def test_validate_gif_payload_empty():
    with pytest.raises(ValueError, match="empty_image"):
        gif_utils.validate_gif_payload(b"", "gif")


def test_validate_gif_payload_bad_type():
    with pytest.raises(ValueError, match="invalid_image_type"):
        gif_utils.validate_gif_payload(b"GIF89a" + b"\x00" * 8, "png")


def test_validate_gif_payload_bad_magic():
    with pytest.raises(ValueError, match="invalid_image_signature"):
        gif_utils.validate_gif_payload(b"not-a-gif-file", "gif")


def test_validate_gif_payload_magic_type_mismatch():
    raw = b"GIF89a" + b"\x00" * 16
    with pytest.raises(ValueError, match="magic_type_mismatch"):
        gif_utils.validate_gif_payload(raw, "webp")


def test_detect_image_format_from_magic():
    assert gif_utils.detect_image_format_from_magic(b"GIF89a" + b"\x00" * 4) == "gif"
    assert gif_utils.detect_image_format_from_magic(b"GIF87a" + b"\x00" * 4) == "gif"
    webp = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 8
    assert gif_utils.detect_image_format_from_magic(webp) == "webp"
    assert gif_utils.detect_image_format_from_magic(b"\x89PNG\r\n\x1a\n") is None
    assert gif_utils.detect_image_format_from_magic(b"") is None
    assert gif_utils.detect_image_format_from_magic(b"short") is None


def test_sanitize_gif_name():
    assert gif_utils.sanitize_gif_name("  hello  ") == "hello"
    assert gif_utils.sanitize_gif_name("") is None
    assert gif_utils.sanitize_gif_name(None) is None
    assert len(gif_utils.sanitize_gif_name("x" * 200) or "") == 128


def test_validate_export_document_ok():
    raw = b"GIF89a" + b"\x00" * 32
    b64 = base64.b64encode(raw).decode("ascii")
    doc = {
        "format": "meshchatx-gifs",
        "version": 1,
        "gifs": [
            {"name": "g1", "image_type": "gif", "image_bytes": b64, "usage_count": 5},
        ],
    }
    items = gif_utils.validate_export_document(doc)
    assert len(items) == 1
    assert items[0]["image_bytes_b64"] == b64
    assert items[0]["usage_count"] == 5


def test_validate_export_document_negative_usage_clamped():
    raw = b"GIF89a" + b"\x00" * 32
    b64 = base64.b64encode(raw).decode("ascii")
    doc = {
        "format": "meshchatx-gifs",
        "version": 1,
        "gifs": [
            {"name": None, "image_type": "gif", "image_bytes": b64, "usage_count": -5},
        ],
    }
    items = gif_utils.validate_export_document(doc)
    assert items[0]["usage_count"] == 0


def test_validate_export_document_wrong_format():
    with pytest.raises(ValueError, match="invalid_format"):
        gif_utils.validate_export_document(
            {"format": "meshchatx-stickers", "version": 1, "gifs": []},
        )


def test_validate_export_document_bad_version():
    with pytest.raises(ValueError, match="unsupported_version"):
        gif_utils.validate_export_document(
            {"format": "meshchatx-gifs", "version": 99, "gifs": []},
        )


def test_validate_export_document_missing_gifs_array():
    with pytest.raises(ValueError, match="invalid_gifs_array"):
        gif_utils.validate_export_document(
            {"format": "meshchatx-gifs", "version": 1},
        )


def test_validate_export_document_missing_image_bytes():
    with pytest.raises(ValueError, match="missing_image_bytes_at_0"):
        gif_utils.validate_export_document(
            {
                "format": "meshchatx-gifs",
                "version": 1,
                "gifs": [{"name": "x", "image_type": "gif", "image_bytes": ""}],
            },
        )


def test_validate_export_document_not_dict():
    with pytest.raises(ValueError, match="invalid_document"):
        gif_utils.validate_export_document([])


def test_mime_for_image_type():
    assert gif_utils.mime_for_image_type("gif") == "image/gif"
    assert gif_utils.mime_for_image_type("webp") == "image/webp"
    assert gif_utils.mime_for_image_type("png") == "application/octet-stream"


def test_build_export_document_shape():
    doc = gif_utils.build_export_document([{"x": 1}], "2026-01-01T00:00:00Z")
    assert doc["format"] == "meshchatx-gifs"
    assert doc["version"] == 1
    assert doc["gifs"] == [{"x": 1}]
    assert doc["exported_at"] == "2026-01-01T00:00:00Z"


@settings(max_examples=200, deadline=None)
@given(
    raw=st.binary(min_size=0, max_size=4096),
    typ=st.one_of(
        st.none(),
        st.text(max_size=40),
        st.sampled_from(["gif", "webp", "image/gif", "image/webp", "png", ""]),
    ),
)
def test_validate_gif_payload_fuzz_never_raises_unexpected(raw, typ):
    """Fuzz: validation either succeeds or raises ValueError with known reasons."""
    try:
        gif_utils.validate_gif_payload(raw, typ)
    except ValueError:
        pass


@settings(max_examples=500, deadline=None)
@given(raw=st.binary(min_size=0, max_size=4096))
def test_detect_image_format_from_magic_fuzz_never_raises(raw):
    out = gif_utils.detect_image_format_from_magic(raw)
    assert out is None or out in {"gif", "webp"}
