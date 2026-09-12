# SPDX-License-Identifier: 0BSD
"""HTTP routes: plugins."""

from __future__ import annotations

import asyncio
import json

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_forbidden,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_body_limited,
    read_field_limited,
    read_field_text_limited,
    read_json_limited,
)
from meshchatx.src.backend.plugin_guard import MAX_PLUGIN_ZIP_BYTES, PluginSecurityError


def register_plugins_routes(routes, app):

    # --- Plugin API ---

    @routes.get(API_V1_PREFIX + "/plugins")
    async def plugins_list(request):
        return web.json_response(
            {
                "plugins": app.plugin_manager.list_plugins(),
                "plugins_enabled": app.plugins_enabled,
            },
        )

    @routes.post(API_V1_PREFIX + "/plugins/preview")
    async def plugins_preview(request):
        if not app.plugins_enabled:
            return http_forbidden("Plugins are disabled")
        try:
            if request.content_type and "multipart" in request.content_type:
                reader = await request.multipart()
                field = await reader.next()
                if field is None:
                    return http_bad_request("No plugin archive provided")
                payload = await read_field_limited(field, MAX_PLUGIN_ZIP_BYTES)
            else:
                payload = await read_body_limited(request, MAX_PLUGIN_ZIP_BYTES)
            if not payload:
                return http_bad_request("No plugin archive provided")
            preview = await asyncio.to_thread(
                app.plugin_manager.preview_from_zip_bytes,
                payload,
            )
            return web.json_response(preview)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception as e:
            return http_error_from_exception(e, key="message")

    @routes.get(API_V1_PREFIX + "/plugins/trusted-publishers")
    async def plugins_trusted_publishers_list(request):
        tampered, reason = app.plugin_manager.trusted_publishers_tampered()
        return web.json_response(
            {
                "publishers": app.plugin_manager.list_trusted_publishers(),
                "tampered": tampered,
                "tamper_reason": reason,
            },
        )

    @routes.post(API_V1_PREFIX + "/plugins/trusted-publishers")
    async def plugins_trusted_publishers_add(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
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
            return http_error_from_exception(e, key="message")

    @routes.delete(API_V1_PREFIX + "/plugins/trusted-publishers/{identity}")
    async def plugins_trusted_publishers_remove(request):
        identity = request.match_info["identity"]
        try:
            publishers = await asyncio.to_thread(
                app.plugin_manager.remove_trusted_publisher,
                identity,
            )
            return web.json_response({"publishers": publishers})
        except Exception as e:
            return http_error_from_exception(e, key="message")

    @routes.post(API_V1_PREFIX + "/plugins/install")
    async def plugins_install(request):
        if not app.plugins_enabled:
            return http_forbidden("Plugins are disabled")
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
                        payload = await read_field_limited(
                            field,
                            MAX_PLUGIN_ZIP_BYTES,
                        )
                    elif name == "granted_permissions":
                        raw = await read_field_text_limited(field, 8 * 1024)
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
                    body = await read_json_limited(request, MAX_PLUGIN_ZIP_BYTES * 2)
                    archive_b64 = body.get("archive_b64") or body.get("zip_b64")
                    if not archive_b64:
                        return http_bad_request("No plugin archive provided")
                    import base64

                    payload = base64.b64decode(archive_b64, validate=True)
                    granted = body.get("granted_permissions")
                    if isinstance(granted, list):
                        granted_permissions = [
                            item for item in granted if isinstance(item, str)
                        ]
                else:
                    payload = await read_body_limited(request, MAX_PLUGIN_ZIP_BYTES)
            if not payload:
                return http_bad_request("No plugin archive provided")
            plugin = await asyncio.to_thread(
                app.plugin_manager.install_from_zip_bytes,
                payload,
                granted_permissions,
            )
            return web.json_response(plugin)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception as e:
            return http_error_from_exception(e, key="message")

    @routes.post(API_V1_PREFIX + "/plugins/{plugin_id}/enable")
    async def plugins_enable(request):
        if not app.plugins_enabled:
            return http_forbidden("Plugins are disabled")
        plugin_id = request.match_info["plugin_id"]
        try:
            plugin = await asyncio.to_thread(app.plugin_manager.enable, plugin_id)
            return web.json_response(plugin)
        except KeyError:
            return http_not_found("Plugin not found")
        except Exception as e:
            return http_error_from_exception(e, key="message")

    @routes.post(API_V1_PREFIX + "/plugins/{plugin_id}/disable")
    async def plugins_disable(request):
        plugin_id = request.match_info["plugin_id"]
        try:
            plugin = await asyncio.to_thread(app.plugin_manager.disable, plugin_id)
            return web.json_response(plugin)
        except KeyError:
            return http_not_found("Plugin not found")
        except Exception as e:
            return http_error_from_exception(e, key="message")

    @routes.delete(API_V1_PREFIX + "/plugins/{plugin_id}")
    async def plugins_remove(request):
        plugin_id = request.match_info["plugin_id"]
        try:
            await asyncio.to_thread(app.plugin_manager.remove, plugin_id)
            return web.json_response({"message": "Plugin removed"})
        except KeyError:
            return http_not_found("Plugin not found")

    @routes.post(API_V1_PREFIX + "/plugins/{plugin_id}/report-failure")
    async def plugins_report_failure(request):
        plugin_id = request.match_info["plugin_id"]
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
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
                return http_not_found("Plugin not found")
            return web.json_response(plugin)
        except Exception as e:
            return http_error_from_exception(e, key="message")

    @routes.post(API_V1_PREFIX + "/plugins/{plugin_id}/invoke")
    async def plugins_invoke(request):
        if not app.plugins_enabled:
            return http_forbidden("Plugins are disabled")
        plugin_id = request.match_info["plugin_id"]
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            data = {}
        method = data.get("method")
        args = data.get("args") or {}
        if not method:
            return http_bad_request("method is required")
        try:
            result = await asyncio.to_thread(
                app.plugin_manager.invoke,
                plugin_id,
                method,
                args,
            )
            return web.json_response({"result": result})
        except KeyError:
            return http_not_found("Plugin not found")
        except PermissionError as e:
            return http_forbidden(str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message")

    @routes.get(API_V1_PREFIX + "/plugins/{plugin_id}/asset/{asset_path:.*}")
    async def plugins_asset(request):
        if not app.plugins_enabled:
            return http_forbidden("Plugins are disabled")
        plugin_id = request.match_info["plugin_id"]
        asset_path = request.match_info["asset_path"]
        try:
            path = app.plugin_manager.asset_path(plugin_id, asset_path)
        except KeyError:
            return http_not_found("Plugin not found")
        except FileNotFoundError:
            return http_not_found("Asset not found")
        except PluginSecurityError as e:
            return http_bad_request(str(e))
        except ValueError as e:
            return http_bad_request(str(e))
        return web.FileResponse(
            path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    # --- Page Node API ---
