# SPDX-License-Identifier: 0BSD
"""HTTP routes: repository_server."""

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


def register_repository_server_routes(routes, app):

    # repository server (wheels + uploads, and optional in-process plain HTTP)
    @routes.get("/api/v1/repository-server/status")
    async def repository_server_status(_request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        return web.json_response(mgr.status())

    @routes.get("/api/v1/repository-server/list")
    async def repository_server_list(_request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        return web.json_response(mgr.list_entries())

    @routes.post("/api/v1/repository-server/upload")
    async def repository_server_upload(request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        try:
            reader = await request.multipart()
            field = await reader.next()
            if not field or field.name != "file":
                return web.json_response(
                    {"error": "No file field in multipart request"},
                    status=400,
                )
            filename = field.filename or "upload.bin"
            data = await field.read()
            ok, err = mgr.save_upload(filename, data)
            if not ok:
                return web.json_response(
                    {"success": False, "error": err},
                    status=400,
                )
            return web.json_response({"success": True})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.delete("/api/v1/repository-server/upload/{name}")
    async def repository_server_delete_upload(request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        name = request.match_info.get("name") or ""
        ok, err = mgr.delete_upload(name)
        if not ok:
            code = 404 if err == "not_found" else 400
            return web.json_response({"success": False, "error": err}, status=code)
        return web.json_response({"success": True})

    @routes.post("/api/v1/repository-server/refresh-bundled")
    async def repository_server_refresh_bundled(_request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        try:
            app._require_outbound_http("repository bundled wheel refresh")
            result = await asyncio.to_thread(mgr.refresh_bundled_wheels)
            return web.json_response(result)
        except OutboundHttpBlockedError as e:
            return web.json_response({"error": str(e)}, status=403)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.post("/api/v1/repository-server/http/start")
    async def repository_server_http_start(request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        try:
            data = await request.json()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        host = data.get("host")
        port = data.get("port")
        port_int = None
        if port is not None:
            try:
                port_int = int(port)
            except (TypeError, ValueError):
                return web.json_response(
                    {"ok": False, "error": "invalid_port"},
                    status=400,
                )
        try:
            result = await asyncio.to_thread(
                mgr.start_http_server,
                str(host).strip() if host is not None else None,
                port_int,
            )
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.post("/api/v1/repository-server/http/stop")
    async def repository_server_http_stop(_request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        try:
            result = await asyncio.to_thread(mgr.stop_http_server)
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.post("/api/v1/repository-server/http/restart")
    async def repository_server_http_restart(request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        try:
            data = await request.json()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        host = data.get("host")
        port = data.get("port")
        port_int = None
        if port is not None:
            try:
                port_int = int(port)
            except (TypeError, ValueError):
                return web.json_response(
                    {"ok": False, "error": "invalid_port"},
                    status=400,
                )
        try:
            result = await asyncio.to_thread(
                mgr.restart_http_server,
                str(host).strip() if host is not None else None,
                port_int,
            )
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # export docs
