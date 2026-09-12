# SPDX-License-Identifier: 0BSD
"""HTTP routes: blocklist."""

from __future__ import annotations

import json
import logging

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.db_availability import (
    http_for_database_exception,
    require_database,
)
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_payload_too_large,
    http_unavailable,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)
from meshchatx.src.backend.message_blocklist import (
    build_export_document as build_blocklist_export_document,
)
from meshchatx.src.backend.message_blocklist import (
    normalize_message_blocklist,
    parse_import_document,
    parse_message_blocklist_json,
)

logger = logging.getLogger(__name__)


def register_blocklist_routes(routes, app):
    @routes.get(API_V1_PREFIX + "/lxmf/message-blocklist")
    async def lxmf_message_blocklist_get(request):
        raw = app.config.message_blocklist_json.get()
        return web.json_response(
            {
                "enabled": app.config.message_blocklist_enabled.get(),
                "blocklist": parse_message_blocklist_json(raw),
            },
        )

    @routes.put(API_V1_PREFIX + "/lxmf/message-blocklist")
    async def lxmf_message_blocklist_put(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        blocklist_in = data.get("blocklist")
        if not isinstance(blocklist_in, dict):
            return http_bad_request("blocklist must be an object")
        normalized = normalize_message_blocklist(blocklist_in)
        if "enabled" in data:
            app.config.message_blocklist_enabled.set(
                app._parse_bool(data["enabled"]),
            )
        app.config.message_blocklist_json.set(json.dumps(normalized))
        return web.json_response(
            {
                "enabled": app.config.message_blocklist_enabled.get(),
                "blocklist": normalized,
            },
        )

    @routes.get(API_V1_PREFIX + "/lxmf/message-blocklist/export")
    async def lxmf_message_blocklist_export(request):
        raw = app.config.message_blocklist_json.get()
        blocklist = parse_message_blocklist_json(raw)
        return web.json_response(build_blocklist_export_document(blocklist))

    @routes.post(API_V1_PREFIX + "/lxmf/message-blocklist/import")
    async def lxmf_message_blocklist_import(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        document = data.get("document")
        if not isinstance(document, dict):
            return http_bad_request("document must be an object")
        merge = app._parse_bool(data.get("merge", False))
        existing = parse_message_blocklist_json(
            app.config.message_blocklist_json.get(),
        )
        imported = parse_import_document(
            document,
            merge=merge,
            existing=existing,
        )
        if imported is None:
            return http_bad_request("Invalid blocklist document")
        app.config.message_blocklist_json.set(json.dumps(imported))
        return web.json_response(
            {
                "enabled": app.config.message_blocklist_enabled.get(),
                "blocklist": imported,
            },
        )

    # get blocked destinations
    @routes.get(API_V1_PREFIX + "/blocked-destinations")
    async def blocked_destinations_get(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        try:
            blocked = app.database.misc.get_blocked_destinations()
            blocked_list = [
                {
                    "destination_hash": b["destination_hash"],
                    "created_at": b["created_at"],
                }
                for b in blocked
            ]
            return web.json_response(
                {
                    "blocked_destinations": blocked_list,
                },
            )
        except Exception as e:
            logger.exception("blocked_destinations_get failed")
            return http_for_database_exception(e)

    # add blocked destination

    # add blocked destination
    @routes.post(API_V1_PREFIX + "/blocked-destinations")
    async def blocked_destinations_add(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        destination_hash = data.get("destination_hash", "")
        if not destination_hash or len(destination_hash) != 32:
            return http_bad_request("Invalid destination hash")

        try:
            app.banish_lxmf_peer(destination_hash)
        except Exception:
            return http_bad_request("Failed to banish destination")

        return web.json_response({"message": "ok"})

    # remove blocked destination

    # remove blocked destination
    @routes.delete(API_V1_PREFIX + "/blocked-destinations/{destination_hash}")
    async def blocked_destinations_delete(request):
        destination_hash = request.match_info.get("destination_hash", "")
        if not destination_hash or len(destination_hash) != 32:
            return http_bad_request("Invalid destination hash")

        try:
            app.lift_lxmf_peer_banishment(destination_hash)
            return web.json_response({"message": "ok"})
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    @routes.get(API_V1_PREFIX + "/reticulum/blackhole")
    async def reticulum_blackhole_get(request):
        if not hasattr(app, "reticulum") or not app.reticulum:
            return http_unavailable("Reticulum not initialized")

        try:
            if hasattr(app.reticulum, "get_blackholed_identities"):
                identities = app.reticulum.get_blackholed_identities()
                # Convert bytes keys to hex strings
                formatted = {}
                for h, info in identities.items():
                    formatted[h.hex()] = {
                        "source": info.get("source", b"").hex()
                        if info.get("source")
                        else None,
                        "until": info.get("until"),
                        "reason": info.get("reason"),
                    }
                return web.json_response({"blackholed_identities": formatted})
            return web.json_response({"blackholed_identities": {}})
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    # get spam keywords
