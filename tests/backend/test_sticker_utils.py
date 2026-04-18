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
    prefix = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
    raw = prefix + b"x" * (sticker_utils.MAX_STICKER_BYTES + 1 - len(prefix))
    assert len(raw) > sticker_utils.MAX_STICKER_BYTES
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
    assert (
        sticker_utils.detect_image_format_from_magic(b"\x1a\x45\xdf\xa3" + b"\x00" * 8)
        == "webm"
    )
    assert (
        sticker_utils.detect_image_format_from_magic(b"\x1f\x8b\x08\x00" + b"\x00" * 8)
        == "tgs"
    )
    assert sticker_utils.detect_image_format_from_magic(b"") is None
    assert sticker_utils.detect_image_format_from_magic(b"short") is None


def test_normalize_image_type_extended():
    assert sticker_utils.normalize_image_type("tgs") == "tgs"
    assert sticker_utils.normalize_image_type("application/x-tgsticker") == "tgs"
    assert sticker_utils.normalize_image_type("video/webm") == "webm"
    assert sticker_utils.normalize_image_type("webm") == "webm"


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
    assert out is None or out in {"png", "jpeg", "gif", "webp", "bmp", "tgs", "webm"}


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


def _build_tgs(
    width: int = 512, height: int = 512, fps: float = 30.0, frames: int = 60
) -> bytes:
    import gzip
    import json

    lottie = {
        "v": "5.0.0",
        "fr": fps,
        "ip": 0,
        "op": frames,
        "w": width,
        "h": height,
        "nm": "test",
        "ddd": 0,
        "assets": [],
        "layers": [],
    }
    return gzip.compress(json.dumps(lottie).encode("ascii"))


def test_parse_tgs_golden_shared_asset():
    from tests.backend.media_test_assets import GZIP_TGS_512

    meta = sticker_utils.parse_tgs(GZIP_TGS_512)
    assert meta["width"] == 512
    assert meta["height"] == 512
    assert meta["duration_ms"] == 2000


def test_parse_tgs_ok():
    raw = _build_tgs()
    meta = sticker_utils.parse_tgs(raw)
    assert meta["width"] == 512
    assert meta["height"] == 512
    assert abs(meta["fps"] - 30.0) < 1e-6
    assert meta["duration_ms"] == 2000


def test_parse_tgs_invalid_gzip():
    with pytest.raises(ValueError, match="invalid_tgs"):
        sticker_utils.parse_tgs(b"\x1f\x8bbroken")


def test_parse_tgs_invalid_metadata():
    import gzip
    import json

    raw = gzip.compress(
        json.dumps({"w": 0, "h": 0, "fr": 0, "ip": 0, "op": 0}).encode()
    )
    with pytest.raises(ValueError, match="invalid_tgs_metadata"):
        sticker_utils.parse_tgs(raw)


def test_validate_strict_tgs_ok():
    raw = _build_tgs()
    nt, h = sticker_utils.validate_sticker_payload(raw, "tgs", strict=True)
    assert nt == "tgs"
    assert len(h) == 64


def test_validate_strict_tgs_too_large():
    big = b"\x1f\x8b" + b"\x00" * (sticker_utils.MAX_ANIMATED_BYTES + 1)
    with pytest.raises(ValueError, match="animated_too_large"):
        sticker_utils.validate_sticker_payload(big, "tgs", strict=True)


def test_validate_strict_tgs_bad_fps():
    raw = _build_tgs(fps=10.0, frames=20)
    with pytest.raises(ValueError, match="animated_fps_out_of_range"):
        sticker_utils.validate_sticker_payload(raw, "tgs", strict=True)


def test_validate_strict_tgs_bad_dims():
    raw = _build_tgs(width=256, height=256)
    with pytest.raises(ValueError, match="animated_dimensions_invalid"):
        sticker_utils.validate_sticker_payload(raw, "tgs", strict=True)


def test_validate_strict_tgs_too_long():
    raw = _build_tgs(fps=30.0, frames=120)
    with pytest.raises(ValueError, match="animated_duration_too_long"):
        sticker_utils.validate_sticker_payload(raw, "tgs", strict=True)


def test_legacy_rejects_tgs():
    raw = _build_tgs()
    with pytest.raises(ValueError, match="invalid_image_type"):
        sticker_utils.validate_sticker_payload(raw, "tgs", strict=False)


def test_parse_webm_invalid():
    with pytest.raises(ValueError, match="invalid_webm"):
        sticker_utils.parse_webm(b"")
    with pytest.raises(ValueError, match="invalid_webm_header"):
        sticker_utils.parse_webm(b"NOTWEBMHEADER" + b"\x00" * 32)


def test_validate_strict_webm_too_large():
    raw = b"\x1a\x45\xdf\xa3" + b"\x00" * (sticker_utils.MAX_VIDEO_BYTES + 1)
    with pytest.raises(ValueError, match="video_too_large"):
        sticker_utils.validate_sticker_payload(raw, "webm", strict=True)


def test_detect_image_dimensions_png():
    raw = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + struct_pack(512, 512)
        + b"\x08\x06\x00\x00\x00"
    )
    assert sticker_utils.detect_image_dimensions("png", raw) == (512, 512)


def struct_pack(w: int, h: int) -> bytes:
    import struct as _s

    return _s.pack(">II", w, h)


def test_detect_image_dimensions_webp_vp8():
    import struct as _struct

    vp8_payload = b"\x00" * 6 + _struct.pack("<HH", 512, 512)
    after_webp = b"VP8 " + _struct.pack("<I", len(vp8_payload)) + vp8_payload
    raw = b"RIFF" + _struct.pack("<I", len(b"WEBP" + after_webp)) + b"WEBP" + after_webp
    assert sticker_utils.detect_image_dimensions("webp", raw) == (512, 512)


def test_sanitize_sticker_emoji():
    assert sticker_utils.sanitize_sticker_emoji(None) is None
    assert sticker_utils.sanitize_sticker_emoji("") is None
    assert sticker_utils.sanitize_sticker_emoji("  ") is None
    assert sticker_utils.sanitize_sticker_emoji("hi") == "hi"
    long = "x" * 200
    assert sticker_utils.sanitize_sticker_emoji(long) == "x" * 16


def test_extract_metadata_tgs():
    raw = _build_tgs()
    meta = sticker_utils.extract_metadata("tgs", raw)
    assert meta["is_animated"] is True
    assert meta["is_video"] is False
    assert meta["width"] == 512
    assert meta["height"] == 512
    assert meta["duration_ms"] == 2000


def test_extract_metadata_static_png():
    raw = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + struct_pack(512, 256)
        + b"\x08\x06\x00\x00\x00"
    )
    meta = sticker_utils.extract_metadata("png", raw)
    assert meta["width"] == 512
    assert meta["height"] == 256
    assert meta["is_animated"] is False
    assert meta["is_video"] is False
