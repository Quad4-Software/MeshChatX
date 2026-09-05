# SPDX-License-Identifier: 0BSD
"""HTTP routes: server security settings."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.auth._names import *  # noqa: F403


def register_auth_security_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/server/security")
    async def server_security_get(request):
        settings = load_app_security_settings(app.storage_dir)
        return web.json_response(
            {
                "listen_host": app.listen_host,
                "listen_port": app.listen_port,
                "https_enabled": app.use_https,
                "is_loopback_bind": _is_loopback_bind_host(app.listen_host),
                "web_ui_ip_allowlist": settings.get("web_ui_ip_allowlist", ""),
                "trusted_proxy_cidrs": settings.get("trusted_proxy_cidrs", ""),
                **app._landlock_status_dict(),
                "privacy_mode_enabled": privacy_mode_enabled(app.config),
                "auth_enabled": app.auth_enabled,
            },
        )

    @routes.patch("/api/v1/server/security")
    async def server_security_patch(request):
        try:
            data = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return web.json_response({"error": "Invalid JSON body"}, status=400)
        if not isinstance(data, dict):
            return web.json_response({"error": "Invalid request body"}, status=400)
        try:
            updates = {}
            if "web_ui_ip_allowlist" in data:
                updates["web_ui_ip_allowlist"] = data.get("web_ui_ip_allowlist")
            if "trusted_proxy_cidrs" in data:
                updates["trusted_proxy_cidrs"] = data.get("trusted_proxy_cidrs")
            if updates:
                settings = save_app_security_settings(app.storage_dir, updates)
            else:
                settings = load_app_security_settings(app.storage_dir)
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        return web.json_response(
            {
                "listen_host": app.listen_host,
                "listen_port": app.listen_port,
                "https_enabled": app.use_https,
                "is_loopback_bind": _is_loopback_bind_host(app.listen_host),
                "web_ui_ip_allowlist": settings.get("web_ui_ip_allowlist", ""),
                "trusted_proxy_cidrs": settings.get("trusted_proxy_cidrs", ""),
                **app._landlock_status_dict(),
                "privacy_mode_enabled": privacy_mode_enabled(app.config),
                "auth_enabled": app.auth_enabled,
            },
        )
