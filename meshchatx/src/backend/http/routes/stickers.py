# SPDX-License-Identifier: 0BSD
"""HTTP routes: stickers."""

from __future__ import annotations

import base64
import json
from datetime import (
    UTC,
    datetime,
)

from aiohttp import web

from meshchatx.src.backend import sticker_pack_utils
from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_conflict,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)
from meshchatx.src.backend.sticker_utils import (
    MAX_STICKER_BYTES,
    MAX_STICKERS_PER_PACK,
    build_export_document,
    mime_for_image_type,
    sanitize_sticker_emoji,
    sanitize_sticker_name,
    validate_export_document,
)

_STICKER_DOC_MAX_BYTES = MAX_STICKER_BYTES * MAX_STICKERS_PER_PACK * 2


def register_stickers_routes(routes, app):

    @routes.get(API_V1_PREFIX + "/stickers")
    async def stickers_list(request):
        identity_hash = app.identity.hash.hex()
        rows = app.database.stickers.list_for_identity(identity_hash)
        return web.json_response({"stickers": [dict(r) for r in rows]})

    @routes.post(API_V1_PREFIX + "/stickers")
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

    @routes.delete(API_V1_PREFIX + "/stickers/{sticker_id}")
    async def stickers_delete(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = int(request.match_info.get("sticker_id", "0"))
        ok = app.database.stickers.delete(sticker_id, identity_hash)
        if not ok:
            return http_not_found("not_found")
        return web.json_response({"message": "deleted"})

    @routes.patch(API_V1_PREFIX + "/stickers/{sticker_id}")
    async def stickers_patch(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = int(request.match_info.get("sticker_id", "0"))
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

    @routes.get(API_V1_PREFIX + "/stickers/{sticker_id}/image")
    async def stickers_get_image(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = int(request.match_info.get("sticker_id", "0"))
        row = app.database.stickers.get_row(sticker_id, identity_hash)
        if row is None:
            return http_not_found("not_found")
        ct = mime_for_image_type(row["image_type"])
        return web.Response(body=row["image_blob"], content_type=ct)

    @routes.get(API_V1_PREFIX + "/stickers/export")
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

    @routes.post(API_V1_PREFIX + "/stickers/import")
    async def stickers_import(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await read_json_limited(request, _STICKER_DOC_MAX_BYTES)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        replace = bool(data.get("replace_duplicates", False))
        try:
            items = validate_export_document(data)
        except ValueError as e:
            return http_bad_request(str(e))
        result = app.database.stickers.import_payloads(
            identity_hash,
            items,
            replace_duplicates=replace,
        )
        return web.json_response(result)

    @routes.get(API_V1_PREFIX + "/sticker-packs")
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

    @routes.post(API_V1_PREFIX + "/sticker-packs")
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

    @routes.get(API_V1_PREFIX + "/sticker-packs/{pack_id}")
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

    @routes.patch(API_V1_PREFIX + "/sticker-packs/{pack_id}")
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

    @routes.post(API_V1_PREFIX + "/sticker-packs/reorder")
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

    @routes.delete(API_V1_PREFIX + "/sticker-packs/{pack_id}")
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

    @routes.get(API_V1_PREFIX + "/sticker-packs/{pack_id}/export")
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

    @routes.post(API_V1_PREFIX + "/sticker-packs/install")
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
