# SPDX-License-Identifier: 0BSD
"""HTTP routes: blocklist (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.blocklist.blocklist import (
    register_blocklist_blocklist_routes,
)
from meshchatx.src.backend.http.routes.blocklist.misc import (
    register_blocklist_misc_routes,
)


def register_blocklist_routes(routes: Any, app: Any) -> None:
    register_blocklist_blocklist_routes(routes, app)
    register_blocklist_misc_routes(routes, app)
