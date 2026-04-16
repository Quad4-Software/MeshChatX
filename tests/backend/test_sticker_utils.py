# SPDX-License-Identifier: 0BSD

"""Unit tests for sticker validation and export/import document parsing."""

import base64

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend import sticker_utils


def test_normalize_image_type():
    assert sticker_utils.normalize_image_type("PNG") == "png"
    assert sticker_utils.normalize_image_type("image/jpeg") == "jpeg"
    assert sticker_utils.normalize_image_type("jpg") == "jpeg"
    assert sticker_utils.normalize_image_type("webp") == "webp"
    assert sticker_utils.normalize_image_type("svg") is None
    assert sticker_utils.normalize_image_type("") is None
    assert sticker_utils.normalize_image_type(None) is None


def test_validate_sticker_payload_ok():
    raw = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    nt, h = sticker_utils.validate_sticker_payload(raw, "png")
    assert nt == "png"
    assert len(h) == 64


def test_validate_sticker_payload_too_large():
    raw = b"x" * (sticker_utils.MAX_STICKER_BYTES + 1)
    with pytest.raises(ValueError, match="image_too_large"):
        sticker_utils.validate_sticker_payload(raw, "png")


def test_validate_sticker_payload_empty():
    with pytest.raises(ValueError, match="empty_image"):
        sticker_utils.validate_sticker_payload(b"", "png")


def test_validate_sticker_payload_bad_type():
    with pytest.raises(ValueError, match="invalid_image_type"):
        sticker_utils.validate_sticker_payload(b"abc", "svg")


def test_validate_sticker_payload_bad_magic():
    with pytest.raises(ValueError, match="invalid_image_signature"):
        sticker_utils.validate_sticker_payload(b"not-an-image-bytes", "png")


def test_validate_sticker_payload_magic_type_mismatch():
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    with pytest.raises(ValueError, match="magic_type_mismatch"):
        sticker_utils.validate_sticker_payload(png_bytes, "jpeg")


def test_detect_image_format_from_magic():
    assert sticker_utils.detect_image_format_from_magic(b"\x89PNG\r\n\x1a\n") == "png"
    assert (
        sticker_utils.detect_image_format_from_magic(b"\xff\xd8\xff\xe0\x00\x10")
        == "jpeg"
    )
    assert (
        sticker_utils.detect_image_format_from_magic(b"GIF89a" + b"\x00" * 4) == "gif"
    )
    assert sticker_utils.detect_image_format_from_magic(b"BM" + b"\x00" * 20) == "bmp"
    webp = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 8
    assert sticker_utils.detect_image_format_from_magic(webp) == "webp"
    assert sticker_utils.detect_image_format_from_magic(b"") is None
    assert sticker_utils.detect_image_format_from_magic(b"short") is None


def test_validate_sticker_payload_jpg_alias_matches_jpeg_magic():
    raw = b"\xff\xd8\xff\xe0" + b"\x00" * 64
    nt, _ = sticker_utils.validate_sticker_payload(raw, "jpg")
    assert nt == "jpeg"


def test_sanitize_sticker_name():
    assert sticker_utils.sanitize_sticker_name("  hello  ") == "hello"
    assert sticker_utils.sanitize_sticker_name("") is None
    assert sticker_utils.sanitize_sticker_name("x" * 200) is not None
    assert len(sticker_utils.sanitize_sticker_name("x" * 200) or "") == 128


def test_validate_export_document_ok():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    b64 = base64.b64encode(png).decode("ascii")
    doc = {
        "format": "meshchatx-stickers",
        "version": 1,
        "stickers": [
            {"name": "a", "image_type": "png", "image_bytes": b64},
        ],
    }
    items = sticker_utils.validate_export_document(doc)
    assert len(items) == 1
    assert items[0]["image_bytes_b64"] == b64


def test_validate_export_document_wrong_format():
    with pytest.raises(ValueError, match="invalid_format"):
        sticker_utils.validate_export_document(
            {"format": "other", "version": 1, "stickers": []},
        )


def test_validate_export_document_bad_version():
    with pytest.raises(ValueError, match="unsupported_version"):
        sticker_utils.validate_export_document(
            {"format": "meshchatx-stickers", "version": 99, "stickers": []},
        )


def test_validate_export_document_missing_version():
    with pytest.raises(ValueError, match="unsupported_version"):
        sticker_utils.validate_export_document(
            {"format": "meshchatx-stickers", "stickers": []},
        )


def test_validate_export_document_not_dict():
    with pytest.raises(ValueError, match="invalid_document"):
        sticker_utils.validate_export_document([])


def test_mime_for_image_type():
    assert "image/" in sticker_utils.mime_for_image_type("png")
    assert sticker_utils.mime_for_image_type("unknown") == "application/octet-stream"


@settings(max_examples=200, deadline=None)
@given(
    raw=st.binary(min_size=0, max_size=sticker_utils.MAX_STICKER_BYTES + 1),
    typ=st.one_of(
        st.none(),
        st.text(max_size=40),
        st.sampled_from(
            ["png", "jpeg", "jpg", "webp", "gif", "bmp", "svg", "image/png", ""],
        ),
    ),
)
def test_validate_sticker_payload_fuzz_never_raises_unexpected(raw, typ):
    """Fuzz: validation either succeeds or raises ValueError with known reasons."""
    try:
        sticker_utils.validate_sticker_payload(raw, typ)
    except ValueError:
        pass


@settings(max_examples=500, deadline=None)
@given(raw=st.binary(min_size=0, max_size=4096))
def test_detect_image_format_from_magic_fuzz_never_raises(raw):
    out = sticker_utils.detect_image_format_from_magic(raw)
    assert out is None or out in {"png", "jpeg", "gif", "webp", "bmp"}


@settings(max_examples=100, deadline=None)
@given(
    doc=st.dictionaries(
        keys=st.text(max_size=16),
        values=st.recursive(
            st.none()
            | st.booleans()
            | st.floats(allow_nan=False)
            | st.text(max_size=40)
            | st.binary(max_size=48),
            lambda children: (
                st.lists(children, max_size=3)
                | st.dictionaries(st.text(max_size=6), children, max_size=3)
            ),
            max_leaves=12,
        ),
        max_size=8,
    ),
)
def test_validate_export_document_fuzz_never_raises_unexpected(doc):
    try:
        sticker_utils.validate_export_document(doc)
    except ValueError:
        pass
