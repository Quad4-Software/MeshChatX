# SPDX-License-Identifier: 0BSD
"""HTTP routes: telemetry."""

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


def register_telemetry_routes(routes, app):

    # get latest telemetry for all peers
    @routes.get("/api/v1/telemetry/peers")
    async def get_all_latest_telemetry(request):
        results = app.database.telemetry.get_all_latest_telemetry()
        telemetry_list = []
        for r in results:
            unpacked = Telemeter.from_packed(r["data"])
            telemetry_list.append(
                {
                    "destination_hash": r["destination_hash"],
                    "timestamp": r["timestamp"],
                    "telemetry": unpacked,
                    "physical_link": json.loads(r["physical_link"])
                    if r["physical_link"]
                    else None,
                    "updated_at": r["updated_at"],
                    "is_tracking": app.database.telemetry.is_tracking(
                        r["destination_hash"],
                    ),
                },
            )
        return web.json_response({"telemetry": telemetry_list})

    @routes.get("/api/v1/telemetry/trusted-peers")
    async def telemetry_trusted_peers_get(request):
        # get all contacts that are telemetry trusted
        contacts = app.database.provider.fetchall(
            "SELECT * FROM contacts WHERE is_telemetry_trusted = 1 ORDER BY name ASC",
        )
        return web.json_response({"trusted_peers": [dict(c) for c in contacts]})

    # toggle telemetry tracking for a destination

    # toggle telemetry tracking for a destination
    @routes.post("/api/v1/telemetry/tracking/{destination_hash}/toggle")
    async def toggle_telemetry_tracking(request):
        destination_hash = request.match_info["destination_hash"]
        data = await request.json()
        is_tracking = data.get("is_tracking")

        new_status = app.database.telemetry.toggle_tracking(
            destination_hash,
            is_tracking,
        )
        return web.json_response({"status": "ok", "is_tracking": new_status})

    # get all tracked peers

    # get all tracked peers
    @routes.get("/api/v1/telemetry/tracking")
    async def get_tracked_peers(request):
        results = app.database.telemetry.get_tracked_peers()
        return web.json_response({"tracked_peers": results})

    # get telemetry history for a destination

    # get telemetry history for a destination
    @routes.get("/api/v1/telemetry/history/{destination_hash}")
    async def get_telemetry_history(request):
        destination_hash = request.match_info.get("destination_hash")
        limit = int(request.query.get("limit", 100))
        offset = int(request.query.get("offset", 0))

        results = app.database.telemetry.get_telemetry_history(
            destination_hash,
            limit,
            offset,
        )
        telemetry_list = []
        for r in results:
            unpacked = Telemeter.from_packed(r["data"])
            telemetry_list.append(
                {
                    "destination_hash": r["destination_hash"],
                    "timestamp": r["timestamp"],
                    "telemetry": unpacked,
                    "physical_link": json.loads(r["physical_link"])
                    if r["physical_link"]
                    else None,
                    "updated_at": r["updated_at"],
                },
            )
        return web.json_response({"telemetry": telemetry_list})

    # get latest telemetry for a destination

    # get latest telemetry for a destination
    @routes.get("/api/v1/telemetry/latest/{destination_hash}")
    async def get_latest_telemetry(request):
        destination_hash = request.match_info.get("destination_hash")
        r = app.database.telemetry.get_latest_telemetry(destination_hash)
        if not r:
            return web.json_response({"error": "No telemetry found"}, status=404)

        unpacked = Telemeter.from_packed(r["data"])
        return web.json_response(
            {
                "destination_hash": r["destination_hash"],
                "timestamp": r["timestamp"],
                "telemetry": unpacked,
                "physical_link": json.loads(r["physical_link"])
                if r["physical_link"]
                else None,
                "updated_at": r["updated_at"],
            },
        )

    # upload offline map
