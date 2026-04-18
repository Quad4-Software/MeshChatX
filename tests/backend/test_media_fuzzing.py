# SPDX-License-Identifier: 0BSD

"""Heavy property-based fuzzing for sticker/TGS/Lottie, WebM, GIFs, and pack JSON.

Run: pytest tests/backend/test_media_fuzzing.py
"""

from __future__ import annotations

import base64
import gzip
import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend import gif_utils, sticker_pack_utils, sticker_utils

_JSON_LEAF = (
    st.none()
    | st.booleans()
    | st.integers(min_value=-(2**53), max_value=2**53)
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=64)
    | st.binary(max_size=128)
)


def _recursive_json(max_leaves: int = 24):
    return st.recursive(
        _JSON_LEAF,
        lambda children: st.lists(children, max_size=8)
        | st.dictionaries(st.text(max_size=12), children, max_size=8),
        max_leaves=max_leaves,
    )


@settings(max_examples=400, deadline=None)
@given(raw=st.binary(min_size=0, max_size=sticker_utils.MAX_ANIMATED_BYTES + 2))
def test_parse_tgs_fuzz_never_raises_unexpected(raw):
    try:
        sticker_utils.parse_tgs(raw)
    except ValueError:
        pass


@settings(max_examples=350, deadline=None)
@given(
    payload=st.dictionaries(
        keys=st.text(max_size=8, alphabet=st.characters(blacklist_categories=("Cs",))),
        values=_recursive_json(20),
        max_size=24,
    ),
)
def test_parse_tgs_gzip_json_fuzz(payload):
    merged = dict(payload)
    merged.setdefault("v", "5.5.7")
    merged.setdefault("fr", 30.0)
    merged.setdefault("ip", 0.0)
    merged.setdefault("op", 60.0)
    merged.setdefault("w", 100)
    merged.setdefault("h", 100)
    raw = gzip.compress(json.dumps(merged, default=str).encode("utf-8", errors="surrogateescape"))
    if len(raw) > sticker_utils.MAX_ANIMATED_BYTES:
        raw = raw[: sticker_utils.MAX_ANIMATED_BYTES]
    try:
        sticker_utils.parse_tgs(raw)
    except ValueError:
        pass


@settings(max_examples=400, deadline=None)
@given(tail=st.binary(min_size=0, max_size=12_288))
def test_parse_webm_fuzz_never_raises_unexpected(tail):
    raw = b"\x1a\x45\xdf\xa3" + tail
    if len(raw) < 32:
        raw = raw + b"\x00" * (32 - len(raw))
    try:
        sticker_utils.parse_webm(raw)
    except ValueError:
        pass


@settings(max_examples=300, deadline=None)
@given(
    image_type=st.one_of(
        st.none(),
        st.text(max_size=48),
        st.sampled_from(
            ["png", "jpeg", "webp", "gif", "bmp", "tgs", "webm", "svg", "image/png", ""],
        ),
    ),
    raw=st.binary(min_size=0, max_size=8192),
)
def test_extract_metadata_fuzz_never_raises(image_type, raw):
    it = image_type if isinstance(image_type, str) else "png"
    sticker_utils.extract_metadata(it, raw)


@settings(max_examples=500, deadline=None)
@given(
    raw=st.binary(min_size=0, max_size=8192),
    typ=st.one_of(
        st.none(),
        st.text(max_size=48),
        st.sampled_from(["png", "jpeg", "jpg", "webp", "gif", "bmp", "tgs", "webm", "svg", ""]),
    ),
    strict=st.booleans(),
)
def test_validate_sticker_payload_fuzz_extended(raw, typ, strict):
    try:
        sticker_utils.validate_sticker_payload(raw, typ, strict=strict)
    except ValueError:
        pass


@settings(max_examples=250, deadline=None)
@given(
    nt=st.sampled_from(["png", "jpeg", "webp", "gif", "bmp"]),
    raw=st.binary(min_size=0, max_size=4096),
)
def test_detect_image_dimensions_fuzz_never_raises(nt, raw):
    sticker_utils.detect_image_dimensions(nt, raw)


