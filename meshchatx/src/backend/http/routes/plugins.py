# SPDX-License-Identifier: 0BSD
"""HTTP routes: plugins."""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urljoin, urlparse

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_forbidden,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.safe_file_response import file_response
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
            # Deny by default: an install request that omits
            # granted_permissions must not silently receive every declared
            # permission.
            granted_permissions = []
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
        if not isinstance(args, dict):
            return http_bad_request("args must be an object")
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

    @routes.post(API_V1_PREFIX + "/plugins/{plugin_id}/storage")
    async def plugins_storage(request):
        if not app.plugins_enabled:
            return http_forbidden("Plugins are disabled")
        plugin_id = request.match_info["plugin_id"]
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            return http_bad_request("body must be an object")
        plugin = next(
            (
                item
                for item in app.plugin_manager.list_plugins()
                if item.get("id") == plugin_id
            ),
            None,
        )
        if plugin is None:
            return http_not_found("Plugin not found")
        if not plugin.get("enabled"):
            return http_forbidden("Plugin is disabled")
        action = data.get("action")
        key = data.get("key")
        value = data.get("value")
        try:
            if action == "get":
                result = app.plugin_manager.storage_get(plugin_id, key)
                return web.json_response({"result": {"value": result}})
            if action == "set":
                app.plugin_manager.storage_set(plugin_id, key, value)
                return web.json_response({"result": {"ok": True}})
            if action == "delete":
                deleted = app.plugin_manager.storage_delete(plugin_id, key)
                return web.json_response({"result": {"deleted": deleted}})
            if action == "list":
                keys = app.plugin_manager.storage_list(plugin_id)
                return web.json_response({"result": {"keys": keys}})
            if action == "clear":
                removed = app.plugin_manager.storage_clear(plugin_id)
                return web.json_response({"result": {"removed": removed}})
            return http_bad_request("unknown storage action")
        except KeyError:
            return http_not_found("Plugin not found")
        except PermissionError as e:
            return http_forbidden(str(e))
        except ValueError as e:
            return http_bad_request(str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message")

    @routes.post(API_V1_PREFIX + "/plugins/{plugin_id}/fetch")
    async def plugins_fetch(request):
        if not app.plugins_enabled:
            return http_forbidden("Plugins are disabled")
        plugin_id = request.match_info["plugin_id"]
        try:
            data = await read_json_limited(request, 512 * 1024)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            return http_bad_request("body must be an object")
        try:
            if not app.plugin_manager.network_fetch_allowed(plugin_id):
                return http_forbidden("network:fetch permission not granted")
        except KeyError:
            return http_not_found("Plugin not found")
        from meshchatx.src.backend.privacy_mode import (
            OutboundHttpBlockedError,
            ensure_outbound_http_allowed,
        )

        try:
            ensure_outbound_http_allowed(
                getattr(app, "config", None),
                feature="plugin fetch",
            )
        except OutboundHttpBlockedError as e:
            return http_forbidden(str(e))
        from meshchatx.src.backend.plugin_permissions import (
            is_allowed_plugin_fetch_url,
            plugin_fetch_host_resolves_public,
        )

        url = data.get("url")
        if not isinstance(url, str) or not is_allowed_plugin_fetch_url(url):
            return http_bad_request("url is not allowed")
        method = str(data.get("method") or "GET").upper()
        allowed_methods = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
        if method not in allowed_methods:
            return http_bad_request("method is not allowed")
        headers = data.get("headers") or {}
        if not isinstance(headers, dict) or len(headers) > 32:
            return http_bad_request("headers must be an object with at most 32 entries")
        clean_headers = {}
        stripped_headers = {
            "host",
            "content-length",
            "transfer-encoding",
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailer",
            "upgrade",
        }
        for name, header_value in headers.items():
            if not isinstance(name, str) or not isinstance(header_value, str):
                return http_bad_request("headers must map strings to strings")
            if len(name) > 128 or len(header_value) > 4096:
                return http_bad_request("header entry too large")
            if any(ch in name + header_value for ch in "\r\n"):
                return http_bad_request("header entries must not contain newlines")
            if name.strip().lower() in stripped_headers:
                continue
            clean_headers[name] = header_value
        body = data.get("body")
        if body is not None and not isinstance(body, str):
            return http_bad_request("body must be a string")
        if (
            body is not None
            and len(body.encode("utf-8", errors="replace")) > 256 * 1024
        ):
            return http_bad_request("body exceeds 256 KiB limit")

        import aiohttp

        timeout = aiohttp.ClientTimeout(total=20)
        max_response_bytes = 1024 * 1024
        max_redirects = 3
        # Per-request timeout is 20s; cap the whole redirect chain plus DNS
        # lookups at 30s so a plugin cannot hold a handler open indefinitely.
        deadline = asyncio.get_running_loop().time() + 30.0
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                current_url = url
                current_method = method
                current_body = body
                current_headers = dict(clean_headers)
                for _hop in range(max_redirects + 1):
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        return http_bad_request("fetch timed out")
                    try:
                        async with asyncio.timeout(remaining):
                            if not is_allowed_plugin_fetch_url(current_url):
                                return http_bad_request(
                                    "redirect target is not allowed"
                                )
                            if not await plugin_fetch_host_resolves_public(current_url):
                                return http_forbidden(
                                    "url does not resolve to a public address"
                                )
                            async with session.request(
                                current_method,
                                current_url,
                                headers=current_headers or None,
                                data=current_body if current_body is not None else None,
                                allow_redirects=False,
                            ) as response:
                                if response.status in (
                                    301,
                                    302,
                                    303,
                                    307,
                                    308,
                                ) and response.headers.get("location"):
                                    if _hop == max_redirects:
                                        return http_bad_request("too many redirects")
                                    location = response.headers["location"]
                                    next_url = urljoin(current_url, location)
                                    # Do not leak plugin-supplied credentials to a
                                    # different origin on redirect.
                                    try:
                                        current_parsed = urlparse(current_url)
                                        next_parsed = urlparse(next_url)
                                        same_origin = (
                                            next_parsed.scheme == current_parsed.scheme
                                            and next_parsed.hostname
                                            == current_parsed.hostname
                                            and (next_parsed.port or None)
                                            == (current_parsed.port or None)
                                        )
                                    except ValueError:
                                        same_origin = False
                                    if not same_origin:
                                        current_headers = {
                                            key: value
                                            for key, value in current_headers.items()
                                            if key.lower()
                                            not in (
                                                "authorization",
                                                "cookie",
                                                "proxy-authorization",
                                            )
                                        }
                                    if response.status == 303 or (
                                        response.status in (301, 302)
                                        and current_method not in ("GET", "HEAD")
                                    ):
                                        current_method = "GET"
                                        current_body = None
                                    current_url = next_url
                                    continue
                                raw = await response.content.read(
                                    max_response_bytes + 1
                                )
                                truncated = len(raw) > max_response_bytes
                                raw = raw[:max_response_bytes]
                                text = raw.decode("utf-8", errors="replace")
                                response_headers = {
                                    key: value
                                    for key, value in response.headers.items()
                                    if key.lower()
                                    not in (
                                        "set-cookie",
                                        "set-cookie2",
                                        # aiohttp already decoded the body;
                                        # these would describe the wire form.
                                        "content-encoding",
                                        "content-length",
                                    )
                                }
                                return web.json_response(
                                    {
                                        "result": {
                                            "status": response.status,
                                            "status_text": response.reason or "",
                                            "headers": response_headers,
                                            "body": text,
                                            "truncated": truncated,
                                            "url": current_url,
                                        }
                                    }
                                )
                    except TimeoutError:
                        return http_bad_request("fetch timed out")
                return http_bad_request("too many redirects")
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
        return file_response(
            path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    # --- Page Node API ---
