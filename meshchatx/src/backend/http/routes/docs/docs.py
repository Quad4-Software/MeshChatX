# SPDX-License-Identifier: 0BSD
"""HTTP routes: docs/docs."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.docs._names import *  # noqa: F403


def register_docs_docs_routes(routes: Any, app: Any) -> None:

    # get docs status

    @routes.get("/api/v1/docs/status")
    async def docs_status(request):
        return web.json_response(app.docs_manager.get_status())

    @routes.post("/api/v1/docs/upload")
    async def docs_upload(request):
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field.name != "file":
                return web.json_response(
                    {"error": "No file field in multipart request"},
                    status=400,
                )

            version = request.query.get("version")
            if not version:
                # use timestamp if no version provided
                version = f"upload-{int(time.time())}"

            zip_data = await field.read()
            success = app.docs_manager.upload_zip(zip_data, version)
            return web.json_response({"success": success, "version": version})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.post("/api/v1/docs/switch")
    async def docs_switch(request):
        try:
            data = await request.json()
            version = data.get("version")
            if not version:
                return web.json_response(
                    {"error": "No version provided"},
                    status=400,
                )

            success = app.docs_manager.switch_version(version)
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.delete("/api/v1/docs/version/{version}")
    async def docs_delete_version(request):
        try:
            version = request.match_info.get("version")
            if not version:
                return web.json_response(
                    {"error": "No version provided"},
                    status=400,
                )

            success = app.docs_manager.delete_version(version)
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.delete("/api/v1/maintenance/docs/reticulum")
    async def docs_clear(request):
        try:
            success = app.docs_manager.clear_reticulum_docs()
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.get("/api/v1/docs/search")
    async def docs_search(request):
        query = request.query.get("q", "")
        lang = request.query.get("lang", "en")
        results = app.docs_manager.search(query, lang)
        return web.json_response({"results": results})

    @routes.get("/api/v1/meshchatx-docs/list")
    async def meshchatx_docs_list(request):
        lang = request.query.get("lang", "en")
        return web.json_response(app.docs_manager.get_meshchatx_docs_list(lang))

    @routes.get("/api/v1/meshchatx-docs/content")
    async def meshchatx_doc_content(request):
        path = request.query.get("path")
        if not path:
            return web.json_response({"error": "No path provided"}, status=400)
        if not app.docs_manager._is_safe_doc_path(path):
            return web.json_response({"error": "Invalid path"}, status=400)

        content = app.docs_manager.get_doc_content(path)
        if not content:
            return web.json_response({"error": "Document not found"}, status=404)

        return web.json_response(content)

    @routes.get("/api/v1/docs/export")
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
            return web.json_response({"error": str(e)}, status=500)

    @routes.get("/api/v1/docs/export/reticulum")
    async def reticulum_docs_export(request):
        try:
            zip_data = app.docs_manager.export_reticulum_docs()
            if zip_data is None:
                return web.json_response(
                    {"error": "No Reticulum manual available to export"},
                    status=404,
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
            return web.json_response({"error": str(e)}, status=500)
