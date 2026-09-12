# SPDX-License-Identifier: 0BSD
"""HTTP routes: bots."""

from __future__ import annotations

import asyncio
import os

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_conflict,
    http_error_from_exception,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)

_MISSING = object()


def register_bots_routes(routes, app):

    @routes.get(API_V1_PREFIX + "/bots/status")
    async def bots_status(request):
        try:
            status = app.bot_handler.get_status()
            templates = app.bot_handler.get_available_templates()
            if app.database:
                for bot in status.get("bots") or []:
                    lxmf_addr = bot.get("lxmf_address") or bot.get("full_address")
                    if not lxmf_addr:
                        bot["last_announce_at"] = None
                        continue
                    lxmf_addr = str(lxmf_addr).strip().lower()
                    ann = app.database.announces.get_announce_by_hash(lxmf_addr)
                    if not ann:
                        bot["last_announce_at"] = None
                        continue
                    arow = dict(ann) if not isinstance(ann, dict) else ann
                    ts = arow.get("updated_at")
                    if ts is not None and hasattr(ts, "isoformat"):
                        bot["last_announce_at"] = ts.isoformat()
                    else:
                        bot["last_announce_at"] = str(ts) if ts is not None else None
            return web.json_response(
                {
                    "status": status,
                    "templates": templates,
                    "detection_error": status.get("detection_error"),
                },
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post(API_V1_PREFIX + "/bots/start")
    async def bots_start(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        template_id = data.get("template_id")
        name = data.get("name")
        bot_id = data.get("bot_id")

        if not template_id:
            return http_bad_request("template_id is required")

        try:
            extra = {}
            if "icon" in data:
                extra["icon"] = data.get("icon")
            if "custom" in data:
                extra["custom"] = data.get("custom")
            bot_id = await asyncio.to_thread(
                app.bot_handler.start_bot,
                template_id,
                name,
                bot_id,
                None,
                data.get("lxmf_config"),
                data.get("rrc"),
                **extra,
            )
            return web.json_response({"bot_id": bot_id, "success": True})
        except ValueError as e:
            return http_bad_request(str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post(API_V1_PREFIX + "/bots/stop")
    async def bots_stop(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        bot_id = data.get("bot_id")

        if not bot_id:
            return http_bad_request("bot_id is required")

        try:
            success = await asyncio.to_thread(app.bot_handler.stop_bot, bot_id)
            return web.json_response({"success": success})
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post(API_V1_PREFIX + "/bots/restart")
    async def bots_restart(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        bot_id = data.get("bot_id")

        if not bot_id:
            return http_bad_request("bot_id is required")

        try:
            new_id = await asyncio.to_thread(
                app.bot_handler.restart_bot,
                bot_id,
            )
            return web.json_response({"bot_id": new_id, "success": True})
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post(API_V1_PREFIX + "/bots/delete")
    async def bots_delete(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        bot_id = data.get("bot_id")

        if not bot_id:
            return http_bad_request("bot_id is required")

        try:
            success = await asyncio.to_thread(app.bot_handler.delete_bot, bot_id)
            return web.json_response({"success": success})
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.get(API_V1_PREFIX + "/bots/subprocess-log")
    async def bots_subprocess_log(request):
        bot_id = request.query.get("bot_id")

        if not bot_id:
            return http_bad_request("bot_id is required")

        try:
            result = await asyncio.to_thread(
                app.bot_handler.read_subprocess_log,
                bot_id,
            )
            return web.json_response(result)
        except ValueError as e:
            return http_not_found(str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.patch(API_V1_PREFIX + "/bots/update")
    async def bots_update(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        bot_id = data.get("bot_id")
        name = data.get("name")
        lxmf_config = data.get("lxmf_config")
        rrc_config = data.get("rrc")
        icon = data.get("icon", _MISSING)
        custom = data.get("custom", _MISSING)

        if not bot_id:
            return http_bad_request("bot_id is required")

        try:
            if name is not None:
                await asyncio.to_thread(
                    app.bot_handler.update_bot_name,
                    bot_id,
                    name,
                )
            saved_lxmf = None
            if lxmf_config is not None:
                saved_lxmf = await asyncio.to_thread(
                    app.bot_handler.update_bot_lxmf_config,
                    bot_id,
                    lxmf_config,
                )
            saved_rrc = None
            if rrc_config is not None:
                saved_rrc = await asyncio.to_thread(
                    app.bot_handler.update_bot_rrc_config,
                    bot_id,
                    rrc_config,
                )
            response = {"success": True}
            if saved_lxmf is not None:
                response["lxmf_config"] = saved_lxmf
            if saved_rrc is not None:
                response["rrc"] = saved_rrc
            if icon is not _MISSING:
                response["icon"] = await asyncio.to_thread(
                    app.bot_handler.update_bot_icon,
                    bot_id,
                    icon,
                )
            if custom is not _MISSING:
                response["custom"] = await asyncio.to_thread(
                    app.bot_handler.update_bot_custom,
                    bot_id,
                    custom,
                )
            return web.json_response(response)
        except ValueError as e:
            return http_bad_request(str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.patch(API_V1_PREFIX + "/bots/lxmf-config")
    async def bots_lxmf_config(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        bot_id = data.get("bot_id")
        lxmf_config = data.get("lxmf_config")

        if not bot_id:
            return http_bad_request("bot_id is required")
        if lxmf_config is None:
            return http_bad_request("lxmf_config is required")

        try:
            saved = await asyncio.to_thread(
                app.bot_handler.update_bot_lxmf_config,
                bot_id,
                lxmf_config,
            )
            return web.json_response({"success": True, "lxmf_config": saved})
        except ValueError as e:
            return http_bad_request(str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post(API_V1_PREFIX + "/bots/announce")
    async def bots_announce(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        bot_id = data.get("bot_id")

        if not bot_id:
            return http_bad_request("bot_id is required")

        try:
            await asyncio.to_thread(app.bot_handler.request_announce, bot_id)
            return web.json_response({"success": True})
        except ValueError as e:
            return http_bad_request(str(e))
        except RuntimeError as e:
            return http_conflict(str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post(API_V1_PREFIX + "/bots/export")
    async def bots_export(request):
        bot_id = None
        try:
            data = await read_json_limited(request)
            if isinstance(data, dict):
                bot_id = data.get("bot_id")
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            bot_id = None
        if not bot_id:
            bot_id = request.query.get("bot_id")

        if not bot_id:
            return http_bad_request("bot_id is required")

        try:
            id_path = app.bot_handler.get_bot_identity_path(bot_id)
            if not id_path or not os.path.exists(id_path):
                return http_not_found("Identity file not found")

            return web.FileResponse(
                id_path,
                headers={
                    "Content-Disposition": f'attachment; filename="bot_{bot_id}_identity"',
                },
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    # get custom destination display name
