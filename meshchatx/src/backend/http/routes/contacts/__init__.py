# SPDX-License-Identifier: 0BSD
"""HTTP routes: contacts (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.contacts.contacts import (
    CONTACTS_MAX_LIMIT as CONTACTS_MAX_LIMIT,
    enrich_contact_row as enrich_contact_row,
    parse_contacts_pagination as parse_contacts_pagination,
    register_contacts_contacts_routes,
)


def register_contacts_routes(routes: Any, app: Any) -> None:
    register_contacts_contacts_routes(routes, app)
