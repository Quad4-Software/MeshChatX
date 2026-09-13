# SPDX-License-Identifier: 0BSD
"""HTTP routes: interfaces (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.interfaces.crud import (
    register_interfaces_crud_routes,
)
from meshchatx.src.backend.http.routes.interfaces.modules import (
    register_interfaces_modules_routes,
)
from meshchatx.src.backend.http.routes.interfaces.add import (
    register_interfaces_add_routes,
)
from meshchatx.src.backend.http.routes.interfaces.import_export import (
    register_interfaces_import_export_routes,
)


def register_interfaces_routes(routes: Any, app: Any) -> None:
    register_interfaces_crud_routes(routes, app)
    register_interfaces_modules_routes(routes, app)
    register_interfaces_add_routes(routes, app)
    register_interfaces_import_export_routes(routes, app)
