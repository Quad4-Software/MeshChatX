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
