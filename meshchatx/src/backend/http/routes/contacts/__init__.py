# SPDX-License-Identifier: 0BSD
"""HTTP routes: contacts (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.contacts.contacts import (
    register_contacts_contacts_routes,
)


def register_contacts_routes(routes: Any, app: Any) -> None:
    register_contacts_contacts_routes(routes, app)
