# SPDX-License-Identifier: 0BSD
"""HTTP routes: interfaces modules."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.interfaces._names import *  # noqa: F403, F405


def register_interfaces_modules_routes(routes, app):

    @routes.get("/api/v1/reticulum/interface-modules")
    async def reticulum_interface_modules_list(_request):
        from meshchatx.src.backend.interface_module_store import (
            list_interface_modules,
        )

        try:
            payload = list_interface_modules(app.reticulum_config_dir)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to list interface modules: {e!s}"},
                status=500,
            )
        return web.json_response(payload)

    @routes.post("/api/v1/reticulum/interface-modules")
    async def reticulum_interface_modules_install(request):
        from meshchatx.src.backend.interface_module_store import (
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
                        chunks = []
                        while True:
                            chunk = await field.read_chunk()
                            if not chunk:
                                break
                            chunks.append(chunk)
                        data = b"".join(chunks)
                    elif field.name == "overwrite":
                        overwrite = (await field.text()).strip().lower() in (
                            "1",
                            "true",
                            "yes",
                            "on",
                        )
                    elif field.name == "filename":
                        filename = (await field.text()).strip() or filename
                    field = await reader.next()
            else:
                body = await request.json()
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
                return web.json_response(
                    {"message": "Interface module file is required"},
                    status=400,
                )
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
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=422)
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to install interface module: {e!s}"},
                status=500,
            )

    @routes.delete("/api/v1/reticulum/interface-modules/{type_name}")
    async def reticulum_interface_modules_delete(request):
        from meshchatx.src.backend.interface_module_store import (
            delete_interface_module,
        )

        type_name = request.match_info.get("type_name")
        try:
            result = delete_interface_module(app.reticulum_config_dir, type_name)
        except FileNotFoundError as e:
            return web.json_response({"message": str(e)}, status=404)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=422)
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to delete interface module: {e!s}"},
                status=500,
            )
        return web.json_response(
            {
                "message": f"Deleted {result['filename']}",
                **result,
            },
        )

    # add reticulum interface
