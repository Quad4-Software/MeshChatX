# SPDX-License-Identifier: 0BSD

"""CSRF token helpers for cookie-authenticated API requests."""

from __future__ import annotations

import secrets

CSRF_HEADER = "X-CSRF-Token"
CSRF_SESSION_KEY = "csrf_token"


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def ensure_session_csrf_token(session) -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not token or not isinstance(token, str):
        token = new_csrf_token()
        session[CSRF_SESSION_KEY] = token
    return token


def rotate_session_csrf_token(session) -> str:
    token = new_csrf_token()
    session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_header(request, session) -> bool:
    expected = session.get(CSRF_SESSION_KEY)
    if not expected or not isinstance(expected, str):
        return False
    provided = request.headers.get(CSRF_HEADER, "")
    if not provided or not isinstance(provided, str):
        return False
    return secrets.compare_digest(provided.strip(), expected.strip())
