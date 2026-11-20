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


def require_announce_manager(app):
    """Return a 503 response when the announce manager is not mounted.

    IdentityContext mounts announce_manager after the database, so a DB
    guard alone lets requests through into None.get_filtered_announces
    during startup and identity switch.
    """
    if getattr(app, "announce_manager", None) is None:
        return http_unavailable(DB_TEMPORARILY_UNAVAILABLE)
    return None


def http_for_database_exception(exc, *, unexpected_message="Internal error"):
    """Map retryable SQLite failures to 503 and other failures to 500."""
    if sqlite_error_is_retryable(exc):
        return http_unavailable(DB_TEMPORARILY_UNAVAILABLE)
    return http_unexpected(unexpected_message)


def exception_looks_like_missing_database(exc: BaseException, app) -> bool:
    """True when a route touched an unmounted context object mid-switch.

    current_context is assigned before setup() finishes, so database,
    message_handler, and announce_manager each pass through a None window.
    An AttributeError raised while any of them is unmounted is a transient
    identity-switch race, not a handler bug, so it maps to 503 like a
    retryable SQLite error.
    """
    mounted = all(
        getattr(app, attr, None) is not None
        for attr in ("database", "message_handler", "announce_manager")
    )
    if mounted:
        return False
    if not isinstance(exc, AttributeError):
        return False
    detail = str(exc).lower()
    return "nonetype" in detail and "attribute" in detail
