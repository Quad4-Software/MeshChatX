# SPDX-License-Identifier: 0BSD

"""Register HTTP routes and build the standard middleware tuple."""

from __future__ import annotations

from meshchatx.src.backend.demo_mode import create_demo_mode_middleware
from meshchatx.src.backend.http.middleware import (
    create_auth_middleware,
    create_csrf_middleware,
    create_ip_allowlist_middleware,
    create_mime_type_middleware,
    create_security_middleware,
)
from meshchatx.src.backend.http.routes import register_extracted_routes


def register_all_routes(routes, app):
    """Register extracted route modules, then return middleware tuple.

    Call order of route modules is fixed in register_extracted_routes.
    Handlers still living in ReticulumMeshChat._define_routes are registered
    by the caller after this returns the middleware factories are created.
    """
    register_extracted_routes(routes, app)
    return (
        create_auth_middleware(app),
        create_mime_type_middleware(app),
        create_security_middleware(app),
        create_csrf_middleware(app),
        create_ip_allowlist_middleware(app),
        create_demo_mode_middleware(app),
    )
