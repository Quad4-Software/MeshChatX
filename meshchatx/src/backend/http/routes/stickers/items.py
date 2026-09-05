# SPDX-License-Identifier: 0BSD
"""HTTP routes: individual stickers CRUD."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.stickers._names import *  # noqa: F403


def register_stickers_items_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/stickers")
    async def stickers_list(request):
        identity_hash = app.identity.hash.hex()
        rows = app.database.stickers.list_for_identity(identity_hash)
        return web.json_response({"stickers": [dict(r) for r in rows]})

    @routes.post("/api/v1/stickers")
    async def stickers_create(request):
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
        name = sanitize_sticker_name(data.get("name"))
        image_type = data.get("image_type")
        src = data.get("source_message_hash")
        src = src if isinstance(src, str) else None
        emoji = sanitize_sticker_emoji(data.get("emoji"))
        strict = bool(data.get("strict", False))
        pack_id_raw = data.get("pack_id")
        pack_id = None
        if pack_id_raw is not None:
            try:
                pack_id = int(pack_id_raw)
            except (TypeError, ValueError):
                return web.json_response({"error": "invalid_pack_id"}, status=400)
            pack_row = app.database.sticker_packs.get_row(pack_id, identity_hash)
            if pack_row is None:
                return web.json_response({"error": "pack_not_found"}, status=404)
        try:
            row = app.database.stickers.insert(
                identity_hash,
                name,
                image_type,
                raw,
                src,
                pack_id=pack_id,
                emoji=emoji,
                strict=strict,
            )
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        if row is None:
            return web.json_response({"error": "duplicate_sticker"}, status=409)
        return web.json_response({"sticker": row})

    @routes.delete("/api/v1/stickers/{sticker_id}")
    async def stickers_delete(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = int(request.match_info.get("sticker_id", "0"))
        ok = app.database.stickers.delete(sticker_id, identity_hash)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"message": "deleted"})

    @routes.patch("/api/v1/stickers/{sticker_id}")
    async def stickers_patch(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = int(request.match_info.get("sticker_id", "0"))
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        applied = False
        if "name" in data:
            name = sanitize_sticker_name(data.get("name"))
            if not app.database.stickers.update_name(
                sticker_id,
                identity_hash,
                name,
            ):
                return web.json_response({"error": "not_found"}, status=404)
            applied = True
        if "emoji" in data:
            emoji = sanitize_sticker_emoji(data.get("emoji"))
            if not app.database.stickers.update_emoji(
                sticker_id,
                identity_hash,
                emoji,
            ):
                return web.json_response({"error": "not_found"}, status=404)
            applied = True
        if "pack_id" in data:
            pid_raw = data.get("pack_id")
            pid = None
            if pid_raw is not None:
                try:
                    pid = int(pid_raw)
                except (TypeError, ValueError):
                    return web.json_response(
                        {"error": "invalid_pack_id"},
                        status=400,
                    )
                if app.database.sticker_packs.get_row(pid, identity_hash) is None:
                    return web.json_response(
                        {"error": "pack_not_found"},
                        status=404,
                    )
            if not app.database.stickers.assign_to_pack(
                sticker_id,
                identity_hash,
                pid,
            ):
                return web.json_response({"error": "not_found"}, status=404)
            applied = True
        if not applied:
            return web.json_response({"error": "nothing_to_update"}, status=400)
        return web.json_response({"message": "updated"})

    @routes.get("/api/v1/stickers/{sticker_id}/image")
    async def stickers_get_image(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = int(request.match_info.get("sticker_id", "0"))
        row = app.database.stickers.get_row(sticker_id, identity_hash)
        if row is None:
            return web.json_response({"error": "not_found"}, status=404)
        ct = mime_for_image_type(row["image_type"])
        return web.Response(body=row["image_blob"], content_type=ct)
