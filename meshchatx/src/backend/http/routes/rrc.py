# SPDX-License-Identifier: 0BSD
"""HTTP routes: rrc."""

from __future__ import annotations

from meshchatx.src.backend.http.meshchat_names import (  # noqa: F401
    LOGIN_PATH,
    LXMF,
    MAX_EXPORT_TILES,
    RNS,
    SETUP_PATH,
    TRANSPARENT_TILE,
    UTC,
    AsyncUtils,
    GeoValidationError,
    InterfaceConfigParser,
    InterfaceDiscovery,
    InterfaceEditor,
    LxmfAudioField,
    LxmfFileAttachment,
    LxmfFileAttachmentsField,
    LxmfImageField,
    MarkdownRenderer,
    NomadnetFileDownloader,
    NomadnetPageDownloader,
    OutboundHttpBlockedError,
    OverlayExportError,
    OverlaySourceParseError,
    PluginSecurityError,
    ReticulumMeshChat,
    RNProbeHandler,
    Telemeter,
    WSMsgType,
    _is_chaquopy_android,
    _is_loopback_bind_host,
    _request_client_ip,
    aiohttp,
    app_version,
    assert_migration_context_paths,
    asyncio,
    base64,
    bcrypt,
    binascii,
    build_blocklist_export_document,
    build_export_document,
    build_messages_export_bundle,
    cache_stats,
    cancel_inbound_deliveries,
    cast,
    compute_lxmf_conversation_unread_from_latest_row,
    configparser,
    contextlib,
    convert_db_favourite_to_dict,
    convert_db_lxmf_message_to_dict,
    convert_lxmf_message_to_dict,
    convert_nomadnet_field_data_to_map,
    convert_nomadnet_string_data_to_map,
    convert_propagation_node_state_to_string,
    copy,
    datetime,
    describe_port_conflict,
    detect_image_format_from_magic,
    ensure_outbound_http_allowed,
    ensure_session_csrf_token,
    filter_announced_dicts_by_search_query,
    fresh_storage_at_target,
    get_cached_active_link,
    get_file_path,
    get_session,
    get_trusted_proxy_cidrs,
    gif_utils,
    i2p_support,
    import_messages_export_bundle,
    io,
    is_mbtiles_filename,
    is_path_within_dir,
    is_port_in_use,
    is_user_facing_lxmf_payload,
    json,
    list_host_network_interfaces,
    list_inbound_deliveries,
    list_ports,
    load_app_security_settings,
    logger,
    logging,
    lxmf_sidebar_preview_for_conversation_latest_row,
    memory_log_handler,
    message_fields_have_attachments,
    migrate_legacy_to_target,
    mime_for_image_type,
    normalize_identity_storage_hash,
    normalize_lxmf_sieve_filters,
    normalize_message_blocklist,
    os,
    parse_bool_query_param,
    parse_import_document,
    parse_lxmf_display_name,
    parse_lxmf_propagation_node_app_data,
    parse_lxmf_sieve_filters_json,
    parse_lxmf_stamp_cost,
    parse_message_blocklist_json,
    parse_nomadnetwork_node_display_name,
    platform,
    privacy_mode_enabled,
    psutil,
    purge_messages_before_cutoff,
    re,
    resolve_message_age_cutoff,
    reticulum_pathfinding,
    rotate_session_csrf_token,
    rrc_protocol,
    safe_path_under_dir,
    sanitize_sticker_emoji,
    sanitize_sticker_name,
    sanitize_websocket_config_update,
    save_app_security_settings,
    secrets,
    shutil,
    sqlite3,
    sticker_pack_utils,
    sys,
    tempfile,
    threading,
    time,
    traceback,
    user_agent_hash,
    validate_export_document,
    web,
    websocket_type_requires_auth,
    zipfile,
)


def register_rrc_routes(routes, app):

    # Reticulum Relay Chat
    RRC_ROOM_MESSAGES_DEFAULT_LIMIT = 200
    RRC_ROOM_MESSAGES_MAX_LIMIT = 1000

    def _rrc_require_manager():
        manager = app.rrc_manager
        if manager is None:
            return None, web.json_response(
                {"message": "Relay chat is not available"},
                status=503,
            )
        return manager, None

    def _rrc_require_hub(hub_hash_hex):
        manager, error = _rrc_require_manager()
        if error is not None:
            return None, None, error
        hub = manager.find_hub_by_hex(hub_hash_hex)
        if hub is None:
            return (
                manager,
                None,
                web.json_response(
                    {"message": "Hub not found"},
                    status=404,
                ),
            )
        return manager, hub, None

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
    def _rrc_server_require_manager():
        manager = app.rrc_server_manager
        if manager is None:
            return None, web.json_response(
                {"message": "Relay chat hosting is not available"},
                status=503,
            )
        return manager, None

    def _rrc_server_require_hub(hub_id):
        manager, error = _rrc_server_require_manager()
        if error is not None:
            return None, None, error
        hub = manager.find_hub(hub_id)
        if hub is None:
            return (
                manager,
                None,
                web.json_response(
                    {"message": "Hub not found"},
                    status=404,
                ),
            )
        return manager, hub, None

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
