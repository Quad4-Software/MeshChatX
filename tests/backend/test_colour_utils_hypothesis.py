# SPDX-License-Identifier: 0BSD

"""Property tests for hex colour parsing."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.colour_utils import ColourUtils


@settings(max_examples=200, deadline=None)
@given(t=st.text(max_size=200))
def test_hex_colour_only_value_error_or_returns_bytes(t):
    try:
        out = ColourUtils.hex_colour_to_byte_array(t)
    except ValueError:
        return
    except Exception as e:
        raise AssertionError(f"unexpected exception: {type(e).__name__}: {e}") from e

    assert isinstance(out, bytes)


@settings(max_examples=150, deadline=None)
@given(
    h=st.from_regex(r"[0-9a-fA-F]{2,64}", fullmatch=True).filter(
        lambda x: len(x) % 2 == 0
    )
)
def test_hex_colour_even_length_hex_round_trip(h):
    out = ColourUtils.hex_colour_to_byte_array(h)
    out_hash = ColourUtils.hex_colour_to_byte_array("#" + h)
    assert out == out_hash
    assert len(out) == len(h) // 2


@settings(max_examples=80, deadline=None)
@given(
    h=st.from_regex(r"[0-9a-fA-F]{1,63}", fullmatch=True).filter(
        lambda x: len(x) % 2 == 1
    )
)
def test_hex_colour_odd_length_raises(h):
    with pytest.raises(ValueError):
        ColourUtils.hex_colour_to_byte_array(h)
