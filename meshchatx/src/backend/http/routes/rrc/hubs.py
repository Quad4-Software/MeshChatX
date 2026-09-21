# SPDX-License-Identifier: 0BSD
"""HTTP routes: rrc hubs."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.rrc._names import *  # noqa: F403, F405
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_payload_too_large,
    http_unavailable,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)

from meshchatx.src.backend.http.routes.rrc._helpers import (
    RRC_ROOM_MESSAGES_DEFAULT_LIMIT,
    RRC_ROOM_MESSAGES_MAX_LIMIT,
    make_rrc_helpers,
)
from meshchatx.src.backend.rrc import search as rrc_search


def register_rrc_hubs_routes(routes, app):
    (
        _rrc_require_manager,
        _rrc_require_hub,
        _rrc_server_require_manager,
        _rrc_server_require_hub,
    ) = make_rrc_helpers(app)

    @routes.get("/api/v1/rrc/hubs")
    async def rrc_hubs_get(request):
        manager, error = _rrc_require_manager()
        if error is not None:
            return error
        return web.json_response(manager.to_dict())

    @routes.post("/api/v1/rrc/hubs")
    async def rrc_hubs_post(request):
        manager, error = _rrc_require_manager()
        if error is not None:
            return error
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        hub_hash_hex = (data.get("hub_hash") or "").strip()
        try:
            hub_hash = bytes.fromhex(hub_hash_hex)
        except (ValueError, TypeError):
            return http_bad_request("A valid hub hash is required")
        if len(hub_hash) != rrc_protocol.HUB_HASH_BYTES:
            return http_bad_request("Hub hash has an invalid length")
        dest_name = data.get("dest_name") or None
        name = data.get("name") or None
        hub = manager.add_hub(hub_hash, dest_name=dest_name, name=name)
        if data.get("connect"):
            hub.connect()
        return web.json_response({"hub": hub.to_dict()})

    @routes.delete("/api/v1/rrc/hubs/{hub_hash}")
    async def rrc_hub_delete(request):
        manager, hub, error = _rrc_require_hub(
            request.match_info.get("hub_hash", ""),
        )
        if error is not None:
            return error
        manager.remove_hub(hub)
        return web.json_response({"message": "Hub removed"})

    @routes.patch("/api/v1/rrc/hubs/{hub_hash}")
    async def rrc_hub_patch(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        if "auto_reconnect" in data:
            hub.set_auto_reconnect(bool(data["auto_reconnect"]))
        if "auto_list" in data:
            hub.set_auto_list(bool(data["auto_list"]))
        if "auto_who" in data:
            hub.set_auto_who(bool(data["auto_who"]))
        if "nick" in data:
            hub.set_nick_override(data["nick"])
        if "custom_name" in data:
            hub.set_custom_name(data.get("custom_name"))
        if data.get("revert_custom_name"):
            hub.set_custom_name(None)
        if "hub_icon" in data:
            try:
                hub.set_hub_icon(data.get("hub_icon"))
            except ValueError as e:
                return http_bad_request(str(e))
        if data.get("revert_hub_icon"):
            hub.set_hub_icon(None)
        return web.json_response({"hub": hub.to_dict()})

    @routes.put("/api/v1/rrc/hubs/order")
    async def rrc_hubs_reorder(request):
        manager, error = _rrc_require_manager()
        if error is not None:
            return error
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        hub_hashes = data.get("hub_hashes")
        if not isinstance(hub_hashes, list):
            return http_bad_request("hub_hashes must be a list")
        if not manager.reorder_hubs(hub_hashes):
            return http_bad_request("Invalid hub order")
        return web.json_response(manager.to_dict())

    @routes.post("/api/v1/rrc/hubs/options")
    async def rrc_hubs_apply_options(request):
        """Apply shared hub options to every configured hub at once.

        Handles auto_reconnect, auto_list, and auto_who keys from the request body.
        """
        manager, error = _rrc_require_manager()
        if error is not None:
            return error
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        applied = {}
        for key in ("auto_reconnect", "auto_list", "auto_who"):
            if key in data:
                applied[key] = bool(data[key])
        if not applied:
            return http_bad_request("No hub options supplied")
        for hub in list(manager.hubs):
            if "auto_reconnect" in applied:
                hub.set_auto_reconnect(applied["auto_reconnect"], save=False)
            if "auto_list" in applied:
                hub.set_auto_list(applied["auto_list"], save=False)
            if "auto_who" in applied:
                hub.set_auto_who(applied["auto_who"], save=False)
        manager.save()
        return web.json_response(manager.to_dict())

    @routes.put("/api/v1/rrc/hubs/{hub_hash}/rooms/order")
    async def rrc_hub_rooms_reorder(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        room_names = data.get("room_names")
        if not isinstance(room_names, list):
            return http_bad_request("room_names must be a list")
        if not hub.reorder_rooms(room_names):
            return http_bad_request("Invalid room order")
        return web.json_response({"hub": hub.to_dict()})

    @routes.post("/api/v1/rrc/hubs/{hub_hash}/rooms/list")
    async def rrc_hub_rooms_list(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        try:
            hub.request_room_list()
        except (ValueError, RuntimeError) as e:
            return http_bad_request(str(e))
        return web.json_response(
            {"message": "Room list requested", "hub": hub.to_dict()},
        )

    @routes.post("/api/v1/rrc/hubs/{hub_hash}/connect")
    async def rrc_hub_connect(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        hub.connect()
        return web.json_response({"hub": hub.to_dict()})

    @routes.post("/api/v1/rrc/hubs/{hub_hash}/disconnect")
    async def rrc_hub_disconnect(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        hub.disconnect()
        return web.json_response({"hub": hub.to_dict()})

    @routes.post("/api/v1/rrc/hubs/{hub_hash}/rooms")
    async def rrc_hub_join_room(request):
        manager, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        room = (data.get("room") or "").strip()
        if not room:
            return http_bad_request("A room name is required")
        key = data.get("key")
        if isinstance(key, str):
            key = key.strip() or None
        else:
            key = None
        remember = bool(data.get("remember", True))
        if key is None:
            with contextlib.suppress(Exception):
                key = manager.get_room_key(hub, room)
        try:
            if hub.status == hub.STATUS_CONNECTED:
                hub.join_room(room, key=key)
            else:
                hub.add_room(room)
            # Persist even while offline so WELCOME auto-rejoin can supply +k.
            if key and remember:
                with contextlib.suppress(Exception):
                    manager.remember_room_key(hub, room, key)
        except (ValueError, RuntimeError) as e:
            return http_bad_request(str(e))
        return web.json_response(
            {
                "hub": hub.to_dict(),
                "has_stored_key": manager.has_stored_room_key(hub, room),
            },
        )

    @routes.get("/api/v1/rrc/hubs/{hub_hash}/room-keys")
    async def rrc_hub_list_room_keys(request):
        manager, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        return web.json_response({"keys": manager.list_stored_room_keys(hub)})

    @routes.put("/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/key")
    async def rrc_hub_store_room_key(request):
        manager, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        room = request.match_info.get("room", "")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        key = data.get("key")
        if not isinstance(key, str) or not key.strip():
            return http_bad_request("A room key is required")
        try:
            manager.remember_room_key(hub, room, key.strip())
        except (TypeError, ValueError, RuntimeError) as e:
            return http_bad_request(str(e))
        return web.json_response(
            {
                "message": "Room key saved",
                "has_stored_key": True,
            },
        )

    @routes.delete("/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/key")
    async def rrc_hub_delete_room_key(request):
        manager, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        room = request.match_info.get("room", "")
        try:
            deleted = manager.forget_room_key(hub, room)
        except ValueError as e:
            return http_bad_request(str(e))
        return web.json_response(
            {
                "message": "Room key removed" if deleted else "No stored room key",
                "deleted": int(deleted or 0),
            },
        )

    @routes.delete("/api/v1/rrc/hubs/{hub_hash}/rooms/{room}")
    async def rrc_hub_part_room(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        room = request.match_info.get("room", "")
        try:
            if hub.status == hub.STATUS_CONNECTED:
                hub.part_room(room)
            else:
                hub.remove_room(room)
        except ValueError as e:
            return http_bad_request(str(e))
        return web.json_response({"hub": hub.to_dict()})

    @routes.delete("/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages")
    async def rrc_hub_clear_room(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        try:
            hub.clear_messages(request.match_info.get("room", ""))
        except ValueError as e:
            return http_bad_request(str(e))
        return web.json_response({"message": "Messages cleared"})

    @routes.get("/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages")
    async def rrc_hub_room_messages(request):
        manager, hub, error = _rrc_require_hub(
            request.match_info.get("hub_hash", ""),
        )
        if error is not None:
            return error
        room = request.match_info.get("room", "")
        try:
            limit = int(request.query.get("limit", RRC_ROOM_MESSAGES_DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = RRC_ROOM_MESSAGES_DEFAULT_LIMIT
        limit = max(1, min(limit, RRC_ROOM_MESSAGES_MAX_LIMIT))
        before_seq_raw = request.query.get("before_seq")
        before_seq = None
        if before_seq_raw not in (None, ""):
            try:
                before_seq = int(before_seq_raw)
            except (TypeError, ValueError):
                before_seq = None
        try:
            messages, has_more = hub.room_messages(
                room,
                limit=limit,
                before_seq=before_seq,
            )
            members = hub.members_dict(room)
        except ValueError as e:
            return http_bad_request(str(e))
        manager.set_active(hub, room)
        app._mark_rrc_mention_notifications_viewed(
            request.match_info.get("hub_hash", ""),
            room,
        )
        return web.json_response(
            {"messages": messages, "members": members, "has_more": has_more},
        )

    @routes.get("/api/v1/rrc/search")
    async def rrc_search_messages(request):
        manager, error = _rrc_require_manager()
        if error is not None:
            return error
        query = request.query.get("q", "")
        if not isinstance(query, str) or not query.strip():
            return web.json_response({"results": []})
        try:
            limit = int(request.query.get("limit", rrc_search.DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = rrc_search.DEFAULT_LIMIT
        limit = max(1, min(limit, rrc_search.MAX_LIMIT))
        with manager._lock:
            hubs = list(manager.hubs)
        return web.json_response(
            {"results": rrc_search.search_hubs(hubs, query, limit=limit)},
        )

    @routes.post("/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages")
    async def rrc_hub_send_message(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        room = request.match_info.get("room", "")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        text = data.get("text")
        is_action = bool(data.get("action"))
        try:
            if is_action:
                hub.send_action(room, text)
            elif isinstance(text, str) and text.strip().startswith("/"):
                hub.send_command(text.strip(), room=room)
            else:
                hub.send_message(room, text)
        except (ValueError, RuntimeError) as e:
            return http_bad_request(str(e))
        return web.json_response({"message": "Sent"})

    @routes.post("/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/read")
    async def rrc_hub_mark_read(request):
        manager, hub, error = _rrc_require_hub(
            request.match_info.get("hub_hash", ""),
        )
        if error is not None:
            return error
        room = request.match_info.get("room", "")
        try:
            manager.set_active(hub, room)
        except ValueError as e:
            return http_bad_request(str(e))
        app._mark_rrc_mention_notifications_viewed(
            request.match_info.get("hub_hash", ""),
            room,
        )
        return web.json_response({"message": "Marked read"})

    @routes.post("/api/v1/rrc/active/clear")
    async def rrc_clear_active(request):
        manager = app.rrc_manager
        if manager is None:
            return http_unavailable("Relay chat is not available")
        manager.set_active(None, None)
        return web.json_response({"message": "Active room cleared"})

    @routes.post("/api/v1/rrc/hubs/{hub_hash}/command")
    async def rrc_hub_command(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        text = data.get("text")
        room = data.get("room") or None
        try:
            hub.send_command(text, room=room)
        except (ValueError, RuntimeError) as e:
            return http_bad_request(str(e))
        return web.json_response({"message": "Sent"})

    # Reticulum Relay Chat hosting (local hubs)
