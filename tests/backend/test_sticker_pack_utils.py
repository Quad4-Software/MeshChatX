# SPDX-License-Identifier: 0BSD

"""Unit tests for sticker pack document validation and sanitisation."""

import base64

import pytest

from meshchatx.src.backend import sticker_pack_utils


def test_sanitize_pack_title_default():
    assert sticker_pack_utils.sanitize_pack_title(None) == "Untitled pack"
    assert sticker_pack_utils.sanitize_pack_title("   ") == "Untitled pack"
    assert sticker_pack_utils.sanitize_pack_title("  hello  ") == "hello"
    assert len(sticker_pack_utils.sanitize_pack_title("x" * 500)) == 80


def test_sanitize_pack_short_name():
    assert sticker_pack_utils.sanitize_pack_short_name(None) is None
    assert sticker_pack_utils.sanitize_pack_short_name("Cats!@#") == "cats"
    assert (
        sticker_pack_utils.sanitize_pack_short_name(" Hello_World-1 ")
        == "hello_world-1"
    )
    assert sticker_pack_utils.sanitize_pack_short_name("***") is None
    assert len(sticker_pack_utils.sanitize_pack_short_name("a" * 200)) == 32


def test_sanitize_pack_description():
    assert sticker_pack_utils.sanitize_pack_description(None) is None
    assert sticker_pack_utils.sanitize_pack_description("   ") is None
    assert sticker_pack_utils.sanitize_pack_description(" hi\nthere ") == "hi\nthere"
    assert len(sticker_pack_utils.sanitize_pack_description("x" * 1000)) == 280


def test_sanitize_pack_type():
    assert sticker_pack_utils.sanitize_pack_type(None) == "mixed"
    assert sticker_pack_utils.sanitize_pack_type("") == "mixed"
    assert sticker_pack_utils.sanitize_pack_type("static") == "static"
    assert sticker_pack_utils.sanitize_pack_type("ANIMATED") == "animated"
    assert sticker_pack_utils.sanitize_pack_type("VIDEO") == "video"
    assert sticker_pack_utils.sanitize_pack_type("garbage") == "mixed"


def test_build_pack_document_shape():
    pack = {
        "title": " My Pack ",
        "short_name": "MyPack!",
        "description": "desc",
        "pack_type": "static",
        "author": "alice",
        "is_strict": True,
    }
    doc = sticker_pack_utils.build_pack_document(pack, [], "2026-01-01T00:00:00Z")
    assert doc["format"] == "meshchatx-stickerpack"
    assert doc["version"] == 1
    assert doc["pack"]["title"] == "My Pack"
    assert doc["pack"]["short_name"] == "mypack"
    assert doc["pack"]["type"] == "static"
    assert doc["pack"]["author"] == "alice"
    assert doc["stickers"] == []


def test_validate_pack_document_ok():
    b64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8).decode("ascii")
    doc = {
        "format": "meshchatx-stickerpack",
        "version": 1,
        "pack": {
            "title": "Cats",
            "short_name": "cats",
            "description": None,
            "type": "static",
            "author": None,
            "is_strict": True,
        },
        "stickers": [
            {"name": "kitten", "emoji": "cat", "image_type": "png", "image_bytes": b64},
        ],
    }
    out = sticker_pack_utils.validate_pack_document(doc)
    assert out["pack"]["title"] == "Cats"
    assert out["pack"]["pack_type"] == "static"
    assert len(out["stickers"]) == 1
    assert out["stickers"][0]["image_bytes_b64"] == b64
    assert out["stickers"][0]["emoji"] == "cat"


def test_validate_pack_document_wrong_format():
    with pytest.raises(ValueError, match="invalid_pack_format"):
        sticker_pack_utils.validate_pack_document(
            {"format": "other", "version": 1, "pack": {}, "stickers": []},
        )


def test_validate_pack_document_unsupported_version():
    with pytest.raises(ValueError, match="unsupported_pack_version"):
        sticker_pack_utils.validate_pack_document(
            {
                "format": "meshchatx-stickerpack",
                "version": 99,
                "pack": {},
                "stickers": [],
            },
        )


def test_validate_pack_document_not_dict():
    with pytest.raises(ValueError, match="invalid_pack_document"):
        sticker_pack_utils.validate_pack_document([])


def test_validate_pack_document_missing_meta():
    with pytest.raises(ValueError, match="invalid_pack_meta"):
        sticker_pack_utils.validate_pack_document(
            {"format": "meshchatx-stickerpack", "version": 1, "stickers": []},
        )


def test_validate_pack_document_bad_stickers():
    with pytest.raises(ValueError, match="invalid_pack_stickers"):
        sticker_pack_utils.validate_pack_document(
            {
                "format": "meshchatx-stickerpack",
                "version": 1,
                "pack": {},
                "stickers": "no",
            },
        )


def test_validate_pack_document_bad_sticker_entry():
    with pytest.raises(ValueError, match="invalid_pack_sticker_at_0"):
        sticker_pack_utils.validate_pack_document(
            {
                "format": "meshchatx-stickerpack",
                "version": 1,
                "pack": {},
                "stickers": ["nope"],
            },
        )


def test_validate_pack_document_missing_bytes():
    with pytest.raises(ValueError, match="missing_pack_sticker_bytes_at_0"):
        sticker_pack_utils.validate_pack_document(
            {
                "format": "meshchatx-stickerpack",
                "version": 1,
                "pack": {},
                "stickers": [{"name": "x", "image_type": "png"}],
            },
        )
