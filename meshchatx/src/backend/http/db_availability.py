# SPDX-License-Identifier: 0BSD

"""Helpers for DB-backed HTTP reads during identity switch and SQLite races."""

from __future__ import annotations

from meshchatx.src.backend.database.sqlite_errors import sqlite_error_is_retryable
from meshchatx.src.backend.http.errors import http_unavailable, http_unexpected

DB_TEMPORARILY_UNAVAILABLE = "Database temporarily unavailable. Retry shortly."


def require_database(app):
    """Return a 503 response when identity DB is not mounted, else None."""
    if getattr(app, "database", None) is None:
        return http_unavailable(DB_TEMPORARILY_UNAVAILABLE)
    return None


def http_for_database_exception(exc, *, unexpected_message="Internal error"):
    """Map retryable SQLite failures to 503 and other failures to 500."""
    if sqlite_error_is_retryable(exc):
        return http_unavailable(DB_TEMPORARILY_UNAVAILABLE)
    return http_unexpected(unexpected_message)


def exception_looks_like_missing_database(exc: BaseException, app) -> bool:
    """True when a route touched app.database while it was None mid-switch."""
    if getattr(app, "database", None) is not None:
        return False
    if not isinstance(exc, AttributeError):
        return False
    detail = str(exc).lower()
    return "nonetype" in detail and "attribute" in detail
