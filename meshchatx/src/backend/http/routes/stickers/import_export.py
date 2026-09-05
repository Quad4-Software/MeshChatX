# SPDX-License-Identifier: 0BSD
"""HTTP routes: stickers import and export."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.stickers._names import *  # noqa: F403


def register_stickers_import_export_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/stickers/export")
    async def stickers_export(request):
        identity_hash = app.identity.hash.hex()
        payloads = app.database.stickers.export_payloads_for_identity(
            identity_hash,
        )
        doc = build_export_document(
            payloads,
            datetime.now(UTC).isoformat(),
        )
        return web.json_response(doc)

    @routes.post("/api/v1/stickers/import")
    async def stickers_import(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        replace = bool(data.get("replace_duplicates", False))
        try:
            items = validate_export_document(data)
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        result = app.database.stickers.import_payloads(
            identity_hash,
            items,
            replace_duplicates=replace,
        )
        return web.json_response(result)
