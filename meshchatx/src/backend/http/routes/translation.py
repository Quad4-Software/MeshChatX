# SPDX-License-Identifier: 0BSD
"""HTTP routes for local offline translation packs."""

from __future__ import annotations

import os
import shutil

import aiohttp
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
from meshchatx.src.backend.http.safe_file_response import file_response
from meshchatx.src.backend.http.uploads import (
    UPLOAD_LIMITS,
    PayloadTooLargeError,
    write_field_to_path,
)
from meshchatx.src.backend.privacy_mode import ensure_outbound_http_allowed
from meshchatx.src.backend.translation_catalog import (
    download_pair_files,
    fetch_catalog,
    staging_dir,
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

    @routes.get(API_V1_PREFIX + "/translation/catalog")
    async def list_translation_catalog(request):
        if not app.translation_pack_manager:
            return http_unavailable("Translation pack manager not available")
        try:
            ensure_outbound_http_allowed(
                app.config, feature="translation pack downloads"
            )
            pairs = await fetch_catalog(aiohttp.ClientTimeout(total=60, sock_read=30))
            return web.json_response(
                {"pairs": sorted(pairs.values(), key=lambda p: p["pair"])}
            )
        except Exception as e:
            RNS.log(f"Error fetching translation catalog: {e}", RNS.LOG_ERROR)
            return http_error_from_exception(e, fallback_status=502)

    @routes.post(API_V1_PREFIX + "/translation/packs/fetch")
    async def fetch_translation_pack(request):
        if not app.translation_pack_manager:
            return http_unavailable("Translation pack manager not available")
        try:
            ensure_outbound_http_allowed(
                app.config, feature="translation pack downloads"
            )
            data = await request.json()
            want_all = bool(data.get("all"))
            pair = str(data.get("pair") or "").lower()
            if not want_all and not pair:
                return http_bad_request("pair required")

            pairs = await fetch_catalog(aiohttp.ClientTimeout(total=60, sock_read=30))
            targets = sorted(pairs) if want_all else ([pair] if pair in pairs else None)
            if targets is None:
                return http_not_found("Pair not in catalog")

            installed = []
            failed = []
            for target in targets:
                tmp_dir = staging_dir(app.translation_pack_manager.incoming_dir)
                try:
                    await download_pair_files(
                        pairs[target],
                        tmp_dir,
                        aiohttp.ClientTimeout(total=None, sock_read=120),
                    )
                    app.translation_pack_manager.install_files_dir(
                        os.path.join(tmp_dir, target), target
                    )
                    installed.append(target)
                except Exception as e:
                    RNS.log(
                        f"Error fetching translation pack {target}: {e}",
                        RNS.LOG_ERROR,
                    )
                    failed.append({"pair": target, "error": str(e)})
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)

            status = 200 if installed and not failed else (207 if installed else 502)
            return web.json_response(
                {"installed": installed, "failed": failed}, status=status
            )
        except Exception as e:
            RNS.log(f"Error fetching translation packs: {e}", RNS.LOG_ERROR)
            return http_error_from_exception(e, fallback_status=502)

    @routes.get("/translation-packs/{path:.*}")
    async def serve_translation_pack_file(request):
        path = request.match_info.get("path", "")
        file_path = app.translation_pack_manager.safe_file_path(path)
        if not file_path or not os.path.isfile(file_path):
            return http_not_found("Not found")
        return file_response(file_path)
