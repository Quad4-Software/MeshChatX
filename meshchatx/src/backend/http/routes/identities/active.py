# SPDX-License-Identifier: 0BSD
"""HTTP routes: identities/active."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.identities._names import *  # noqa: F403


def register_identities_active_routes(routes: Any, app: Any) -> None:
    @routes.post("/api/v1/identity/backup/download")
    async def identity_backup_download(request):
        try:
            info = app.backup_identity()
            with open(info["path"], "rb") as f:
                data = f.read()
            return web.Response(
                body=data,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Disposition": 'attachment; filename="identity.bin"',
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to create identity backup: {e!s}",
                },
                status=500,
            )

    @routes.post("/api/v1/identity/backup/base32")
    async def identity_backup_base32(request):
        try:
            return web.json_response(
                {
                    "identity_base32": app.backup_identity_base32(),
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to export identity: {e!s}",
                },
                status=500,
            )

    @routes.post("/api/v1/identity/restore")
    async def identity_restore(request):
        try:
            content_type = request.headers.get("Content-Type", "")
            # multipart file upload
            if "multipart/form-data" in content_type:
                reader = await request.multipart()
                identity_bytes = None
                display_name = None
                field = await reader.next()
                while field is not None:
                    if field.name == "file":
                        from meshchatx.src.backend.identity_manager import (
                            IdentityManager,
                        )

                        identity_bytes = await IdentityManager.read_upload_bytes_capped(
                            field.read_chunk,
                        )
                    elif field.name == "display_name":
                        display_name = (await field.text()).strip() or None
                    field = await reader.next()
                if identity_bytes is None:
                    return web.json_response(
                        {"message": "Identity file is required"},
                        status=400,
                    )
                result = app.restore_identity_from_bytes(
                    identity_bytes,
                    display_name=display_name,
                )
            else:
                data = await request.json()
                base32_value = data.get("base32")
                if not base32_value:
                    return web.json_response(
                        {"message": "base32 value is required"},
                        status=400,
                    )
                result = app.restore_identity_from_base32(
                    base32_value,
                    display_name=data.get("display_name"),
                )

            return web.json_response(
                {
                    "message": "Identity restored. Restart app to use the new identity.",
                    "identity": result,
                },
            )
        except ValueError as e:
            return web.json_response(
                {
                    "message": str(e),
                },
                status=400,
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to restore identity: {e!s}",
                },
                status=500,
            )
