# SPDX-License-Identifier: 0BSD
"""HTTP routes: blocklist/misc."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.blocklist._names import *  # noqa: F403


def register_blocklist_misc_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/lxmf/message-blocklist")
    async def lxmf_message_blocklist_get(request):
        raw = app.config.message_blocklist_json.get()
        return web.json_response(
            {
                "enabled": app.config.message_blocklist_enabled.get(),
                "blocklist": parse_message_blocklist_json(raw),
            },
        )

    @routes.put("/api/v1/lxmf/message-blocklist")
    async def lxmf_message_blocklist_put(request):
        data = await request.json()
        blocklist_in = data.get("blocklist")
        if not isinstance(blocklist_in, dict):
            return web.json_response(
                {"message": "blocklist must be an object"},
                status=400,
            )
        normalized = normalize_message_blocklist(blocklist_in)
        if "enabled" in data:
            app.config.message_blocklist_enabled.set(
                app._parse_bool(data["enabled"]),
            )
        app.config.message_blocklist_json.set(json.dumps(normalized))
        return web.json_response(
            {
                "enabled": app.config.message_blocklist_enabled.get(),
                "blocklist": normalized,
            },
        )

    @routes.get("/api/v1/lxmf/message-blocklist/export")
    async def lxmf_message_blocklist_export(request):
        raw = app.config.message_blocklist_json.get()
        blocklist = parse_message_blocklist_json(raw)
        return web.json_response(build_blocklist_export_document(blocklist))

    @routes.post("/api/v1/lxmf/message-blocklist/import")
    async def lxmf_message_blocklist_import(request):
        data = await request.json()
        document = data.get("document")
        if not isinstance(document, dict):
            return web.json_response(
                {"message": "document must be an object"},
                status=400,
            )
        merge = app._parse_bool(data.get("merge", False))
        existing = parse_message_blocklist_json(
            app.config.message_blocklist_json.get(),
        )
        imported = parse_import_document(
            document,
            merge=merge,
            existing=existing,
        )
        if imported is None:
            return web.json_response(
                {"message": "Invalid blocklist document"},
                status=400,
            )
        app.config.message_blocklist_json.set(json.dumps(imported))
        return web.json_response(
            {
                "enabled": app.config.message_blocklist_enabled.get(),
                "blocklist": imported,
            },
        )

    @routes.get("/api/v1/reticulum/blackhole")
    async def reticulum_blackhole_get(request):
        if not hasattr(app, "reticulum") or not app.reticulum:
            return web.json_response(
                {"error": "Reticulum not initialized"},
                status=503,
            )

        try:
            if hasattr(app.reticulum, "get_blackholed_identities"):
                identities = app.reticulum.get_blackholed_identities()
                # Convert bytes keys to hex strings
                formatted = {}
                for h, info in identities.items():
                    formatted[h.hex()] = {
                        "source": info.get("source", b"").hex()
                        if info.get("source")
                        else None,
                        "until": info.get("until"),
                        "reason": info.get("reason"),
                    }
                return web.json_response({"blackholed_identities": formatted})
            return web.json_response({"blackholed_identities": {}})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
