# SPDX-License-Identifier: 0BSD
"""HTTP routes: archives (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.archives.opt_outs import (
    register_archives_opt_outs_routes,
)
from meshchatx.src.backend.http.routes.archives.pages import (
    register_archives_pages_routes,
)
from meshchatx.src.backend.http.routes.archives.recrawl import (
    register_archives_recrawl_routes,
)


def register_archives_routes(routes: Any, app: Any) -> None:
    register_archives_pages_routes(routes, app)
    register_archives_opt_outs_routes(routes, app)
    register_archives_recrawl_routes(routes, app)
