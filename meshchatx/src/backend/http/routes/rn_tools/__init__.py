# SPDX-License-Identifier: 0BSD
"""HTTP routes: rn_tools (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.rn_tools.rnsh import (
    register_rn_tools_rnsh_routes,
)
from meshchatx.src.backend.http.routes.rn_tools.rnx import register_rn_tools_rnx_routes
from meshchatx.src.backend.http.routes.rn_tools.rncp import (
    register_rn_tools_rncp_routes,
)
from meshchatx.src.backend.http.routes.rn_tools.rnstatus import (
    register_rn_tools_rnstatus_routes,
)
from meshchatx.src.backend.http.routes.rn_tools.rnpath import (
    register_rn_tools_rnpath_routes,
)
from meshchatx.src.backend.http.routes.rn_tools.rnprobe import (
    register_rn_tools_rnprobe_routes,
)


def register_rn_tools_routes(routes: Any, app: Any) -> None:
    register_rn_tools_rnsh_routes(routes, app)
    register_rn_tools_rnx_routes(routes, app)
    register_rn_tools_rncp_routes(routes, app)
    register_rn_tools_rnstatus_routes(routes, app)
    register_rn_tools_rnpath_routes(routes, app)
    register_rn_tools_rnprobe_routes(routes, app)
