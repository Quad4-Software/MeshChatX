# SPDX-License-Identifier: 0BSD

"""Validation for Material Design Icons names (kebab-case, LXMF-style)."""

import re

MDI_ICON_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_MDI_ICON_NAME_LEN = 64


def normalize_mdi_icon_name(value):
    """Return a normalized icon name or ``None`` when unset/invalid."""
    if value is None:
        return None
    if not isinstance(value, str):
        msg = "icon name must be a string"
        raise ValueError(msg)
    trimmed = value.strip().lower()
    if not trimmed:
        return None
    if len(trimmed) > MAX_MDI_ICON_NAME_LEN or not MDI_ICON_NAME_RE.match(trimmed):
        msg = "invalid MDI icon name"
        raise ValueError(msg)
    return trimmed
