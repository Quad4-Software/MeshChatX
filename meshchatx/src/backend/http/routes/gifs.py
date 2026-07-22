# SPDX-License-Identifier: 0BSD
"""HTTP routes: gifs."""

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


def register_gifs_routes(routes, app):

    @routes.get("/api/v1/gifs")
    async def gifs_list(request):
        identity_hash = app.identity.hash.hex()
        rows = app.database.gifs.list_for_identity(identity_hash)
        return web.json_response({"gifs": [dict(r) for r in rows]})

    @routes.post("/api/v1/gifs")
    async def gifs_create(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        image_b64 = data.get("image_bytes")
        if not isinstance(image_b64, str) or not image_b64.strip():
            return web.json_response({"error": "missing_image_bytes"}, status=400)
        try:
            raw = base64.b64decode(image_b64.strip(), validate=True)
        except (ValueError, TypeError):
            return web.json_response({"error": "invalid_base64"}, status=400)
        name = gif_utils.sanitize_gif_name(data.get("name"))
        image_type = data.get("image_type")
        src = data.get("source_message_hash")
        src = src if isinstance(src, str) else None
        try:
            row = app.database.gifs.insert(
                identity_hash,
                name,
                image_type,
                raw,
                src,
            )
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        if row is None:
            return web.json_response({"error": "duplicate_gif"}, status=409)
        return web.json_response({"gif": row})

    @routes.delete("/api/v1/gifs/{gif_id}")
    async def gifs_delete(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        ok = app.database.gifs.delete(gif_id, identity_hash)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"message": "deleted"})

    @routes.patch("/api/v1/gifs/{gif_id}")
    async def gifs_patch(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        if "name" not in data:
            return web.json_response({"error": "missing_name"}, status=400)
        name = gif_utils.sanitize_gif_name(data.get("name"))
        ok = app.database.gifs.update_name(gif_id, identity_hash, name)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"message": "updated"})

    @routes.get("/api/v1/gifs/{gif_id}/image")
    async def gifs_get_image(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        row = app.database.gifs.get_row(gif_id, identity_hash)
        if row is None:
            return web.json_response({"error": "not_found"}, status=404)
        ct = gif_utils.mime_for_image_type(row["image_type"])
        return web.Response(body=row["image_blob"], content_type=ct)

    @routes.post("/api/v1/gifs/{gif_id}/use")
    async def gifs_record_usage(request):
        identity_hash = app.identity.hash.hex()
        gif_id = int(request.match_info.get("gif_id", "0"))
        ok = app.database.gifs.record_usage(gif_id, identity_hash)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"message": "recorded"})

    @routes.get("/api/v1/gifs/export")
    async def gifs_export(request):
        identity_hash = app.identity.hash.hex()
        payloads = app.database.gifs.export_payloads_for_identity(identity_hash)
        doc = gif_utils.build_export_document(
            payloads,
            datetime.now(UTC).isoformat(),
        )
        return web.json_response(doc)

    @routes.post("/api/v1/gifs/import")
    async def gifs_import(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        replace = bool(data.get("replace_duplicates", False))
        try:
            items = gif_utils.validate_export_document(data)
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        result = app.database.gifs.import_payloads(
            identity_hash,
            items,
            replace_duplicates=replace,
        )
        return web.json_response(result)

    # get latest telemetry for all peers
