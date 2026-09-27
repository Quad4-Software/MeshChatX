# SPDX-License-Identifier: 0BSD
"""Telephone manager public API."""

from __future__ import annotations

from meshchatx.src.backend.telephone_manager import core as _core

# ruff: noqa: F403
from meshchatx.src.backend.telephone_manager.core import *


def __getattr__(name: str):
    return getattr(_core, name)
