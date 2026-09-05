# SPDX-License-Identifier: 0BSD
"""HTTP routes: rrc hubs."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.rrc._names import *  # noqa: F403, F405
from meshchatx.src.backend.http.routes.rrc._helpers import (
    RRC_ROOM_MESSAGES_DEFAULT_LIMIT,
    RRC_ROOM_MESSAGES_MAX_LIMIT,
    make_rrc_helpers,
)


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
        data = await request.json()
        hub_hash_hex = (data.get("hub_hash") or "").strip()
        try:
            hub_hash = bytes.fromhex(hub_hash_hex)
        except (ValueError, TypeError):
            return web.json_response(
                {"message": "A valid hub hash is required"},
                status=400,
            )
        if len(hub_hash) != rrc_protocol.HUB_HASH_BYTES:
            return web.json_response(
                {"message": "Hub hash has an invalid length"},
                status=400,
            )
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
        data = await request.json()
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
                return web.json_response({"message": str(e)}, status=400)
        if data.get("revert_hub_icon"):
            hub.set_hub_icon(None)
        return web.json_response({"hub": hub.to_dict()})

    @routes.put("/api/v1/rrc/hubs/order")
    async def rrc_hubs_reorder(request):
        manager, error = _rrc_require_manager()
        if error is not None:
            return error
        data = await request.json()
        hub_hashes = data.get("hub_hashes")
        if not isinstance(hub_hashes, list):
            return web.json_response(
                {"message": "hub_hashes must be a list"},
                status=400,
            )
        if not manager.reorder_hubs(hub_hashes):
            return web.json_response(
                {"message": "Invalid hub order"},
                status=400,
            )
        return web.json_response(manager.to_dict())

    @routes.put("/api/v1/rrc/hubs/{hub_hash}/rooms/order")
    async def rrc_hub_rooms_reorder(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        data = await request.json()
        room_names = data.get("room_names")
        if not isinstance(room_names, list):
            return web.json_response(
                {"message": "room_names must be a list"},
                status=400,
            )
        if not hub.reorder_rooms(room_names):
            return web.json_response(
                {"message": "Invalid room order"},
                status=400,
            )
        return web.json_response({"hub": hub.to_dict()})

    @routes.post("/api/v1/rrc/hubs/{hub_hash}/rooms/list")
    async def rrc_hub_rooms_list(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        try:
            hub.request_room_list()
        except (ValueError, RuntimeError) as e:
            return web.json_response({"message": str(e)}, status=400)
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
        data = await request.json()
        room = (data.get("room") or "").strip()
        if not room:
            return web.json_response(
                {"message": "A room name is required"},
                status=400,
            )
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
            return web.json_response({"message": str(e)}, status=400)
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
        data = await request.json()
        key = data.get("key")
        if not isinstance(key, str) or not key.strip():
            return web.json_response(
                {"message": "A room key is required"},
                status=400,
            )
        try:
            manager.remember_room_key(hub, room, key.strip())
        except (TypeError, ValueError, RuntimeError) as e:
            return web.json_response({"message": str(e)}, status=400)
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
            return web.json_response({"message": str(e)}, status=400)
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
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"hub": hub.to_dict()})

    @routes.delete("/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages")
    async def rrc_hub_clear_room(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        try:
            hub.clear_messages(request.match_info.get("room", ""))
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
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
            return web.json_response({"message": str(e)}, status=400)
        manager.set_active(hub, room)
        app._mark_rrc_mention_notifications_viewed(
            request.match_info.get("hub_hash", ""),
            room,
        )
        return web.json_response(
            {"messages": messages, "members": members, "has_more": has_more},
        )

    @routes.post("/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages")
    async def rrc_hub_send_message(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        room = request.match_info.get("room", "")
        data = await request.json()
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
            return web.json_response({"message": str(e)}, status=400)
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
            return web.json_response({"message": str(e)}, status=400)
        app._mark_rrc_mention_notifications_viewed(
            request.match_info.get("hub_hash", ""),
            room,
        )
        return web.json_response({"message": "Marked read"})

    @routes.post("/api/v1/rrc/active/clear")
    async def rrc_clear_active(request):
        manager = app.rrc_manager
        if manager is None:
            return web.json_response(
                {"message": "Relay chat is not available"},
                status=503,
            )
        manager.set_active(None, None)
        return web.json_response({"message": "Active room cleared"})

    @routes.post("/api/v1/rrc/hubs/{hub_hash}/command")
    async def rrc_hub_command(request):
        _, hub, error = _rrc_require_hub(request.match_info.get("hub_hash", ""))
        if error is not None:
            return error
        data = await request.json()
        text = data.get("text")
        room = data.get("room") or None
        try:
            hub.send_command(text, room=room)
        except (ValueError, RuntimeError) as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"message": "Sent"})

    # Reticulum Relay Chat hosting (local hubs)
