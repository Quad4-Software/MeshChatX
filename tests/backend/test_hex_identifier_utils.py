# SPDX-License-Identifier: 0BSD

from hypothesis import given
from hypothesis import strategies as st

from meshchatx.src.backend.meshchat_utils import (
    hex_identifier_to_bytes,
    normalize_hex_identifier,
)


def test_normalize_hex_identifier_strips_uuid_separators():
    u = "BA7F0E59-FC70-4E77-9438-FA83A090F74A"
    assert normalize_hex_identifier(u) == "ba7f0e59fc704e779438fa83a090f74a"


def test_normalize_hex_identifier_strips_colons_and_spaces():
    assert normalize_hex_identifier("AB: CD : EF") == "abcdef"


def test_hex_identifier_to_bytes_uuid_style():
    u = "ba7f0e59-fc70-4e77-9438-fa83a090f74a"
    b = hex_identifier_to_bytes(u)
    assert b is not None
    assert len(b) == 16


def test_hex_identifier_to_bytes_standard_hash():
    h = "a" * 64
    b = hex_identifier_to_bytes(h)
    assert b is not None
    assert len(b) == 32


def test_hex_identifier_to_bytes_invalid_returns_none():
    assert hex_identifier_to_bytes("not-hex") is None
    assert hex_identifier_to_bytes("") is None
    assert hex_identifier_to_bytes(None) is None
    assert hex_identifier_to_bytes("abc") is None


@given(s=st.one_of(st.none(), st.text(), st.binary(), st.integers()))
def test_normalize_hex_identifier_oracle(s):
    """Output is only lowercase hex digits, empty for non-str or empty input."""
    out = normalize_hex_identifier(s)  # type: ignore[arg-type]
    if not isinstance(s, str) or not s:
        assert out == ""
        return
    assert isinstance(out, str)
    assert all(c in "0123456789abcdef" for c in out)
    assert out == "".join(c for c in s.strip().lower() if c in "0123456789abcdef")


@given(s=st.one_of(st.none(), st.text(max_size=400)))
def test_hex_identifier_to_bytes_oracle(s):
    """Accept only even-length normalized hex. Reject odd or empty."""
    n = normalize_hex_identifier(s)
    b = hex_identifier_to_bytes(s)
    if not n or len(n) % 2:
        assert b is None
        return
    assert b is not None
    assert isinstance(b, bytes)
    assert len(b) == len(n) // 2
    assert b.hex() == n


@given(h=st.from_regex(r"[0-9a-fA-F]{0,200}"))
def test_hex_identifier_length_invariant(h):
    n = normalize_hex_identifier(h)
    b = hex_identifier_to_bytes(h)
    if not n or len(n) % 2:
        assert b is None
    else:
        assert b is not None
        assert len(b) == len(n) // 2


@given(
    a=st.from_regex(r"[0-9a-fA-F]{2,64}"),
    b=st.from_regex(r"[0-9a-fA-F]{2,64}"),
)
def test_normalize_concat_equals_normalize_join(a, b):
    assert normalize_hex_identifier(a + b) == normalize_hex_identifier(
        normalize_hex_identifier(a) + normalize_hex_identifier(b),
    )
