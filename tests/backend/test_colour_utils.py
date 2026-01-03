import pytest
from meshchatx.src.backend.colour_utils import ColourUtils


def test_hex_colour_to_byte_array():
    # Test with # prefix
    hex_val = "#FF00AA"
    expected = bytes.fromhex("FF00AA")
    assert ColourUtils.hex_colour_to_byte_array(hex_val) == expected

    # Test without # prefix
    hex_val = "00BBFF"
    expected = bytes.fromhex("00BBFF")
    assert ColourUtils.hex_colour_to_byte_array(hex_val) == expected


def test_hex_colour_to_byte_array_invalid():
    # Test with invalid hex
    with pytest.raises(ValueError):
        ColourUtils.hex_colour_to_byte_array("#GG00AA")
