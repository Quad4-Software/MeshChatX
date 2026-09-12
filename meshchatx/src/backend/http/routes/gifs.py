# SPDX-License-Identifier: 0BSD
"""HTTP routes: gifs."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime

from aiohttp import web

from meshchatx.src.backend import gif_utils
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


def register_gifs_routes(routes, app):

    @routes.get(API_V1_PREFIX + "/gifs")
    async def gifs_list(request):
        identity_hash = app.identity.hash.hex()
        rows = app.database.gifs.list_for_identity(identity_hash)
        return web.json_response({"gifs": [dict(r) for r in rows]})

    @routes.post(API_V1_PREFIX + "/gifs")
    async def gifs_create(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await read_json_limited(request, gif_utils.MAX_GIF_BYTES * 2)
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
            return http_bad_request(str(e))
        if row is None:
            return http_conflict("duplicate_gif")
        return web.json_response({"gif": row})

    @routes.delete(API_V1_PREFIX + "/gifs/{gif_id}")
    async def gifs_delete(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        ok = app.database.gifs.delete(gif_id, identity_hash)
        if not ok:
            return http_not_found("not_found")
        return web.json_response({"message": "deleted"})

    @routes.patch(API_V1_PREFIX + "/gifs/{gif_id}")
    async def gifs_patch(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        try:
            data = await read_json_limited(request, gif_utils.MAX_GIF_BYTES * 2)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        if "name" not in data:
            return http_bad_request("missing_name")
        name = gif_utils.sanitize_gif_name(data.get("name"))
        ok = app.database.gifs.update_name(gif_id, identity_hash, name)
        if not ok:
            return http_not_found("not_found")
        return web.json_response({"message": "updated"})

    @routes.get(API_V1_PREFIX + "/gifs/{gif_id}/image")
    async def gifs_get_image(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        row = app.database.gifs.get_row(gif_id, identity_hash)
        if row is None:
            return http_not_found("not_found")
        ct = gif_utils.mime_for_image_type(row["image_type"])
        return web.Response(body=row["image_blob"], content_type=ct)

    @routes.post(API_V1_PREFIX + "/gifs/{gif_id}/use")
    async def gifs_record_usage(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        ok = app.database.gifs.record_usage(gif_id, identity_hash)
        if not ok:
            return http_not_found("not_found")
        return web.json_response({"message": "recorded"})

    @routes.get(API_V1_PREFIX + "/gifs/export")
    async def gifs_export(request):
        identity_hash = app.identity.hash.hex()
        payloads = app.database.gifs.export_payloads_for_identity(identity_hash)
        doc = gif_utils.build_export_document(
            payloads,
            datetime.now(UTC).isoformat(),
        )
        return web.json_response(doc)

    @routes.post(API_V1_PREFIX + "/gifs/import")
    async def gifs_import(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await read_json_limited(request, gif_utils.MAX_GIF_BYTES * 8)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        replace = bool(data.get("replace_duplicates", False))
        try:
            items = gif_utils.validate_export_document(data)
        except ValueError as e:
            return http_bad_request(str(e))
        result = app.database.gifs.import_payloads(
            identity_hash,
            items,
            replace_duplicates=replace,
        )
        return web.json_response(result)

    # get latest telemetry for all peers
