# SPDX-License-Identifier: 0BSD
"""HTTP routes: rrc servers."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.rrc._names import *  # noqa: F403, F405
from meshchatx.src.backend.http.routes.rrc._helpers import (
    make_rrc_helpers,
)


def register_rrc_servers_routes(routes, app):
    (
        _rrc_require_manager,
        _rrc_require_hub,
        _rrc_server_require_manager,
        _rrc_server_require_hub,
    ) = make_rrc_helpers(app)

    # Reticulum Relay Chat hosting (local hubs)

    @routes.get("/api/v1/rrc/servers")
    async def rrc_servers_get(request):
        manager, error = _rrc_server_require_manager()
        if error is not None:
            return error
        return web.json_response(manager.to_dict())

    @routes.post("/api/v1/rrc/servers")
    async def rrc_servers_post(request):
        manager, error = _rrc_server_require_manager()
        if error is not None:
            return error
        data = await request.json()
        name = (data.get("name") or "").strip() or None
        greeting = (data.get("greeting") or "").strip() or None
        announce = bool(data.get("announce", True))
        enabled = bool(data.get("enabled", True))
        create_kwargs = {
            "name": name,
            "greeting": greeting,
            "announce": announce,
            "enabled": enabled,
        }
        if "announce_interval_seconds" in data:
            create_kwargs["announce_interval_seconds"] = data.get(
                "announce_interval_seconds",
            )
        hub = manager.create_hub(**create_kwargs)
        return web.json_response({"hub": hub.to_dict()})

    @routes.delete("/api/v1/rrc/servers/{hub_id}")
    async def rrc_server_delete(request):
        manager, _, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        manager.delete_hub(request.match_info.get("hub_id", ""))
        return web.json_response({"message": "Hub removed"})

    @routes.patch("/api/v1/rrc/servers/{hub_id}")
    async def rrc_server_patch(request):
        manager, hub, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        data = await request.json()
        manager.update_hub(
            hub.hub_id,
            name=(data.get("name") if "name" in data else None),
            greeting=(data.get("greeting") if "greeting" in data else None),
            announce=(data.get("announce") if "announce" in data else None),
            announce_interval_seconds=(
                data.get("announce_interval_seconds")
                if "announce_interval_seconds" in data
                else None
            ),
            trusted_identities=(
                data.get("trusted_identities") if "trusted_identities" in data else None
            ),
            banned_identities=(
                data.get("banned_identities") if "banned_identities" in data else None
            ),
        )
        return web.json_response({"hub": hub.to_dict()})

    @routes.post("/api/v1/rrc/servers/{hub_id}/start")
    async def rrc_server_start(request):
        manager, hub, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        manager.start_hub(hub.hub_id)
        return web.json_response({"hub": hub.to_dict()})

    @routes.post("/api/v1/rrc/servers/{hub_id}/stop")
    async def rrc_server_stop(request):
        manager, hub, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        manager.stop_hub(hub.hub_id)
        return web.json_response({"hub": hub.to_dict()})

    @routes.post("/api/v1/rrc/servers/{hub_id}/announce")
    async def rrc_server_announce(request):
        _, hub, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        hub.announce_now()
        return web.json_response({"message": "Announced"})

    @routes.post("/api/v1/rrc/servers/{hub_id}/rooms")
    async def rrc_server_room_create(request):
        manager, hub, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        data = await request.json()
        name = (data.get("name") or "").strip()
        if not name:
            return web.json_response(
                {"message": "A room name is required"},
                status=400,
            )
        topic = (data.get("topic") or "").strip() or None
        private = bool(data.get("private", False))
        moderated = bool(data.get("moderated", False))
        invite_only = bool(data.get("invite_only", False))
        topic_ops_only = bool(data.get("topic_ops_only", False))
        no_outside_msgs = bool(data.get("no_outside_msgs", False))
        key = (data.get("key") or "").strip() or None
        try:
            manager.create_room(
                hub.hub_id,
                name,
                topic=topic,
                private=private,
                moderated=moderated,
                invite_only=invite_only,
                topic_ops_only=topic_ops_only,
                no_outside_msgs=no_outside_msgs,
                key=key,
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"hub": hub.to_dict()})

    @routes.delete("/api/v1/rrc/servers/{hub_id}/rooms/{room}")
    async def rrc_server_room_delete(request):
        manager, hub, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        manager.delete_room(hub.hub_id, request.match_info.get("room", ""))
        return web.json_response({"hub": hub.to_dict()})

    @routes.put("/api/v1/rrc/servers/{hub_id}/rooms/{room}/key")
    async def rrc_server_room_set_key(request):
        manager, hub, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        room = request.match_info.get("room", "")
        data = await request.json()
        raw_key = data.get("key")
        if raw_key is None or raw_key == "":
            key = None
        elif isinstance(raw_key, str):
            key = raw_key.strip() or None
        else:
            return web.json_response(
                {"message": "Room key must be a string or null"},
                status=400,
            )
        try:
            hub.set_room_key(room, key)
            manager.save()
        except (TypeError, ValueError) as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"hub": hub.to_dict()})

    @routes.get("/api/v1/rrc/servers/{hub_id}/members")
    async def rrc_server_members(request):
        _, hub, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        room = request.rel_url.query.get("room")
        room_arg = room.strip() if isinstance(room, str) and room.strip() else None
        try:
            members = hub.members_dict(room_arg)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"members": members})

    @routes.get("/api/v1/rrc/servers/{hub_id}/activity")
    async def rrc_server_activity(request):
        _, hub, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        return web.json_response(hub.rooms_activity())

    @routes.get("/api/v1/rrc/servers/{hub_id}/messages")
    async def rrc_server_messages(request):
        _, hub, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        peer = request.rel_url.query.get("peer")
        if not isinstance(peer, str) or not peer.strip():
            return web.json_response(
                {"message": "peer query parameter is required"},
                status=400,
            )
        room = request.rel_url.query.get("room")
        room_arg = room.strip() if isinstance(room, str) and room.strip() else None
        limit = request.rel_url.query.get("limit")
        try:
            messages = hub.messages_for_peer(
                peer.strip(),
                room=room_arg,
                limit=limit,
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"messages": messages})

    @routes.post("/api/v1/rrc/servers/{hub_id}/moderate")
    async def rrc_server_moderate(request):
        _, hub, error = _rrc_server_require_hub(
            request.match_info.get("hub_id", ""),
        )
        if error is not None:
            return error
        data = await request.json()
        action = (data.get("action") or "").strip().lower()
        peer = (data.get("peer") or "").strip()
        room = (data.get("room") or "").strip() or None
        if action not in ("kick", "ban", "room_ban"):
            return web.json_response(
                {"message": "action must be kick, ban, or room_ban"},
                status=400,
            )
        if not peer:
            return web.json_response(
                {"message": "peer is required"},
                status=400,
            )
        try:
            if action == "kick":
                if not room:
                    return web.json_response(
                        {"message": "room is required for kick"},
                        status=400,
                    )
                hub.admin_kick_from_room(peer, room)
            elif action == "ban":
                hub.admin_hub_ban(peer)
            else:
                if not room:
                    return web.json_response(
                        {"message": "room is required for room_ban"},
                        status=400,
                    )
                hub.admin_room_ban(peer, room)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"message": "ok", "hub": hub.to_dict()})

    # serve telephone status
