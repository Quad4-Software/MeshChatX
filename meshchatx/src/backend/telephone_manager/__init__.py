# SPDX-License-Identifier: 0BSD
"""Telephone manager public API."""

from __future__ import annotations

# ruff: noqa: F403
from meshchatx.src.backend.telephone_manager.core import *
from meshchatx.src.backend.telephone_manager import core as _core


def __getattr__(name: str):
    return getattr(_core, name)
