# SPDX-License-Identifier: 0BSD
"""HTTP routes: messages (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.messages.destination import (
    register_messages_destination_routes,
)
from meshchatx.src.backend.http.routes.messages.notifications import (
    register_messages_notifications_routes,
)


def register_messages_routes(routes: Any, app: Any) -> None:
    register_messages_destination_routes(routes, app)
    register_messages_notifications_routes(routes, app)
