# SPDX-License-Identifier: 0BSD
"""HTTP routes: identities/active."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_payload_too_large,
    http_unexpected,
)

# ruff: noqa: F403, F405
from meshchatx.src.backend.http.routes.identities._names import *
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_field_text_limited,
    read_json_limited,
)


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
        except Exception:
            return http_unexpected("Failed to create identity backup")

    @routes.post("/api/v1/identity/backup/base32")
    async def identity_backup_base32(request):
        try:
            return web.json_response(
                {
                    "identity_base32": app.backup_identity_base32(),
                },
            )
        except Exception:
            return http_unexpected("Failed to export identity")

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
                        display_name = (
                            await read_field_text_limited(field)
                        ).strip() or None
                    field = await reader.next()
                if identity_bytes is None:
                    return http_bad_request("Identity file is required")
                result = app.restore_identity_from_bytes(
                    identity_bytes,
                    display_name=display_name,
                )
            else:
                data = await read_json_limited(request)
                base32_value = data.get("base32")
                if not base32_value:
                    return http_bad_request("base32 value is required")
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
        except PayloadTooLargeError:
            return http_payload_too_large()
        except ValueError as e:
            return http_bad_request(str(e))
        except Exception:
            return http_unexpected("Failed to restore identity")
