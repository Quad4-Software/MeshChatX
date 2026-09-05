# SPDX-License-Identifier: 0BSD
"""sticker_utils public API."""

from __future__ import annotations

# ruff: noqa: F401, F403, F405

from meshchatx.src.backend.sticker_utils.core import *  # noqa: F403

from meshchatx.src.backend.sticker_utils import core as _core

_read_png_dimensions = _core._read_png_dimensions
_read_webp_dimensions = _core._read_webp_dimensions
_read_gif_dimensions = _core._read_gif_dimensions
_read_bmp_dimensions = _core._read_bmp_dimensions
_read_jpeg_dimensions = _core._read_jpeg_dimensions
_decompress_gzip_bounded = _core._decompress_gzip_bounded
_ebml_read_vint = _core._ebml_read_vint
_ebml_iter_elements = _core._ebml_iter_elements
_ebml_read_uint = _core._ebml_read_uint
_ebml_read_float = _core._ebml_read_float
_validate_dimensions_telegram_static = _core._validate_dimensions_telegram_static
_validate_strict_payload = _core._validate_strict_payload
_LEGACY_TYPES = _core._LEGACY_TYPES
_TELEGRAM_STATIC_TYPES = _core._TELEGRAM_STATIC_TYPES
_ALLOWED_TYPES = _core._ALLOWED_TYPES
_TYPE_ALIASES = _core._TYPE_ALIASES
_GZIP_WBITS = _core._GZIP_WBITS
_EXPORT_FORMAT = _core._EXPORT_FORMAT
_EXPORT_VERSION = _core._EXPORT_VERSION
_EMOJI_MAX_LEN = _core._EMOJI_MAX_LEN
