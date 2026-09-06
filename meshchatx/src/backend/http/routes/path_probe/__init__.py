# SPDX-License-Identifier: 0BSD
"""HTTP routes: path_probe (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.path_probe.destination import (
    register_path_probe_destination_routes,
)
from meshchatx.src.backend.http.routes.path_probe.ping import (
    register_path_probe_ping_routes,
)
from meshchatx.src.backend.http.routes.path_probe.path_table import (
    register_path_probe_path_table_routes,
)
from meshchatx.src.backend.http.routes.path_probe._names import (
    PATH_WAIT_REQUIRES_POST_MESSAGE as PATH_WAIT_REQUIRES_POST_MESSAGE,
    lxmf_delivery_hash_bytes_for_path as lxmf_delivery_hash_bytes_for_path,
)


def register_path_probe_routes(routes: Any, app: Any) -> None:
    register_path_probe_destination_routes(routes, app)
    register_path_probe_ping_routes(routes, app)
    register_path_probe_path_table_routes(routes, app)
