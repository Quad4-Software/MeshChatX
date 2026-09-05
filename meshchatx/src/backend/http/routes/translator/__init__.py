# SPDX-License-Identifier: 0BSD
"""HTTP routes: translator (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.translator.translator import (
    register_translator_translator_routes,
)


def register_translator_routes(routes: Any, app: Any) -> None:
    register_translator_translator_routes(routes, app)
