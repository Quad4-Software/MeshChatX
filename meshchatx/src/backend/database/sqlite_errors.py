# SPDX-License-Identifier: 0BSD
"""Classify SQLite exceptions the UI can retry."""

from __future__ import annotations

_RETRYABLE_SNIPPETS = (
    "unable to open database file",
    "database is locked",
    "closed database",
    "cannot operate on a closed database",
    "disk i/o error",
)


def sqlite_error_is_retryable(exc: BaseException) -> bool:
    """True for locked, missing-file, and closed-handle SQLite failures."""
    detail = str(exc).lower()
    return any(snippet in detail for snippet in _RETRYABLE_SNIPPETS)
