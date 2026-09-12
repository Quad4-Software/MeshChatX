# SPDX-License-Identifier: 0BSD
"""HTTP routes: docs."""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    UPLOAD_LIMITS,
    PayloadTooLargeError,
    read_field_limited,
    read_json_limited,
)


def register_docs_routes(routes, app):

    # get docs status
    @routes.get(API_V1_PREFIX + "/docs/status")
    async def docs_status(request):
        return web.json_response(app.docs_manager.get_status())

    # upload docs zip

    # upload docs zip
    @routes.post(API_V1_PREFIX + "/docs/upload")
    async def docs_upload(request):
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field.name != "file":
                return http_bad_request(
                    "No file field in multipart request",
                )

            version = request.query.get("version")
            if not version:
                # use timestamp if no version provided
                version = f"upload-{int(time.time())}"

            zip_data = await read_field_limited(field, UPLOAD_LIMITS["docs_zip"])
            success = app.docs_manager.upload_zip(zip_data, version)
            return web.json_response({"success": success, "version": version})
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    # switch docs version

    # switch docs version
    @routes.post(API_V1_PREFIX + "/docs/switch")
    async def docs_switch(request):
        try:
            data = await read_json_limited(request)
            version = data.get("version")
            if not version:
                return http_bad_request("No version provided")

            success = app.docs_manager.switch_version(version)
            return web.json_response({"success": success})
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    # delete docs version

    # delete docs version
    @routes.delete(API_V1_PREFIX + "/docs/version/{version}")
    async def docs_delete_version(request):
        try:
            version = request.match_info.get("version")
            if not version:
                return http_bad_request("No version provided")

            success = app.docs_manager.delete_version(version)
            return web.json_response({"success": success})
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    # clear reticulum docs

    # clear reticulum docs
    @routes.delete(API_V1_PREFIX + "/maintenance/docs/reticulum")
    async def docs_clear(request):
        try:
            success = app.docs_manager.clear_reticulum_docs()
            return web.json_response({"success": success})
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    # search docs

    # search docs
    @routes.get(API_V1_PREFIX + "/docs/search")
    async def docs_search(request):
        query = request.query.get("q", "")
        lang = request.query.get("lang", "en")
        results = app.docs_manager.search(query, lang)
        return web.json_response({"results": results})

    # get meshchatx docs list

    # get meshchatx docs list
    @routes.get(API_V1_PREFIX + "/meshchatx-docs/list")
    async def meshchatx_docs_list(request):
        lang = request.query.get("lang", "en")
        return web.json_response(app.docs_manager.get_meshchatx_docs_list(lang))

    # get meshchatx doc content

    # get meshchatx doc content
    @routes.get(API_V1_PREFIX + "/meshchatx-docs/content")
    async def meshchatx_doc_content(request):
        path = request.query.get("path")
        if not path:
            return http_bad_request("No path provided")
        if not app.docs_manager._is_safe_doc_path(path):
            return http_bad_request("Invalid path")

        content = app.docs_manager.get_doc_content(path)
        if not content:
            return http_not_found("Document not found")

        return web.json_response(content)

    # repository server (wheels + uploads, and optional in-process plain HTTP)

    # export docs
    @routes.get(API_V1_PREFIX + "/docs/export")
    async def docs_export(request):
        try:
            zip_data = app.docs_manager.export_docs()
            filename = (
                f"meshchatx_docs_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.zip"
            )
            return web.Response(
                body=zip_data,
                content_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    # export the active Reticulum manual in a layout the upload route accepts,
    # so users can share their bundled or customised manual with another peer.

    # export the active Reticulum manual in a layout the upload route accepts,
    # so users can share their bundled or customised manual with another peer.
    @routes.get(API_V1_PREFIX + "/docs/export/reticulum")
    async def reticulum_docs_export(request):
        try:
            zip_data = app.docs_manager.export_reticulum_docs()
            if zip_data is None:
                return http_not_found(
                    "No Reticulum manual available to export",
                )
            version = app.docs_manager.get_current_version() or "manual"
            safe_version = re.sub(r"[^A-Za-z0-9._-]+", "_", str(version))
            filename = (
                "reticulum_manual_"
                f"{safe_version}_"
                f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.zip"
            )
            return web.Response(
                body=zip_data,
                content_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)
