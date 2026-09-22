# SPDX-License-Identifier: 0BSD
"""HTTP routes: individual stickers CRUD."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_conflict,
    http_not_found,
    http_payload_too_large,
    parse_int_param,
)

# ruff: noqa: F403, F405
from meshchatx.src.backend.http.routes.stickers._names import *
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


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
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        image_b64 = data.get("image_bytes")
        if not isinstance(image_b64, str) or not image_b64.strip():
            return http_bad_request("missing_image_bytes")
        try:
            raw = base64.b64decode(image_b64.strip(), validate=True)
        except (ValueError, TypeError):
            return http_bad_request("invalid_base64")
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
                return http_bad_request("invalid_pack_id")
            pack_row = app.database.sticker_packs.get_row(pack_id, identity_hash)
            if pack_row is None:
                return http_not_found("pack_not_found")
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
            return http_bad_request(str(e))
        if row is None:
            return http_conflict("duplicate_sticker")
        return web.json_response({"sticker": row})

    @routes.delete("/api/v1/stickers/{sticker_id}")
    async def stickers_delete(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = parse_int_param(request.match_info.get("sticker_id"))
        if sticker_id is None:
            return http_bad_request("invalid sticker id")
        ok = app.database.stickers.delete(sticker_id, identity_hash)
        if not ok:
            return http_not_found("not_found")
        return web.json_response({"message": "deleted"})

    @routes.patch("/api/v1/stickers/{sticker_id}")
    async def stickers_patch(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = parse_int_param(request.match_info.get("sticker_id"))
        if sticker_id is None:
            return http_bad_request("invalid sticker id")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        applied = False
        if "name" in data:
            name = sanitize_sticker_name(data.get("name"))
            if not app.database.stickers.update_name(
                sticker_id,
                identity_hash,
                name,
            ):
                return http_not_found("not_found")
            applied = True
        if "emoji" in data:
            emoji = sanitize_sticker_emoji(data.get("emoji"))
            if not app.database.stickers.update_emoji(
                sticker_id,
                identity_hash,
                emoji,
            ):
                return http_not_found("not_found")
            applied = True
        if "pack_id" in data:
            pid_raw = data.get("pack_id")
            pid = None
            if pid_raw is not None:
                try:
                    pid = int(pid_raw)
                except (TypeError, ValueError):
                    return http_bad_request("invalid_pack_id")
                if app.database.sticker_packs.get_row(pid, identity_hash) is None:
                    return http_not_found("pack_not_found")
            if not app.database.stickers.assign_to_pack(
                sticker_id,
                identity_hash,
                pid,
            ):
                return http_not_found("not_found")
            applied = True
        if not applied:
            return http_bad_request("nothing_to_update")
        return web.json_response({"message": "updated"})

    @routes.get("/api/v1/stickers/{sticker_id}/image")
    async def stickers_get_image(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = parse_int_param(request.match_info.get("sticker_id"))
        if sticker_id is None:
            return http_bad_request("invalid sticker id")
        row = app.database.stickers.get_row(sticker_id, identity_hash)
        if row is None:
            return http_not_found("not_found")
        ct = mime_for_image_type(row["image_type"])
        return web.Response(body=row["image_blob"], content_type=ct)
