# SPDX-License-Identifier: 0BSD
"""HTTP routes: interfaces modules."""

from __future__ import annotations

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error,
    http_not_found,
    http_payload_too_large,
    http_unexpected,
)

# ruff: noqa: F405
from meshchatx.src.backend.http.routes.interfaces._names import *  # noqa: F403
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_field_limited,
    read_field_text_limited,
    read_json_limited,
)


def register_interfaces_modules_routes(routes, app):

    @routes.get("/api/v1/reticulum/interface-modules")
    async def reticulum_interface_modules_list(_request):
        from meshchatx.src.backend.interface_module_store import (
            list_interface_modules,
        )

        try:
            payload = list_interface_modules(app.reticulum_config_dir)
        except ValueError as e:
            return http_bad_request(str(e))
        except Exception:
            return http_unexpected("Failed to list interface modules")
        return web.json_response(payload)

    @routes.post("/api/v1/reticulum/interface-modules")
    async def reticulum_interface_modules_install(request):
        from meshchatx.src.backend.interface_module_store import (
            _MAX_MODULE_BYTES,
            install_interface_module,
        )

        try:
            content_type = request.headers.get("Content-Type", "")
            filename = None
            data = b""
            overwrite = False
            if "multipart/form-data" in content_type:
                reader = await request.multipart()
                field = await reader.next()
                while field is not None:
                    if field.name == "file":
                        filename = field.filename or filename
                        data = await read_field_limited(field, _MAX_MODULE_BYTES)
                    elif field.name == "overwrite":
                        overwrite = (
                            await read_field_text_limited(field)
                        ).strip().lower() in (
                            "1",
                            "true",
                            "yes",
                            "on",
                        )
                    elif field.name == "filename":
                        filename = (
                            await read_field_text_limited(field)
                        ).strip() or filename
                    field = await reader.next()
            else:
                body = await read_json_limited(request, _MAX_MODULE_BYTES * 2)
                filename = body.get("filename") or body.get("type")
                raw = body.get("content") or body.get("data") or ""
                if isinstance(raw, str):
                    try:
                        data = base64.b64decode(raw, validate=False)
                    except (binascii.Error, ValueError):
                        data = raw.encode("utf-8")
                elif isinstance(raw, (bytes, bytearray)):
                    data = bytes(raw)
                overwrite = bool(body.get("overwrite", False))
            if not data:
                return http_bad_request("Interface module file is required")
            result = install_interface_module(
                app.reticulum_config_dir,
                filename=filename,
                data=data,
                overwrite=overwrite,
            )
            return web.json_response(
                {
                    "message": (
                        f"Installed {result['filename']}. "
                        "Reload Reticulum or restart MeshChatX to load it."
                    ),
                    **result,
                },
            )
        except PayloadTooLargeError:
            return http_payload_too_large()
        except ValueError as e:
            return http_error(422, str(e))
        except Exception:
            return http_unexpected("Failed to install interface module")

    @routes.delete("/api/v1/reticulum/interface-modules/{type_name}")
    async def reticulum_interface_modules_delete(request):
        from meshchatx.src.backend.interface_module_store import (
            delete_interface_module,
        )

        type_name = request.match_info.get("type_name")
        try:
            result = delete_interface_module(app.reticulum_config_dir, type_name)
        except FileNotFoundError as e:
            return http_not_found(str(e))
        except ValueError as e:
            return http_error(422, str(e))
        except Exception:
            return http_unexpected("Failed to delete interface module")
        return web.json_response(
            {
                "message": f"Deleted {result['filename']}",
                **result,
            },
        )

    # add reticulum interface
