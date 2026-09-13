# SPDX-License-Identifier: 0BSD
"""HTTP routes: lxmf (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.lxmf.propagation import (
    register_lxmf_propagation_routes,
)
from meshchatx.src.backend.http.routes.lxmf.messages import (
    register_lxmf_messages_routes,
)
from meshchatx.src.backend.http.routes.lxmf.conversations import (
    register_lxmf_conversations_routes,
)
from meshchatx.src.backend.http.routes.lxmf.folders import register_lxmf_folders_routes


def register_lxmf_routes(routes: Any, app: Any) -> None:
    register_lxmf_propagation_routes(routes, app)
    register_lxmf_messages_routes(routes, app)
    register_lxmf_conversations_routes(routes, app)
    register_lxmf_folders_routes(routes, app)
