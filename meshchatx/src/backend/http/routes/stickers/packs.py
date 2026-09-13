# SPDX-License-Identifier: 0BSD
"""HTTP routes: sticker packs management."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.stickers._names import *  # noqa: F403
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)



def register_stickers_packs_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/sticker-packs")
    async def sticker_packs_list(request):
        identity_hash = app.identity.hash.hex()
        packs = [
            dict(p)
            for p in app.database.sticker_packs.list_for_identity(
                identity_hash,
            )
        ]
        for p in packs:
            p["sticker_count"] = app.database.stickers.count_for_pack(
                p["id"],
                identity_hash,
            )
            stickers = app.database.stickers.list_for_pack(
                p["id"],
                identity_hash,
            )
            p["stickers"] = [dict(s) for s in stickers]
        return web.json_response({"packs": packs})

    @routes.post("/api/v1/sticker-packs")
    async def sticker_packs_create(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        try:
            pack = app.database.sticker_packs.insert(
                identity_hash,
                data.get("title"),
                short_name=data.get("short_name"),
                description=data.get("description"),
                pack_type=data.get("pack_type"),
                author=data.get("author"),
                is_strict=bool(data.get("is_strict", True)),
            )
        except ValueError as e:
            return http_bad_request(str(e))
        return web.json_response({"pack": pack})

    @routes.get("/api/v1/sticker-packs/{pack_id}")
    async def sticker_packs_get(request):
        identity_hash = app.identity.hash.hex()
        try:
            pack_id = int(request.match_info.get("pack_id", "0"))
        except ValueError:
            return http_bad_request("invalid_pack_id")
        row = app.database.sticker_packs.get_row(pack_id, identity_hash)
        if row is None:
            return http_not_found("not_found")
        stickers = app.database.stickers.list_for_pack(pack_id, identity_hash)
        return web.json_response(
            {
                "pack": dict(row),
                "stickers": [dict(s) for s in stickers],
            },
        )

    @routes.patch("/api/v1/sticker-packs/{pack_id}")
    async def sticker_packs_patch(request):
        identity_hash = app.identity.hash.hex()
        try:
            pack_id = int(request.match_info.get("pack_id", "0"))
        except ValueError:
            return http_bad_request("invalid_pack_id")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        kwargs = {}
        for key in ("title", "description", "pack_type"):
            if key in data:
                kwargs[key] = data.get(key)
        if "cover_sticker_id" in data:
            v = data.get("cover_sticker_id")
            kwargs["cover_sticker_id"] = int(v) if v is not None else None
        if not kwargs:
            return http_bad_request("nothing_to_update")
        ok = app.database.sticker_packs.update(
            pack_id,
            identity_hash,
            **kwargs,
        )
        if not ok:
            return http_not_found("not_found")
        return web.json_response({"message": "updated"})

    @routes.post("/api/v1/sticker-packs/reorder")
    async def sticker_packs_reorder(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        ids = data.get("pack_ids")
        if not isinstance(ids, list):
            return http_bad_request("missing_pack_ids")
        try:
            ids_int = [int(x) for x in ids]
        except (TypeError, ValueError):
            return http_bad_request("invalid_pack_ids")
        updated = app.database.sticker_packs.reorder(identity_hash, ids_int)
        return web.json_response({"updated": updated})

    @routes.delete("/api/v1/sticker-packs/{pack_id}")
    async def sticker_packs_delete(request):
        identity_hash = app.identity.hash.hex()
        try:
            pack_id = int(request.match_info.get("pack_id", "0"))
        except ValueError:
            return http_bad_request("invalid_pack_id")
        with_stickers = request.query.get("with_stickers", "false").lower() == "true"
        if with_stickers:
            ok = app.database.sticker_packs.delete_with_stickers(
                pack_id,
                identity_hash,
            )
        else:
            ok = app.database.sticker_packs.delete(pack_id, identity_hash)
        if not ok:
            return http_not_found("not_found")
        return web.json_response({"message": "deleted"})

    @routes.get("/api/v1/sticker-packs/{pack_id}/export")
    async def sticker_packs_export(request):
        identity_hash = app.identity.hash.hex()
        try:
            pack_id = int(request.match_info.get("pack_id", "0"))
        except ValueError:
            return http_bad_request("invalid_pack_id")
        row = app.database.sticker_packs.get_row(pack_id, identity_hash)
        if row is None:
            return http_not_found("not_found")
        stickers = app.database.stickers.export_payloads_for_pack(
            pack_id,
            identity_hash,
        )
        doc = sticker_pack_utils.build_pack_document(
            dict(row),
            stickers,
            datetime.now(UTC).isoformat(),
        )
        return web.json_response(doc)

    @routes.post("/api/v1/sticker-packs/install")
    async def sticker_packs_install(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await read_json_limited(request, _STICKER_DOC_MAX_BYTES)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        replace = bool(data.get("replace_duplicates", False))
        try:
            parsed = sticker_pack_utils.validate_pack_document(data)
        except ValueError as e:
            return http_bad_request(str(e))
        try:
            pack_row = app.database.sticker_packs.insert(
                identity_hash,
                parsed["pack"]["title"],
                short_name=parsed["pack"]["short_name"],
                description=parsed["pack"]["description"],
                pack_type=parsed["pack"]["pack_type"],
                author=parsed["pack"]["author"],
                is_strict=parsed["pack"]["is_strict"],
            )
        except ValueError as e:
            return http_bad_request(str(e))
        result = app.database.stickers.import_payloads(
            identity_hash,
            parsed["stickers"],
            replace_duplicates=replace,
            pack_id=pack_row["id"],
            strict=parsed["pack"]["is_strict"],
        )
        return web.json_response({"pack": pack_row, **result})
