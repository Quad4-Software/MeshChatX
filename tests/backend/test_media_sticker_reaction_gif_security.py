# SPDX-License-Identifier: 0BSD

"""Fuzz and security-style tests for stickers, GIFs, reactions, and related sanitizers."""

import base64
import os
from unittest.mock import MagicMock

import LXMF
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend import (
    gif_utils,
    lxmf_utils,
    sticker_pack_utils,
    sticker_utils,
)


_TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
    b"\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00"
    b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@settings(max_examples=150, deadline=None)
@given(s=st.text(max_size=5000, alphabet=st.characters(blacklist_categories=("Cs",))))
def test_sanitize_sticker_name_fuzzing(s):
    out = sticker_utils.sanitize_sticker_name(s)
    assert out is None or (
        isinstance(out, str) and len(out) <= 128 and all(c.isprintable() for c in out)
    )


@settings(max_examples=150, deadline=None)
@given(s=st.text(max_size=500, alphabet=st.characters(blacklist_categories=("Cs",))))
def test_sanitize_sticker_emoji_fuzzing(s):
    out = sticker_utils.sanitize_sticker_emoji(s)
    assert out is None or (
        isinstance(out, str) and len(out) <= 16 and all(c.isprintable() for c in out)
    )


@settings(max_examples=120, deadline=None)
@given(s=st.text(max_size=2000, alphabet=st.characters(blacklist_categories=("Cs",))))
def test_sanitize_gif_name_fuzzing(s):
    out = gif_utils.sanitize_gif_name(s)
    assert out is None or (
        isinstance(out, str) and len(out) <= 128 and all(c.isprintable() for c in out)
    )


@settings(max_examples=100, deadline=None)
@given(s=st.text(max_size=500, alphabet=st.characters(blacklist_categories=("Cs",))))
def test_sticker_normalize_image_type_fuzzing(s):
    sticker_utils.normalize_image_type(s)


@settings(max_examples=100, deadline=None)
@given(s=st.text(max_size=500, alphabet=st.characters(blacklist_categories=("Cs",))))
def test_gif_normalize_image_type_fuzzing(s):
    gif_utils.normalize_image_type(s)


@pytest.mark.parametrize(
    "title,short_name,desc",
    [
        ("<script>x</script>", "ok_pack", "d"),
        ("t", "bad<script>", "e"),
        ("t", "ok", "<svg onload=alert(1)>"),
        ("x" * 1000, "y" * 100, "z" * 500),
    ],
)
def test_sticker_pack_sanitizers_accept_malicious_strings(title, short_name, desc):
    assert len(sticker_pack_utils.sanitize_pack_title(title)) <= 80
    sn = sticker_pack_utils.sanitize_pack_short_name(short_name)
    assert sn is None or (len(sn) <= 32 and "<" not in sn)
    d = sticker_pack_utils.sanitize_pack_description(desc)
    assert d is None or len(d) <= 280


def test_validate_export_document_sticker_xss_fields_parse():
    b64 = base64.b64encode(_TINY_PNG).decode("ascii")
    doc = {
        "format": "meshchatx-stickers",
        "version": 1,
        "stickers": [
            {
                "name": "<img src=x onerror=alert(1)>",
                "emoji": "<script>emoji</script>",
                "image_type": "png",
                "image_bytes": b64,
            },
        ],
    }
    rows = sticker_utils.validate_export_document(doc)
    assert len(rows) == 1
    assert rows[0]["emoji"] == "<script>emoji</script>"
    sn = sticker_utils.sanitize_sticker_name(rows[0]["name"])
    assert sn is not None and len(sn) <= 128
    em = sticker_utils.sanitize_sticker_emoji(rows[0]["emoji"])
    assert em is not None and len(em) <= 16


def test_validate_gif_payload_rejects_wrong_magic():
    with pytest.raises(ValueError, match="signature|mismatch"):
        gif_utils.validate_gif_payload(_TINY_PNG, "gif")


def test_validate_gif_payload_accepts_minimal_gif():
    nt, h = gif_utils.validate_gif_payload(_TINY_GIF, "gif")
    assert nt == "gif"
    assert len(h) == 64


def _minimal_lxmf_mock_reaction(reaction_to: str, emoji: str):
    m = MagicMock()
    m.hash = os.urandom(16)
    m.source_hash = os.urandom(16)
    m.destination_hash = os.urandom(16)
    m.incoming = True
    m.state = LXMF.LXMessage.DELIVERED
    m.method = LXMF.LXMessage.OPPORTUNISTIC
    m.progress = 1.0
    m.delivery_attempts = 0
    m.title = b""
    m.content = b""
    m.timestamp = 1.0
    m.rssi = None
    m.snr = None
    m.q = None
    target_bytes = None
    try:
        target_bytes = bytes.fromhex(reaction_to)
    except ValueError:
        target_bytes = reaction_to.encode("utf-8", errors="replace")
    m.get_fields.return_value = {
        lxmf_utils.FIELD_REACTION: {
            lxmf_utils.REACTION_TO: target_bytes,
            lxmf_utils.REACTION_CONTENT: emoji.encode("utf-8", errors="replace"),
        },
    }
    return m


@settings(max_examples=80, deadline=None)
@given(
    emoji=st.text(max_size=800, alphabet=st.characters(blacklist_categories=("Cs",))),
    reaction_to=st.text(max_size=64, alphabet="0123456789abcdef"),
)
def test_convert_lxmf_reaction_field_fuzzing(emoji, reaction_to):
    if len(reaction_to) % 2 != 0:
        reaction_to = "0" + reaction_to
    out = lxmf_utils.convert_lxmf_message_to_dict(
        _minimal_lxmf_mock_reaction(reaction_to, emoji),
        include_attachments=False,
    )
    assert out["is_reaction"] is True
    assert isinstance(out.get("reaction_emoji"), str)
    assert isinstance(out.get("reaction_to"), str)
    assert isinstance(out.get("reaction_sender"), str)


def test_validate_export_document_gif_xss_names():
    b64 = base64.b64encode(_TINY_GIF).decode("ascii")
    doc = {
        "format": "meshchatx-gifs",
        "version": 1,
        "gifs": [
            {
                "name": "javascript:alert(1)",
                "image_type": "gif",
                "image_bytes": b64,
                "usage_count": 0,
            },
        ],
    }
    rows = gif_utils.validate_export_document(doc)
    assert len(rows) == 1
    assert gif_utils.sanitize_gif_name(rows[0]["name"]) == "javascript:alert(1)"[:128]
