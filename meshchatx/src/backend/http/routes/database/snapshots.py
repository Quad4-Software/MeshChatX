# SPDX-License-Identifier: 0BSD
"""HTTP routes: database/snapshots."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_not_found,
    http_payload_too_large,
    parse_int_param,
)

# ruff: noqa: F403, F405
from meshchatx.src.backend.http.routes.database._names import *
from meshchatx.src.backend.http.uploads import (
    UPLOAD_LIMITS,
    PayloadTooLargeError,
    read_json_limited,
    write_field_to_path,
)


def register_database_snapshots_routes(routes: Any, app: Any) -> None:
    # ── Database ─────────────────────────────────────────────────────

    @routes.post("/api/v1/database/snapshot")
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

    @routes.get("/api/v1/database/snapshots")
    async def list_db_snapshots(request):
        try:
            limit = parse_int_param(request.query.get("limit"), 100, minimum=0)
            offset = parse_int_param(request.query.get("offset"), 0, minimum=0)
            if limit is None or offset is None:
                return http_bad_request(
                    "limit and offset must be non-negative integers",
                )
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

    @routes.delete("/api/v1/database/snapshots/{filename}")
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

    @routes.post("/api/v1/database/snapshots/{filename}/download")
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

    @routes.post("/api/v1/database/restore")
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
