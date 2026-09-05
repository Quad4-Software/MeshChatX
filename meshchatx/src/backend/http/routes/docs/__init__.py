# SPDX-License-Identifier: 0BSD
"""HTTP routes: docs (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.docs.docs import (
    register_docs_docs_routes,
)


def register_docs_routes(routes: Any, app: Any) -> None:
    register_docs_docs_routes(routes, app)
