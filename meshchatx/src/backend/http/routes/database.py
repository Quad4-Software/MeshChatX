# SPDX-License-Identifier: 0BSD
"""HTTP routes: database."""

from __future__ import annotations

import asyncio
import contextlib
import os
import tempfile
import time

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
    read_json_limited,
    write_field_to_path,
)
from meshchatx.src.path_utils import safe_path_under_dir


def register_database_routes(routes, app):
    # ── Database ─────────────────────────────────────────────────────

    @routes.post(API_V1_PREFIX + "/database/snapshot")
    async def create_db_snapshot(request):
        try:
            data = await read_json_limited(request)
            name = data.get("name", f"snapshot-{int(time.time())}")
            result = app.database.create_snapshot(app.storage_path, name)
            return web.json_response({"status": "success", "result": result})
        except PayloadTooLargeError:
            return http_payload_too_large(
                "Upload exceeds size limit",
                status="error",
            )
        except Exception as e:
            return http_error_from_exception(
                e,
                key="message",
                extra={"status": "error"},
                fallback_status=500,
            )

    @routes.get(API_V1_PREFIX + "/database/snapshots")
    async def list_db_snapshots(request):
        try:
            limit = int(request.query.get("limit", 100))
            offset = int(request.query.get("offset", 0))
            snapshots = app.database.list_snapshots(app.storage_path)
            total = len(snapshots)
            paginated_snapshots = snapshots[offset : offset + limit]
            return web.json_response(
                {
                    "snapshots": paginated_snapshots,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            )
        except Exception as e:
            return http_error_from_exception(
                e,
                key="message",
                extra={"status": "error"},
                fallback_status=500,
            )

    @routes.delete(API_V1_PREFIX + "/database/snapshots/{filename}")
    async def delete_db_snapshot(request):
        try:
            filename = request.match_info.get("filename")
            if not filename.endswith(".zip"):
                filename += ".zip"
            app.database.delete_snapshot_or_backup(
                app.storage_path,
                filename,
                is_backup=False,
            )
            return web.json_response({"status": "success"})
        except Exception as e:
            return http_error_from_exception(
                e,
                key="message",
                extra={"status": "error"},
                fallback_status=500,
            )

    @routes.post(API_V1_PREFIX + "/database/restore")
    async def restore_db_snapshot(request):
        try:
            content_type = request.headers.get("Content-Type", "")

            # multipart upload: restore from a user-provided backup/zip file
            if "multipart/form-data" in content_type:
                reader = await request.multipart()
                field = await reader.next()
                if field is None or field.name != "file":
                    return http_bad_request(
                        "Restore file is required",
                        status="error",
                    )

                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    temp_path = tmp.name
                await write_field_to_path(
                    field,
                    temp_path,
                    UPLOAD_LIMITS["database_restore"],
                )

                try:
                    # Restore tears down identity contexts and blocks for up
                    # to ~30s; keep it off the event loop.
                    result = await asyncio.to_thread(
                        app.restore_database, temp_path, relaunch=True
                    )
                finally:
                    with contextlib.suppress(OSError):
                        os.remove(temp_path)

                return web.json_response(
                    {
                        "status": "success",
                        "result": result,
                        "database": result,
                        "requires_relaunch": True,
                        "message": "Database restored. Application will restart.",
                    },
                )

            # JSON body: restore from an on-disk snapshot/auto-backup path
            data = await read_json_limited(request)
            path = data.get("path")
            if not path:
                return http_bad_request(
                    "No path provided",
                    status="error",
                )

            resolved = app._resolve_database_restore_path(path)
            if not resolved:
                return http_not_found(
                    "Snapshot not found",
                    status="error",
                )

            result = await asyncio.to_thread(
                app.restore_database, resolved, relaunch=True
            )
            return web.json_response(
                {
                    "status": "success",
                    "result": result,
                    "requires_relaunch": True,
                    "message": "Database restored. Application will restart.",
                },
            )
        except PayloadTooLargeError:
            return http_payload_too_large(
                "Upload exceeds size limit",
                status="error",
            )
        except Exception as e:
            return http_error_from_exception(
                e,
                key="message",
                extra={"status": "error"},
                fallback_status=500,
            )

    @routes.get(API_V1_PREFIX + "/database/backups")
    async def list_db_backups(request):
        try:
            limit = int(request.query.get("limit", 100))
            offset = int(request.query.get("offset", 0))
            storage_path = app.storage_path
            if app.database is not None:
                sorted_backups = app.database.list_auto_backups(storage_path)
            else:
                from meshchatx.src.backend.database import Database

                db_path = app.database_path
                if not db_path:
                    sorted_backups = []
                else:
                    sorted_backups = Database(db_path).list_auto_backups(storage_path)
            total = len(sorted_backups)
            paginated_backups = sorted_backups[offset : offset + limit]
            return web.json_response(
                {
                    "backups": paginated_backups,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            )
        except Exception as e:
            return http_error_from_exception(
                e,
                key="message",
                extra={"status": "error"},
                fallback_status=500,
            )

    @routes.delete(API_V1_PREFIX + "/database/backups/{filename}")
    async def delete_db_backup(request):
        try:
            filename = request.match_info.get("filename")
            if not filename.endswith(".zip"):
                filename += ".zip"
            app.database.delete_snapshot_or_backup(
                app.storage_path,
                filename,
                is_backup=True,
            )
            return web.json_response({"status": "success"})
        except Exception as e:
            return http_error_from_exception(
                e,
                key="message",
                extra={"status": "error"},
                fallback_status=500,
            )

    @routes.post(API_V1_PREFIX + "/database/backups/{filename}/download")
    async def download_db_backup(request):
        try:
            filename = request.match_info.get("filename")
            if not filename.endswith(".zip"):
                filename += ".zip"
            backup_dir = os.path.join(app.storage_path, "database-backups")
            full_path = safe_path_under_dir(backup_dir, filename)

            if not full_path or not os.path.isfile(full_path):
                return http_not_found(
                    "Backup not found",
                    status="error",
                )

            return web.FileResponse(
                path=full_path,
                headers={
                    "Content-Disposition": f'attachment; filename="{os.path.basename(full_path)}"',
                },
            )
        except Exception as e:
            return http_error_from_exception(
                e,
                key="message",
                extra={"status": "error"},
                fallback_status=500,
            )

    @routes.post(API_V1_PREFIX + "/database/snapshots/{filename}/download")
    async def download_db_snapshot(request):
        try:
            filename = request.match_info.get("filename")
            if not filename.endswith(".zip"):
                filename += ".zip"
            snapshot_dir = os.path.join(app.storage_path, "snapshots")
            full_path = safe_path_under_dir(snapshot_dir, filename)

            if not full_path or not os.path.isfile(full_path):
                return http_not_found(
                    "Snapshot not found",
                    status="error",
                )

            return web.FileResponse(
                path=full_path,
                headers={
                    "Content-Disposition": f'attachment; filename="{os.path.basename(full_path)}"',
                },
            )
        except Exception as e:
            return http_error_from_exception(
                e,
                key="message",
                extra={"status": "error"},
                fallback_status=500,
            )

    @routes.get(API_V1_PREFIX + "/database/health")
    async def database_health(request):
        try:
            return web.json_response(
                {
                    "database": app.database.get_database_health_snapshot(),
                },
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post(API_V1_PREFIX + "/database/vacuum")
    async def database_vacuum(request):
        try:
            result = app.database.run_database_vacuum()
            return web.json_response(
                {
                    "message": "Database vacuum completed",
                    "database": result,
                },
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post(API_V1_PREFIX + "/database/recover")
    async def database_recover(request):
        try:
            result = app.database.run_database_recovery()
            return web.json_response(
                {
                    "message": "Database recovery routine completed",
                    "database": result,
                },
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post(API_V1_PREFIX + "/database/auto-recover")
    async def database_auto_recover(request):
        try:
            try:
                data = await read_json_limited(request)
            except PayloadTooLargeError:
                return http_payload_too_large(
                    "Upload exceeds size limit",
                    strategy="none",
                )
            except Exception:
                data = {}
            if not isinstance(data, dict):
                data = {}
            relaunch = bool(data.get("relaunch", True))
            result = app.auto_recover_database(relaunch=relaunch)
            status = 200 if result.get("strategy") != "none" else 500
            return web.json_response(
                {
                    "message": result.get("message"),
                    "strategy": result.get("strategy"),
                    "requires_relaunch": bool(result.get("requires_relaunch")),
                    "backup": result.get("backup"),
                    "database": result.get("database"),
                    "restore_result": result.get("restore_result"),
                    "error": result.get("error"),
                },
                status=status,
            )
        except Exception as e:
            return http_error_from_exception(
                e,
                key="message",
                extra={"strategy": "none"},
                fallback_status=500,
            )

    @routes.post(API_V1_PREFIX + "/database/backup")
    async def database_backup(request):
        try:
            result = app.database.backup_database(app.storage_path)
            return web.json_response(
                {
                    "message": "Database backup created",
                    "backup": result,
                },
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post(API_V1_PREFIX + "/database/backup/download")
    async def database_backup_download(request):
        # POST so CSRF middleware applies. Creating a zip is state-changing.
        try:
            backup_info = app.database.backup_database(app.storage_path)
            file_path = backup_info["path"]
            return web.FileResponse(
                path=file_path,
                headers={
                    "Content-Type": "application/zip",
                    "Content-Disposition": f'attachment; filename="{os.path.basename(file_path)}"',
                },
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
