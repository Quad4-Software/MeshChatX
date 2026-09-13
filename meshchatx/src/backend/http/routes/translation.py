# SPDX-License-Identifier: 0BSD
"""HTTP routes for local offline translation packs."""

from __future__ import annotations

import os

import RNS
from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_not_found,
    http_payload_too_large,
    http_unavailable,
)
from meshchatx.src.backend.http.uploads import (
    UPLOAD_LIMITS,
    PayloadTooLargeError,
    write_field_to_path,
)
from meshchatx.src.path_utils import safe_path_under_dir


def register_translation_routes(routes, app) -> None:
    """Register pack import, listing, removal, and file-serving routes."""

    @routes.get(API_V1_PREFIX + "/translation/packs")
    async def list_translation_packs(request):
        try:
            packs = app.translation_pack_manager.list_installed()
            return web.json_response({"packs": packs})
        except Exception as e:
            RNS.log(f"Error listing translation packs: {e}", RNS.LOG_ERROR)
            return http_error_from_exception(e, fallback_status=500)

    @routes.post(API_V1_PREFIX + "/translation/packs/import")
    async def import_translation_pack(request):
        if not app.translation_pack_manager:
            return http_unavailable("Translation pack manager not available")

        try:
            reader = await request.multipart()
            field = await reader.next()
            if field is None or field.name != "file":
                return http_bad_request("No file field")

            filename = os.path.basename(field.filename or "")
            incoming_dir = app.translation_pack_manager.incoming_dir
            os.makedirs(incoming_dir, exist_ok=True)
            archive_path = os.path.join(incoming_dir, filename)
            if not safe_path_under_dir(incoming_dir, archive_path):
                return http_bad_request("Invalid filename")

            await write_field_to_path(
                field,
                archive_path,
                UPLOAD_LIMITS["translation_pack"],
            )

            pairs = app.translation_pack_manager.import_archive(archive_path)
            return web.json_response({"pairs": pairs})
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception as e:
            RNS.log(f"Error importing translation pack: {e}", RNS.LOG_ERROR)
            return http_error_from_exception(e)

    @routes.delete(API_V1_PREFIX + "/translation/packs/{pair}")
    async def remove_translation_pack(request):
        pair = request.match_info.get("pair", "").lower()
        if not pair:
            return http_bad_request("Missing pair")
        try:
            ok = app.translation_pack_manager.remove_pack(pair)
            if not ok:
                return http_not_found("Pack not found")
            return web.json_response({"removed": pair})
        except Exception as e:
            RNS.log(f"Error removing translation pack: {e}", RNS.LOG_ERROR)
            return http_error_from_exception(e, fallback_status=500)

    @routes.get("/translation-packs/{path:.*}")
    async def serve_translation_pack_file(request):
        path = request.match_info.get("path", "")
        file_path = app.translation_pack_manager.safe_file_path(path)
        if not file_path or not os.path.isfile(file_path):
            return http_not_found("Not found")
        return web.FileResponse(file_path)
