# SPDX-License-Identifier: 0BSD
"""HTTP routes: filesync (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.filesync.acl import (
    register_filesync_acl_routes,
)
from meshchatx.src.backend.http.routes.filesync.peers import (
    register_filesync_peers_routes,
)
from meshchatx.src.backend.http.routes.filesync.status import (
    register_filesync_status_routes,
)
from meshchatx.src.backend.http.routes.filesync.tree import (
    register_filesync_tree_routes,
)


def register_filesync_routes(routes: Any, app: Any) -> None:
    register_filesync_status_routes(routes, app)
    register_filesync_peers_routes(routes, app)
    register_filesync_tree_routes(routes, app)
    register_filesync_acl_routes(routes, app)
