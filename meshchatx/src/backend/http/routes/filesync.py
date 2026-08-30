# SPDX-License-Identifier: 0BSD
"""HTTP routes: filesync."""

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


def register_filesync_routes(routes, app):

    # --- RNS FileSync ---

    def _filesync_require_handler():
        return app._require_rns_tool_handler(
            app.rns_filesync_handler,
            "RNS FileSync",
        )

    @routes.get("/api/v1/filesync/status")
    async def filesync_status(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response(app.rns_filesync_handler.get_status())

    @routes.post("/api/v1/filesync/start")
    async def filesync_start(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = {}
        with contextlib.suppress(Exception):
            data = await request.json()
        if not isinstance(data, dict):
            data = {}
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.start,
                sync_directory=data.get("sync_directory"),
                monitor=data.get("monitor"),
                announce_interval=data.get("announce_interval"),
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "failed to start")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/stop")
    async def filesync_stop(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            result = await asyncio.to_thread(app.rns_filesync_handler.stop)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        return web.json_response(result)

    @routes.get("/api/v1/filesync/peers")
    async def filesync_peers(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response({"peers": app.rns_filesync_handler.list_peers()})

    @routes.get("/api/v1/filesync/files")
    async def filesync_files(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response({"files": app.rns_filesync_handler.list_files()})

    @routes.get("/api/v1/filesync/tree")
    async def filesync_tree(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        path = request.rel_url.query.get("path")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.list_tree,
                path,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "list tree failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/mkdir")
    async def filesync_mkdir(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.manager_mkdir,
                data.get("path", ""),
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "mkdir failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/upload")
    async def filesync_upload(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        subdir = None
        filename = None
        file_data = None
        try:
            reader = await request.multipart()
            while True:
                field = await reader.next()
                if field is None:
                    break
                name = field.name or ""
                if name == "path":
                    subdir = (await field.text()).strip() or None
                elif name == "file":
                    filename = field.filename or "upload"
                    file_data = await field.read()
                else:
                    with contextlib.suppress(Exception):
                        await field.read()
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid upload request: {e}"},
                status=400,
            )
        if file_data is None:
            return web.json_response({"message": "No file uploaded"}, status=400)
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.manager_upload,
                filename=filename,
                data=file_data,
                subdir=subdir,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "upload failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.delete("/api/v1/filesync/entry")
    async def filesync_entry_delete(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = {}
        with contextlib.suppress(Exception):
            data = await request.json()
        if not isinstance(data, dict):
            data = {}
        path = data.get("path", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.manager_delete,
                path,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "delete failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.get("/api/v1/filesync/content")
    async def filesync_content(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        path = request.rel_url.query.get("path", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.manager_content,
                path,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "content failed")},
                status=400,
            )
        abspath = result.get("abspath")
        filename = result.get("filename") or "download"
        if not abspath or not os.path.isfile(abspath):
            return web.json_response({"message": "file not found"}, status=404)
        safe_name = (
            os.path.basename(str(filename))
            .replace('"', "_")
            .replace("\r", "")
            .replace("\n", "")
            .replace("\x00", "")
        ) or "download"
        return web.FileResponse(
            abspath,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}"',
            },
        )

    @routes.get("/api/v1/filesync/directories")
    async def filesync_directories(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        path = request.rel_url.query.get("path")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.list_directories,
                path,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "list directories failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/directories")
    async def filesync_directories_create(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.create_directory,
                data.get("parent"),
                data.get("name", ""),
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "create directory failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/connect")
    async def filesync_connect(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        identity_hash = data.get("identity_hash", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.connect_peer,
                identity_hash,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "connect failed"), **result},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/disconnect")
    async def filesync_disconnect(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        peer_id = data.get("peer_id", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.disconnect_peer,
                peer_id,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "disconnect failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/announce")
    async def filesync_announce(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            result = await asyncio.to_thread(app.rns_filesync_handler.announce_now)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "announce failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/browse")
    async def filesync_browse(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        peer_id = data.get("peer_id", "")
        timeout = data.get("timeout", 10.0)
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.browse_peer,
                peer_id,
                timeout,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {
                    "message": result.get("error", "browse failed"),
                    "files": result.get("files", []),
                },
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/download")
    async def filesync_download(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        peer_id = data.get("peer_id", "")
        path = data.get("path", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.download_file,
                peer_id,
                path,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "download failed"), **result},
                status=400,
            )
        return web.json_response(result)

    @routes.get("/api/v1/filesync/acl")
    async def filesync_acl_get(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response(app.rns_filesync_handler.get_acl())

    @routes.post("/api/v1/filesync/acl")
    async def filesync_acl_post(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        perms = data.get("perms")
        if perms is not None and not isinstance(perms, list):
            return web.json_response(
                {"message": "perms must be a list"},
                status=400,
            )
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.update_acl,
                identity_hash=data.get("identity_hash"),
                perms=perms,
                enforce=data.get("enforce"),
                rules_text=data.get("rules_text"),
                replace=bool(data.get("replace", False)),
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "acl update failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.patch("/api/v1/filesync/settings")
    async def filesync_settings(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.update_settings,
                sync_directory=data.get("sync_directory"),
                monitor=data.get("monitor"),
                announce_interval=data.get("announce_interval"),
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "settings update failed")},
                status=400,
            )
        return web.json_response(result)

    # --- Plugin API ---