@settings(max_examples=600, deadline=None)
@given(name=st.one_of(st.none(), st.text(max_size=300)))
def test_sanitize_sticker_name_fuzz_never_raises(name):
    sticker_utils.sanitize_sticker_name(name)


@settings(max_examples=600, deadline=None)
@given(emoji=st.one_of(st.none(), st.text(max_size=120)))
def test_sanitize_sticker_emoji_fuzz_never_raises(emoji):
    sticker_utils.sanitize_sticker_emoji(emoji)


@settings(max_examples=400, deadline=None)
@given(t=st.text(max_size=120))
def test_mime_for_image_type_fuzz_never_raises(t):
    sticker_utils.mime_for_image_type(t)


@settings(max_examples=400, deadline=None)
@given(
    title=st.one_of(st.none(), st.text(max_size=200)),
    short_name=st.one_of(st.none(), st.text(max_size=120)),
    description=st.one_of(st.none(), st.text(max_size=400)),
    pack_type=st.one_of(st.none(), st.text(max_size=40)),
)
def test_sticker_pack_sanitizers_fuzz_never_raises(title, short_name, description, pack_type):
    sticker_pack_utils.sanitize_pack_title(title)
    sticker_pack_utils.sanitize_pack_short_name(short_name)
    sticker_pack_utils.sanitize_pack_description(description)
    sticker_pack_utils.sanitize_pack_type(pack_type)


@settings(max_examples=250, deadline=None)
@given(doc=_recursive_json(28))
def test_validate_pack_document_fuzz_never_raises_unexpected(doc):
    if not isinstance(doc, dict):
        doc = {"x": doc}
    try:
        sticker_pack_utils.validate_pack_document(doc)
    except ValueError:
        pass


@settings(max_examples=300, deadline=None)
@given(
    raw=st.binary(min_size=0, max_size=min(256 * 1024, gif_utils.MAX_GIF_BYTES + 1)),
    typ=st.one_of(
        st.none(),
        st.text(max_size=48),
        st.sampled_from(["gif", "webp", "image/gif", "image/webp", "png", ""]),
    ),
)
def test_validate_gif_payload_fuzz_extended(raw, typ):
    try:
        gif_utils.validate_gif_payload(raw, typ)
    except ValueError:
        pass


@settings(max_examples=400, deadline=None)
@given(name=st.one_of(st.none(), st.text(max_size=300)))
def test_sanitize_gif_name_fuzz_never_raises(name):
    gif_utils.sanitize_gif_name(name)


@settings(max_examples=250, deadline=None)
@given(doc=_recursive_json(28))
def test_gif_validate_export_document_fuzz_never_raises_unexpected(doc):
    if not isinstance(doc, dict):
        doc = {"k": doc}
    try:
        gif_utils.validate_export_document(doc)
    except ValueError:
        pass


@settings(max_examples=200, deadline=None)
@given(
    inner=st.dictionaries(
        keys=st.text(max_size=12),
        values=_recursive_json(16),
        max_size=16,
    ),
)
def test_strict_tgs_from_structured_gzip_json_fuzz(inner):
    doc = {
        "v": "5.0.0",
        "fr": 45.0,
        "ip": 0.0,
        "op": 90.0,
        "w": 512,
        "h": 512,
        "nm": "fuzz",
        "ddd": 0,
        "assets": [],
        "layers": [],
    }
    for k, v in inner.items():
        if k not in doc:
            doc[k] = v
    raw = gzip.compress(json.dumps(doc, default=str).encode("ascii"))
    if len(raw) > sticker_utils.MAX_ANIMATED_BYTES:
        return
    try:
        sticker_utils.validate_sticker_payload(raw, "tgs", strict=True)
    except ValueError:
        pass


@settings(max_examples=150, deadline=None)
@given(
    b64=st.one_of(st.text(max_size=400), st.binary(max_size=200).map(lambda b: base64.b64encode(b).decode("ascii"))),
)
def test_sticker_validate_export_document_sticker_rows_fuzz(b64):
    doc = {
        "format": "meshchatx-stickers",
        "version": 1,
        "stickers": [
            {
                "name": "n",
                "image_type": "png",
                "image_bytes": b64,
                "emoji": None,
            },
        ],
    }
    try:
        sticker_utils.validate_export_document(doc)
    except ValueError:
        pass
