# SPDX-License-Identifier: 0BSD
"""HTTP routes: gifs/gifs."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.gifs._names import *  # noqa: F403


def register_gifs_gifs_routes(routes: Any, app: Any) -> None:

    @routes.get("/api/v1/gifs")
    async def gifs_list(request):
        identity_hash = app.identity.hash.hex()
        rows = app.database.gifs.list_for_identity(identity_hash)
        return web.json_response({"gifs": [dict(r) for r in rows]})

    @routes.post("/api/v1/gifs")
    async def gifs_create(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        image_b64 = data.get("image_bytes")
        if not isinstance(image_b64, str) or not image_b64.strip():
            return web.json_response({"error": "missing_image_bytes"}, status=400)
        try:
            raw = base64.b64decode(image_b64.strip(), validate=True)
        except (ValueError, TypeError):
            return web.json_response({"error": "invalid_base64"}, status=400)
        name = gif_utils.sanitize_gif_name(data.get("name"))
        image_type = data.get("image_type")
        src = data.get("source_message_hash")
        src = src if isinstance(src, str) else None
        try:
            row = app.database.gifs.insert(
                identity_hash,
                name,
                image_type,
                raw,
                src,
            )
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        if row is None:
            return web.json_response({"error": "duplicate_gif"}, status=409)
        return web.json_response({"gif": row})

    @routes.delete("/api/v1/gifs/{gif_id}")
    async def gifs_delete(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        ok = app.database.gifs.delete(gif_id, identity_hash)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"message": "deleted"})

    @routes.patch("/api/v1/gifs/{gif_id}")
    async def gifs_patch(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        if "name" not in data:
            return web.json_response({"error": "missing_name"}, status=400)
        name = gif_utils.sanitize_gif_name(data.get("name"))
        ok = app.database.gifs.update_name(gif_id, identity_hash, name)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"message": "updated"})

    @routes.get("/api/v1/gifs/{gif_id}/image")
    async def gifs_get_image(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        row = app.database.gifs.get_row(gif_id, identity_hash)
        if row is None:
            return web.json_response({"error": "not_found"}, status=404)
        ct = gif_utils.mime_for_image_type(row["image_type"])
        return web.Response(body=row["image_blob"], content_type=ct)

    @routes.post("/api/v1/gifs/{gif_id}/use")
    async def gifs_record_usage(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        ok = app.database.gifs.record_usage(gif_id, identity_hash)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"message": "recorded"})

    @routes.get("/api/v1/gifs/export")
    async def gifs_export(request):
        identity_hash = app.identity.hash.hex()
        payloads = app.database.gifs.export_payloads_for_identity(identity_hash)
        doc = gif_utils.build_export_document(
            payloads,
            datetime.now(UTC).isoformat(),
        )
        return web.json_response(doc)

    @routes.post("/api/v1/gifs/import")
    async def gifs_import(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        replace = bool(data.get("replace_duplicates", False))
        try:
            items = gif_utils.validate_export_document(data)
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        result = app.database.gifs.import_payloads(
            identity_hash,
            items,
            replace_duplicates=replace,
        )
        return web.json_response(result)
