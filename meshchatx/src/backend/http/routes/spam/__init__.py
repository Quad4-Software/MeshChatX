# SPDX-License-Identifier: 0BSD
"""HTTP routes: spam (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.spam.spam import (
    register_spam_spam_routes,
)


def register_spam_routes(routes: Any, app: Any) -> None:
    register_spam_spam_routes(routes, app)
