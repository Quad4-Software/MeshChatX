# SPDX-License-Identifier: 0BSD

"""Public demo mode: read-only mesh and default-deny HTTP mutations."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from aiohttp import web

from meshchatx.src.env_utils import env_bool

if TYPE_CHECKING:
    from meshchatx.meshchat import ReticulumMeshChat

DEMO_READONLY_CODE = "demo_readonly"

DEMO_HTTP_MUTATION_ALLOWLIST: frozenset[str] = frozenset(
    {
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/setup",
        "/api/v1/app/tutorial/seen",
        "/api/v1/app/changelog/seen",
    },
)


def demo_mode_from_env() -> bool:
    return env_bool("MESHCHAT_DEMO_MODE", False)


def auth_bypass_from_env() -> bool:
    return env_bool("MESHCHAT_AUTH_BYPASS", False)


def demo_auth_password_from_env() -> str:
    return os.environ.get("MESHCHAT_DEMO_AUTH_PASSWORD", "demo")


def normalize_api_path(path: str) -> str:
    if not path.startswith("/api/"):
        return path
    parts = [p for p in path.split("/") if p]
    return "/" + "/".join(parts)


def demo_mode_active(app: ReticulumMeshChat) -> bool:
    return bool(getattr(app, "demo_mode", False))


def demo_mode_blocks_ws_type(app: ReticulumMeshChat, msg_type: str) -> bool:
    if not demo_mode_active(app):
        return False
    from meshchatx.src.backend.websocket_config_guard import WEBSOCKET_MUTATOR_TYPES

    return msg_type in WEBSOCKET_MUTATOR_TYPES


def demo_mode_block_response(app: ReticulumMeshChat) -> web.Response | None:
    if not demo_mode_active(app):
        return None
    return web.json_response(
        {
            "error": "Demo mode is read-only",
            "code": DEMO_READONLY_CODE,
        },
        status=403,
    )


def demo_http_mutation_allowed(method: str, path: str) -> bool:
    if method.upper() in ("GET", "HEAD", "OPTIONS"):
        return True
    if method.upper() not in ("POST", "PUT", "PATCH", "DELETE"):
        return True
    normalized = normalize_api_path(path)
    if not normalized.startswith("/api/v1/"):
        return True
    return normalized in DEMO_HTTP_MUTATION_ALLOWLIST


def create_demo_mode_middleware(app: ReticulumMeshChat):
    @web.middleware
    async def demo_mode_middleware(request, handler):
        if demo_mode_active(app) and not demo_http_mutation_allowed(
            request.method,
            request.path,
        ):
            return web.json_response(
                {
                    "error": "Demo mode is read-only",
                    "code": DEMO_READONLY_CODE,
                },
                status=403,
            )
        return await handler(request)

    return demo_mode_middleware
