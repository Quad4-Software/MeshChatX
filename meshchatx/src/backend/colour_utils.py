# SPDX-License-Identifier: 0BSD

"""Helpers for converting CSS-style hex colours to raw bytes."""

from __future__ import annotations


class ColourUtils:
    """Static helpers for colour string conversion."""

    @staticmethod
    def hex_colour_to_byte_array(hex_colour: str) -> bytes:
        """Parse a hex colour string (optional leading #) into bytes."""
        text = (hex_colour or "").strip()
        if text.startswith("#"):
            text = text[1:]
        return bytes.fromhex(text)
