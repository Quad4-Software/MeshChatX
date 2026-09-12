# SPDX-License-Identifier: 0BSD
"""HTTP routes: filesync."""

from __future__ import annotations

import asyncio
import contextlib
import os

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
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


def register_filesync_routes(routes, app):
    # --- RNS FileSync ---

    def _filesync_require_handler():
        return app._require_rns_tool_handler(
            app.rns_filesync_handler,
            "RNS FileSync",
        )

    @routes.get(API_V1_PREFIX + "/filesync/status")
    async def filesync_status(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response(app.rns_filesync_handler.get_status())

    @routes.post(API_V1_PREFIX + "/filesync/start")
    async def filesync_start(request):
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
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.start,
                sync_directory=data.get("sync_directory"),
                monitor=data.get("monitor"),
                announce_interval=data.get("announce_interval"),
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "failed to start"))
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/filesync/stop")
    async def filesync_stop(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            result = await asyncio.to_thread(app.rns_filesync_handler.stop)
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        return web.json_response(result)

    @routes.get(API_V1_PREFIX + "/filesync/peers")
    async def filesync_peers(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response({"peers": app.rns_filesync_handler.list_peers()})

    @routes.get(API_V1_PREFIX + "/filesync/files")
    async def filesync_files(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response({"files": app.rns_filesync_handler.list_files()})

    @routes.get(API_V1_PREFIX + "/filesync/tree")
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

    @routes.post(API_V1_PREFIX + "/filesync/mkdir")
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

    @routes.post(API_V1_PREFIX + "/filesync/upload")
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

    @routes.delete(API_V1_PREFIX + "/filesync/entry")
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

    @routes.get(API_V1_PREFIX + "/filesync/content")
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

    @routes.get(API_V1_PREFIX + "/filesync/directories")
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

    @routes.get(API_V1_PREFIX + "/filesync/shared-directory-suggestion")
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

    @routes.post(API_V1_PREFIX + "/filesync/directories")
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

    @routes.post(API_V1_PREFIX + "/filesync/connect")
    async def filesync_connect(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        if not isinstance(data, dict):
            return http_bad_request("Invalid JSON body")
        identity_hash = data.get("identity_hash", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.connect_peer,
                identity_hash,
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "connect failed"), **result)
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/filesync/disconnect")
    async def filesync_disconnect(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        if not isinstance(data, dict):
            return http_bad_request("Invalid JSON body")
        peer_id = data.get("peer_id", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.disconnect_peer,
                peer_id,
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "disconnect failed"))
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/filesync/announce")
    async def filesync_announce(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            result = await asyncio.to_thread(app.rns_filesync_handler.announce_now)
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "announce failed"))
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/filesync/browse")
    async def filesync_browse(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        if not isinstance(data, dict):
            return http_bad_request("Invalid JSON body")
        peer_id = data.get("peer_id", "")
        timeout = data.get("timeout", 10.0)
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.browse_peer,
                peer_id,
                timeout,
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(
                result.get("error", "browse failed"), files=result.get("files", [])
            )
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/filesync/download")
    async def filesync_download(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        if not isinstance(data, dict):
            return http_bad_request("Invalid JSON body")
        peer_id = data.get("peer_id", "")
        path = data.get("path", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.download_file,
                peer_id,
                path,
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "download failed"), **result)
        return web.json_response(result)

    @routes.get(API_V1_PREFIX + "/filesync/acl")
    async def filesync_acl_get(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response(app.rns_filesync_handler.get_acl())

    @routes.post(API_V1_PREFIX + "/filesync/acl")
    async def filesync_acl_post(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        if not isinstance(data, dict):
            return http_bad_request("Invalid JSON body")
        perms = data.get("perms")
        if perms is not None and not isinstance(perms, list):
            return http_bad_request("perms must be a list")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.update_acl,
                identity_hash=data.get("identity_hash"),
                perms=perms,
                enforce=data.get("enforce"),
                rules_text=data.get("rules_text"),
                replace=bool(data.get("replace", False)),
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "acl update failed"))
        return web.json_response(result)

    @routes.patch(API_V1_PREFIX + "/filesync/settings")
    async def filesync_settings(request):
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
                app.rns_filesync_handler.update_settings,
                sync_directory=data.get("sync_directory"),
                monitor=data.get("monitor"),
                announce_interval=data.get("announce_interval"),
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "settings update failed"))
        return web.json_response(result)

    # --- Plugin API ---
