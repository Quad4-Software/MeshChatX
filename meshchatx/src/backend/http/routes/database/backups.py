# SPDX-License-Identifier: 0BSD
"""HTTP routes: database/backups."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.database._names import *  # noqa: F403


def register_database_backups_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/database/backups")
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
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    @routes.delete("/api/v1/database/backups/{filename}")
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
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/database/backups/{filename}/download")
    async def download_db_backup(request):
        try:
            filename = request.match_info.get("filename")
            if not filename.endswith(".zip"):
                filename += ".zip"
            backup_dir = os.path.join(app.storage_path, "database-backups")
            full_path = safe_path_under_dir(backup_dir, filename)

            if not full_path or not os.path.isfile(full_path):
                return web.json_response(
                    {"status": "error", "message": "Backup not found"},
                    status=404,
                )

            return web.FileResponse(
                path=full_path,
                headers={
                    "Content-Disposition": f'attachment; filename="{os.path.basename(full_path)}"',
                },
            )
        except Exception as e:
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/database/backup")
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
            return web.json_response(
                {
                    "message": f"Failed to create database backup: {e!s}",
                },
                status=500,
            )

    @routes.post("/api/v1/database/backup/download")
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
            return web.json_response(
                {
                    "message": f"Failed to create database backup: {e!s}",
                },
                status=500,
            )
