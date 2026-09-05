# SPDX-License-Identifier: 0BSD
"""HTTP routes: filesync tree and files."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.filesync._helpers import make_filesync_helpers
from meshchatx.src.backend.http.routes.filesync._names import *  # noqa: F403


def register_filesync_tree_routes(routes: Any, app: Any) -> None:
    (_filesync_require_handler,) = make_filesync_helpers(app)

    @routes.get("/api/v1/filesync/files")
    async def filesync_files(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response({"files": app.rns_filesync_handler.list_files()})

    @routes.get("/api/v1/filesync/tree")
    async def filesync_tree(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        path = request.rel_url.query.get("path")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.list_tree,
                path,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "list tree failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/mkdir")
    async def filesync_mkdir(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.manager_mkdir,
                data.get("path", ""),
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "mkdir failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/upload")
    async def filesync_upload(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        subdir = None
        filename = None
        file_data = None
        try:
            reader = await request.multipart()
            while True:
                field = await reader.next()
                if field is None:
                    break
                name = field.name or ""
                if name == "path":
                    subdir = (await field.text()).strip() or None
                elif name == "file":
                    filename = field.filename or "upload"
                    file_data = await field.read()
                else:
                    with contextlib.suppress(Exception):
                        await field.read()
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid upload request: {e}"},
                status=400,
            )
        if file_data is None:
            return web.json_response({"message": "No file uploaded"}, status=400)
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.manager_upload,
                filename=filename,
                data=file_data,
                subdir=subdir,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "upload failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.delete("/api/v1/filesync/entry")
    async def filesync_entry_delete(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = {}
        with contextlib.suppress(Exception):
            data = await request.json()
        if not isinstance(data, dict):
            data = {}
        path = data.get("path", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.manager_delete,
                path,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "delete failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.get("/api/v1/filesync/content")
    async def filesync_content(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        path = request.rel_url.query.get("path", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.manager_content,
                path,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "content failed")},
                status=400,
            )
        abspath = result.get("abspath")
        filename = result.get("filename") or "download"
        if not abspath or not os.path.isfile(abspath):
            return web.json_response({"message": "file not found"}, status=404)
        safe_name = (
            os.path.basename(str(filename))
            .replace('"', "_")
            .replace("\r", "")
            .replace("\n", "")
            .replace("\x00", "")
        ) or "download"
        return web.FileResponse(
            abspath,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}"',
            },
        )

    @routes.get("/api/v1/filesync/directories")
    async def filesync_directories(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        path = request.rel_url.query.get("path")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.list_directories,
                path,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "list directories failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.get("/api/v1/filesync/shared-directory-suggestion")
    async def filesync_shared_directory_suggestion(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.suggest_shared_sync_directory,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "suggestion failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/directories")
    async def filesync_directories_create(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.create_directory,
                data.get("parent"),
                data.get("name", ""),
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "create directory failed")},
                status=400,
            )
        return web.json_response(result)
