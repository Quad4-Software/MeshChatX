# SPDX-License-Identifier: 0BSD
"""HTTP routes: spam."""

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


def register_spam_routes(routes, app):

    # get spam keywords
    @routes.get("/api/v1/spam-keywords")
    async def spam_keywords_get(request):
        keywords = app.database.misc.get_spam_keywords()
        keyword_list = [
            {
                "id": k["id"],
                "keyword": k["keyword"],
                "created_at": k["created_at"],
            }
            for k in keywords
        ]
        return web.json_response(
            {
                "spam_keywords": keyword_list,
            },
        )

    # add spam keyword

    # add spam keyword
    @routes.post("/api/v1/spam-keywords")
    async def spam_keywords_add(request):
        data = await request.json()
        keyword = data.get("keyword", "").strip()
        if not keyword:
            return web.json_response({"error": "Keyword is required"}, status=400)

        try:
            app.database.misc.add_spam_keyword(keyword)
            return web.json_response({"message": "ok"})
        except Exception:
            return web.json_response(
                {"error": "Keyword already exists"},
                status=400,
            )

    # remove spam keyword

    # remove spam keyword
    @routes.delete("/api/v1/spam-keywords/{keyword_id}")
    async def spam_keywords_delete(request):
        keyword_id = request.match_info.get("keyword_id", "")
        try:
            keyword_id = int(keyword_id)
        except (ValueError, TypeError):
            return web.json_response({"error": "Invalid keyword ID"}, status=400)

        try:
            app.database.misc.delete_spam_keyword(keyword_id)
            return web.json_response({"message": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # mark message as spam or not spam

    # mark message as spam or not spam
    @routes.post("/api/v1/lxmf-messages/{hash}/spam")
    async def lxmf_messages_spam(request):
        message_hash = request.match_info.get("hash", "")
        data = await request.json()
        is_spam = data.get("is_spam", False)

        try:
            message = app.database.messages.get_lxmf_message_by_hash(message_hash)
            if message:
                message_data = dict(message)
                message_data["is_spam"] = 1 if is_spam else 0
                app.database.messages.upsert_lxmf_message(message_data)
                return web.json_response({"message": "ok"})
            return web.json_response({"error": "Message not found"}, status=404)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # get offline map metadata
