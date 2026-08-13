# SPDX-License-Identifier: 0BSD
"""HTTP routes: blocklist."""

from __future__ import annotations


from meshchatx.src.backend.http.meshchat_names import (  # noqa: F401
    GeoValidationError,
    OutboundHttpBlockedError,
    OverlayExportError,
    OverlaySourceParseError,
    PluginSecurityError,
    AsyncUtils,
    InterfaceConfigParser,
    InterfaceDiscovery,
    InterfaceEditor,
    LOGIN_PATH,
    LXMF,
    LxmfAudioField,
    LxmfFileAttachment,
    LxmfFileAttachmentsField,
    LxmfImageField,
    MAX_EXPORT_TILES,
    MarkdownRenderer,
    NomadnetFileDownloader,
    NomadnetPageDownloader,
    RNProbeHandler,
    RNS,
    ReticulumMeshChat,
    SETUP_PATH,
    TRANSPARENT_TILE,
    Telemeter,
    UTC,
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


def register_blocklist_routes(routes, app):

    @routes.get("/api/v1/lxmf/message-blocklist")
    async def lxmf_message_blocklist_get(request):
        raw = app.config.message_blocklist_json.get()
        return web.json_response(
            {
                "enabled": app.config.message_blocklist_enabled.get(),
                "blocklist": parse_message_blocklist_json(raw),
            },
        )

    @routes.put("/api/v1/lxmf/message-blocklist")
    async def lxmf_message_blocklist_put(request):
        data = await request.json()
        blocklist_in = data.get("blocklist")
        if not isinstance(blocklist_in, dict):
            return web.json_response(
                {"message": "blocklist must be an object"},
                status=400,
            )
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

    @routes.get("/api/v1/lxmf/message-blocklist/export")
    async def lxmf_message_blocklist_export(request):
        raw = app.config.message_blocklist_json.get()
        blocklist = parse_message_blocklist_json(raw)
        return web.json_response(build_blocklist_export_document(blocklist))

    @routes.post("/api/v1/lxmf/message-blocklist/import")
    async def lxmf_message_blocklist_import(request):
        data = await request.json()
        document = data.get("document")
        if not isinstance(document, dict):
            return web.json_response(
                {"message": "document must be an object"},
                status=400,
            )
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
            return web.json_response(
                {"message": "Invalid blocklist document"},
                status=400,
            )
        app.config.message_blocklist_json.set(json.dumps(imported))
        return web.json_response(
            {
                "enabled": app.config.message_blocklist_enabled.get(),
                "blocklist": imported,
            },
        )

    # get blocked destinations
    @routes.get("/api/v1/blocked-destinations")
    async def blocked_destinations_get(request):
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

    # add blocked destination

    # add blocked destination
    @routes.post("/api/v1/blocked-destinations")
    async def blocked_destinations_add(request):
        data = await request.json()
        destination_hash = data.get("destination_hash", "")
        if not destination_hash or len(destination_hash) != 32:
            return web.json_response(
                {"error": "Invalid destination hash"},
                status=400,
            )

        try:
            app.banish_lxmf_peer(destination_hash)
        except Exception:
            return web.json_response(
                {"error": "Failed to banish destination"},
                status=400,
            )

        return web.json_response({"message": "ok"})

    # remove blocked destination

    # remove blocked destination
    @routes.delete("/api/v1/blocked-destinations/{destination_hash}")
    async def blocked_destinations_delete(request):
        destination_hash = request.match_info.get("destination_hash", "")
        if not destination_hash or len(destination_hash) != 32:
            return web.json_response(
                {"error": "Invalid destination hash"},
                status=400,
            )

        try:
            app.lift_lxmf_peer_banishment(destination_hash)
            return web.json_response({"message": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.get("/api/v1/reticulum/blackhole")
    async def reticulum_blackhole_get(request):
        if not hasattr(app, "reticulum") or not app.reticulum:
            return web.json_response(
                {"error": "Reticulum not initialized"},
                status=503,
            )

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
            return web.json_response({"error": str(e)}, status=500)

    # get spam keywords
