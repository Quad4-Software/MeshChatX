# SPDX-License-Identifier: 0BSD
"""HTTP routes: filesync tree and files."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.filesync._helpers import make_filesync_helpers
from meshchatx.src.backend.http.routes.filesync._names import *  # noqa: F403

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_field_limited,
    read_field_text_limited,
    read_json_limited,
    write_field_to_path,
)
from meshchatx.src.backend.rns_filesync_handler import MANAGER_UPLOAD_MAX_BYTES


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
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "list tree failed"))
        return web.json_response(result)

    @routes.post("/api/v1/filesync/mkdir")
    async def filesync_mkdir(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        if not isinstance(data, dict):
            return http_bad_request("Invalid JSON body")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.manager_mkdir,
                data.get("path", ""),
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "mkdir failed"))
        return web.json_response(result)

    @routes.post("/api/v1/filesync/upload")
    async def filesync_upload(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        subdir = None
        filename = None
        tmp_path = None
        try:
            reader = await request.multipart()
            while True:
                field = await reader.next()
                if field is None:
                    break
                name = field.name or ""
                if name == "path":
                    subdir = (await read_field_text_limited(field)).strip() or None
                elif name == "file":
                    filename = field.filename or "upload"
                    if tmp_path is not None:
                        with contextlib.suppress(OSError):
                            os.unlink(tmp_path)
                    tmp_path = await asyncio.to_thread(
                        app.rns_filesync_handler.manager_upload_staging_path,
                    )
                    await write_field_to_path(
                        field,
                        tmp_path,
                        MANAGER_UPLOAD_MAX_BYTES,
                    )
                else:
                    with contextlib.suppress(Exception):
                        await read_field_limited(field, MANAGER_UPLOAD_MAX_BYTES)
        except PayloadTooLargeError:
            if tmp_path is not None:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
            return http_payload_too_large()
        except Exception as e:
            if tmp_path is not None:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
            return http_bad_request(f"Invalid upload request: {e}")
        if tmp_path is None:
            return http_bad_request("No file uploaded")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.manager_upload_file,
                filename=filename,
                src_path=tmp_path,
                subdir=subdir,
            )
        except Exception as e:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            return http_bad_request(result.get("error", "upload failed"))
        return web.json_response(result)

    @routes.delete("/api/v1/filesync/entry")
    async def filesync_entry_delete(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = {}
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        path = data.get("path", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.manager_delete,
                path,
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "delete failed"))
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
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "content failed"))
        abspath = result.get("abspath")
        filename = result.get("filename") or "download"
        if not abspath or not os.path.isfile(abspath):
            return http_not_found("file not found")
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
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "list directories failed"))
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
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "suggestion failed"))
        return web.json_response(result)

    @routes.post("/api/v1/filesync/directories")
    async def filesync_directories_create(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        if not isinstance(data, dict):
            return http_bad_request("Invalid JSON body")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.create_directory,
                data.get("parent"),
                data.get("name", ""),
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "create directory failed"))
        return web.json_response(result)
