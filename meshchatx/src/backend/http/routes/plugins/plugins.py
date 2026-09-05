# SPDX-License-Identifier: 0BSD
"""HTTP routes: plugins/plugins."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.plugins._names import *  # noqa: F403


def register_plugins_plugins_routes(routes: Any, app: Any) -> None:

    # --- Plugin API ---

    @routes.get("/api/v1/plugins")
    async def plugins_list(request):
        return web.json_response(
            {
                "plugins": app.plugin_manager.list_plugins(),
                "plugins_enabled": app.plugins_enabled,
            },
        )

    @routes.post("/api/v1/plugins/preview")
    async def plugins_preview(request):
        if not app.plugins_enabled:
            return web.json_response(
                {"message": "Plugins are disabled"},
                status=403,
            )
        try:
            if request.content_type and "multipart" in request.content_type:
                reader = await request.multipart()
                field = await reader.next()
                if field is None:
                    return web.json_response(
                        {"message": "No plugin archive provided"},
                        status=400,
                    )
                payload = await field.read()
            else:
                payload = await request.read()
            if not payload:
                return web.json_response(
                    {"message": "No plugin archive provided"},
                    status=400,
                )
            preview = await asyncio.to_thread(
                app.plugin_manager.preview_from_zip_bytes,
                payload,
            )
            return web.json_response(preview)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)

    @routes.get("/api/v1/plugins/trusted-publishers")
    async def plugins_trusted_publishers_list(request):
        tampered, reason = app.plugin_manager.trusted_publishers_tampered()
        return web.json_response(
            {
                "publishers": app.plugin_manager.list_trusted_publishers(),
                "tampered": tampered,
                "tamper_reason": reason,
            },
        )

    @routes.post("/api/v1/plugins/trusted-publishers")
    async def plugins_trusted_publishers_add(request):
        try:
            data = await request.json()
        except Exception:
            data = {}
        identity = data.get("identity") or ""
        name = data.get("name") or ""
        try:
            publishers = await asyncio.to_thread(
                app.plugin_manager.add_trusted_publisher,
                identity,
                name,
            )
            return web.json_response({"publishers": publishers})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)

    @routes.delete("/api/v1/plugins/trusted-publishers/{identity}")
    async def plugins_trusted_publishers_remove(request):
        identity = request.match_info["identity"]
        try:
            publishers = await asyncio.to_thread(
                app.plugin_manager.remove_trusted_publisher,
                identity,
            )
            return web.json_response({"publishers": publishers})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)

    @routes.post("/api/v1/plugins/install")
    async def plugins_install(request):
        if not app.plugins_enabled:
            return web.json_response(
                {"message": "Plugins are disabled"},
                status=403,
            )
        try:
            granted_permissions = None
            payload = b""
            if request.content_type and "multipart" in request.content_type:
                reader = await request.multipart()
                while True:
                    field = await reader.next()
                    if field is None:
                        break
                    name = field.name or ""
                    if name in ("archive", "file", "plugin"):
                        payload = await field.read()
                    elif name == "granted_permissions":
                        raw = await field.text()
                        try:
                            parsed = json.loads(raw)
                        except Exception:
                            parsed = None
                        if isinstance(parsed, list):
                            granted_permissions = [
                                item for item in parsed if isinstance(item, str)
                            ]
            else:
                content_type = request.content_type or ""
                if "application/json" in content_type:
                    body = await request.json()
                    archive_b64 = body.get("archive_b64") or body.get("zip_b64")
                    if not archive_b64:
                        return web.json_response(
                            {"message": "No plugin archive provided"},
                            status=400,
                        )
                    import base64

                    payload = base64.b64decode(archive_b64, validate=True)
                    granted = body.get("granted_permissions")
                    if isinstance(granted, list):
                        granted_permissions = [
                            item for item in granted if isinstance(item, str)
                        ]
                else:
                    payload = await request.read()
            if not payload:
                return web.json_response(
                    {"message": "No plugin archive provided"},
                    status=400,
                )
            plugin = await asyncio.to_thread(
                app.plugin_manager.install_from_zip_bytes,
                payload,
                granted_permissions,
            )
            return web.json_response(plugin)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)

    @routes.post("/api/v1/plugins/{plugin_id}/enable")
    async def plugins_enable(request):
        if not app.plugins_enabled:
            return web.json_response(
                {"message": "Plugins are disabled"},
                status=403,
            )
        plugin_id = request.match_info["plugin_id"]
        try:
            plugin = await asyncio.to_thread(app.plugin_manager.enable, plugin_id)
            return web.json_response(plugin)
        except KeyError:
            return web.json_response({"message": "Plugin not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)

    @routes.post("/api/v1/plugins/{plugin_id}/disable")
    async def plugins_disable(request):
        plugin_id = request.match_info["plugin_id"]
        try:
            plugin = await asyncio.to_thread(app.plugin_manager.disable, plugin_id)
            return web.json_response(plugin)
        except KeyError:
            return web.json_response({"message": "Plugin not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)

    @routes.delete("/api/v1/plugins/{plugin_id}")
    async def plugins_remove(request):
        plugin_id = request.match_info["plugin_id"]
        try:
            await asyncio.to_thread(app.plugin_manager.remove, plugin_id)
            return web.json_response({"message": "Plugin removed"})
        except KeyError:
            return web.json_response({"message": "Plugin not found"}, status=404)

    @routes.post("/api/v1/plugins/{plugin_id}/report-failure")
    async def plugins_report_failure(request):
        plugin_id = request.match_info["plugin_id"]
        try:
            data = await request.json()
        except Exception:
            data = {}
        reason = data.get("reason") or "Unknown plugin failure"
        source = data.get("source") or "frontend"
        try:
            plugin = await asyncio.to_thread(
                app.plugin_manager.report_failure,
                plugin_id,
                reason,
                source,
            )
            if plugin is None:
                return web.json_response(
                    {"message": "Plugin not found"},
                    status=404,
                )
            return web.json_response(plugin)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)

    @routes.post("/api/v1/plugins/{plugin_id}/invoke")
    async def plugins_invoke(request):
        if not app.plugins_enabled:
            return web.json_response(
                {"message": "Plugins are disabled"},
                status=403,
            )
        plugin_id = request.match_info["plugin_id"]
        try:
            data = await request.json()
        except Exception:
            data = {}
        method = data.get("method")
        args = data.get("args") or {}
        if not method:
            return web.json_response({"message": "method is required"}, status=400)
        try:
            result = await asyncio.to_thread(
                app.plugin_manager.invoke,
                plugin_id,
                method,
                args,
            )
            return web.json_response({"result": result})
        except KeyError:
            return web.json_response({"message": "Plugin not found"}, status=404)
        except PermissionError as e:
            return web.json_response({"message": str(e)}, status=403)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)

    @routes.get("/api/v1/plugins/{plugin_id}/asset/{asset_path:.*}")
    async def plugins_asset(request):
        if not app.plugins_enabled:
            return web.json_response(
                {"message": "Plugins are disabled"},
                status=403,
            )
        plugin_id = request.match_info["plugin_id"]
        asset_path = request.match_info["asset_path"]
        try:
            path = app.plugin_manager.asset_path(plugin_id, asset_path)
        except KeyError:
            return web.json_response({"message": "Plugin not found"}, status=404)
        except FileNotFoundError:
            return web.json_response({"message": "Asset not found"}, status=404)
        except PluginSecurityError as e:
            return web.json_response({"message": str(e)}, status=400)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.FileResponse(
            path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
