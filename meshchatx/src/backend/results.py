# SPDX-License-Identifier: 0BSD

"""Shared {"ok": bool, ...} result envelopes for backend managers.

Managers return these dicts to both HTTP routes and WS handlers. Keep
the shape identical everywhere so frontends can rely on ok/error.
"""

from __future__ import annotations


def ok_result(**fields) -> dict:
    return {"ok": True, **fields}


def err_result(message: str, **fields) -> dict:
    return {"ok": False, "error": message, **fields}


def err_result_from(exc: BaseException, fallback: str = "operation failed") -> dict:
    """Envelope for an exception without leaking internals to clients.

    ValueError-family messages pass through (user-facing by convention);
    OSError and unknown exceptions return the generic fallback so errno
    text and absolute paths stay server-side.
    """
    if isinstance(exc, ValueError):
        return err_result(str(exc))
    return err_result(fallback)
