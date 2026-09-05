# SPDX-License-Identifier: 0BSD
"""HTTP routes: reticulum_instance (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.reticulum_instance.discovery import (
    register_reticulum_instance_discovery_routes,
)
from meshchatx.src.backend.http.routes.reticulum_instance.transport import (
    register_reticulum_instance_transport_routes,
)
from meshchatx.src.backend.http.routes.reticulum_instance.instance import (
    register_reticulum_instance_instance_routes,
)
from meshchatx.src.backend.http.routes.reticulum_instance.config import (
    register_reticulum_instance_config_routes,
)


def register_reticulum_instance_routes(routes: Any, app: Any) -> None:
    register_reticulum_instance_discovery_routes(routes, app)
    register_reticulum_instance_transport_routes(routes, app)
    register_reticulum_instance_instance_routes(routes, app)
    register_reticulum_instance_config_routes(routes, app)
