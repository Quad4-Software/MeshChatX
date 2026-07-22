# SPDX-License-Identifier: 0BSD
"""HTTP routes: archives."""

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


def register_archives_routes(routes, app):

    # serve archived pages
    @routes.get("/api/v1/nomadnet/archives")
    async def get_all_archived_pages(request):
        # get search query and pagination from request
        query = request.query.get("q", "").strip()
        try:
            page = max(1, int(request.query.get("page", 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            limit = max(1, min(100, int(request.query.get("limit", 15))))
        except (ValueError, TypeError):
            limit = 15
        offset = (page - 1) * limit

        # fetch archived pages from database
        all_archives = app.database.misc.get_archived_pages_paginated(
            query=query,
        )
        total_count = len(all_archives)
        total_pages = (total_count + limit - 1) // limit

        # apply pagination
        archives_results = all_archives[offset : offset + limit]

        # return results
        archives = []
        for archive in archives_results:
            # find node name from announces or custom display names
            node_name = app.get_custom_destination_display_name(
                archive["destination_hash"],
            )
            if not node_name:
                db_announce = app.database.announces.get_announce_by_hash(
                    archive["destination_hash"],
                )
                if db_announce and db_announce["aspect"] == "nomadnetwork.node":
                    node_name = parse_nomadnetwork_node_display_name(
                        db_announce["app_data"],
                    )

            archives.append(
                {
                    "id": archive["id"],
                    "destination_hash": archive["destination_hash"],
                    "node_name": node_name or "Unknown Node",
                    "page_path": archive["page_path"],
                    "content": archive["content"],
                    "hash": archive["hash"],
                    "created_at": archive["created_at"],
                },
            )

        return web.json_response(
            {
                "archives": archives,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": total_pages,
                },
            },
        )

    # delete archived pages

    # delete archived pages
    @routes.delete("/api/v1/nomadnet/archives")
    async def delete_archived_pages(request):
        # get archive IDs from body
        data = await request.json()
        ids = data.get("ids", [])

        if not ids:
            return web.json_response(
                {
                    "message": "No archive IDs provided!",
                },
                status=400,
            )

        # delete archives from database
        app.database.misc.delete_archived_pages(ids=ids)

        return web.json_response(
            {
                "message": f"Deleted {len(ids)} archives!",
            },
        )
