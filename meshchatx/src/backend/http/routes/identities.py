# SPDX-License-Identifier: 0BSD
"""HTTP routes: identities."""

from __future__ import annotations

import io
import os
import shutil
import sys
import threading
import time
import zipfile

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_not_found,
    http_payload_too_large,
    http_unexpected,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_field_text_limited,
    read_json_limited,
)
from meshchatx.src.backend.meshchat_utils import (
    normalize_identity_storage_hash,
)
from meshchatx.src.path_utils import is_path_within_dir


def register_identities_routes(routes, app):

    @routes.post(API_V1_PREFIX + "/identity/backup/download")
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

    @routes.post(API_V1_PREFIX + "/identity/backup/base32")
    async def identity_backup_base32(request):
        try:
            return web.json_response(
                {
                    "identity_base32": app.backup_identity_base32(),
                },
            )
        except Exception:
            return http_unexpected("Failed to export identity")

    @routes.post(API_V1_PREFIX + "/identity/restore")
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

    @routes.get(API_V1_PREFIX + "/identities")
    async def identities_list(request):
        try:
            identities = app.list_identities()
            if app.database:
                for item in identities:
                    if item.get("is_current"):
                        item["message_count"] = (
                            app.database.messages.count_lxmf_messages()
                        )
                        break
            return web.json_response(
                {
                    "identities": identities,
                },
            )
        except Exception:
            return http_unexpected("Failed to list identities")

    @routes.post(API_V1_PREFIX + "/identities/export-all")
    async def identities_export_all(request):
        try:
            all_bytes = app.identity_manager.get_all_identity_backup_bytes()
            if not all_bytes:
                return http_bad_request("No identities to export")
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for identity_hash, data in all_bytes.items():
                    zf.writestr(f"identity_{identity_hash}", data)
            buf.seek(0)
            return web.Response(
                body=buf.read(),
                headers={
                    "Content-Type": "application/zip",
                    "Content-Disposition": 'attachment; filename="identities_export.zip"',
                },
            )
        except Exception:
            return http_unexpected("Failed to export identities")

    @routes.post(API_V1_PREFIX + "/identities/create")
    async def identities_create(request):
        try:
            data = await read_json_limited(request)
            display_name = data.get("display_name")
            result = app.create_identity(display_name)
            return web.json_response(
                {
                    "message": "Identity created successfully",
                    "identity": result,
                },
            )
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_unexpected("Failed to create identity")

    @routes.delete(API_V1_PREFIX + "/identities/{identity_hash}")
    async def identities_delete(request):
        try:
            identity_hash = normalize_identity_storage_hash(
                request.match_info.get("identity_hash"),
            )
            if not identity_hash:
                return http_bad_request("Invalid identity hash")
            if app.delete_identity(identity_hash):
                return web.json_response(
                    {
                        "message": "Identity deleted successfully",
                    },
                )
            return http_not_found("Identity not found")
        except ValueError as e:
            return http_bad_request(str(e))
        except Exception:
            return http_unexpected("Failed to delete identity")

    @routes.post(API_V1_PREFIX + "/identities/switch")
    async def identities_switch(request):
        try:
            data = await read_json_limited(request)
            identity_hash = normalize_identity_storage_hash(
                data.get("identity_hash"),
            )
            if not identity_hash:
                return http_bad_request("Invalid identity hash")
            keep_alive = data.get("keep_alive", False)

            # attempt hotswap first
            success = await app.hotswap_identity(
                identity_hash,
                keep_alive=keep_alive,
            )

            if success:
                display_name = (
                    app.config.display_name.get()
                    if hasattr(app, "config")
                    else "Unknown"
                )
                return web.json_response(
                    {
                        "message": "Identity switched successfully.",
                        "hotswapped": True,
                        "identity_hash": identity_hash,
                        "display_name": display_name,
                        "requires_reauth": bool(app.auth_enabled),
                    },
                )
            # fallback to restart if hotswap failed
            # (this part should probably be unreachable if hotswap is reliable)
            main_identity_file = app.identity_file_path or os.path.join(
                app.storage_dir,
                "identity",
            )
            identities_root = os.path.join(app.storage_dir, "identities")
            identity_dir = os.path.join(identities_root, identity_hash)
            identity_file = os.path.join(identity_dir, "identity")
            if not is_path_within_dir(identity_dir, identities_root):
                return http_bad_request("Invalid identity hash")

            # A symlinked identity file would copy the link target into the
            # active identity slot, reading an arbitrary local file.
            if os.path.islink(identity_file):
                return http_bad_request("Invalid identity file")
            shutil.copy2(identity_file, main_identity_file, follow_symlinks=False)

            def restart():
                time.sleep(1)
                try:
                    os.execv(sys.executable, [sys.executable, *sys.argv])  # noqa: S606
                except Exception as e:
                    print(f"Failed to restart: {e}")
                    os._exit(0)

            threading.Thread(target=restart).start()

            return web.json_response(
                {
                    "message": "Identity switch scheduled. Application will restart.",
                    "hotswapped": False,
                    "should_restart": True,
                },
            )
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_unexpected("Failed to switch identity")

    # maintenance - clear messages (all, or older than days / before date)
