# SPDX-License-Identifier: 0BSD
"""HTTP routes: docs."""

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


def register_docs_routes(routes, app):

    # get docs status
    @routes.get("/api/v1/docs/status")
    async def docs_status(request):
        return web.json_response(app.docs_manager.get_status())

    # upload docs zip

    # upload docs zip
    @routes.post("/api/v1/docs/upload")
    async def docs_upload(request):
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field.name != "file":
                return web.json_response(
                    {"error": "No file field in multipart request"},
                    status=400,
                )

            version = request.query.get("version")
            if not version:
                # use timestamp if no version provided
                version = f"upload-{int(time.time())}"

            zip_data = await field.read()
            success = app.docs_manager.upload_zip(zip_data, version)
            return web.json_response({"success": success, "version": version})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # switch docs version

    # switch docs version
    @routes.post("/api/v1/docs/switch")
    async def docs_switch(request):
        try:
            data = await request.json()
            version = data.get("version")
            if not version:
                return web.json_response(
                    {"error": "No version provided"},
                    status=400,
                )

            success = app.docs_manager.switch_version(version)
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # delete docs version

    # delete docs version
    @routes.delete("/api/v1/docs/version/{version}")
    async def docs_delete_version(request):
        try:
            version = request.match_info.get("version")
            if not version:
                return web.json_response(
                    {"error": "No version provided"},
                    status=400,
                )

            success = app.docs_manager.delete_version(version)
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # clear reticulum docs

    # clear reticulum docs
    @routes.delete("/api/v1/maintenance/docs/reticulum")
    async def docs_clear(request):
        try:
            success = app.docs_manager.clear_reticulum_docs()
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # search docs

    # search docs
    @routes.get("/api/v1/docs/search")
    async def docs_search(request):
        query = request.query.get("q", "")
        lang = request.query.get("lang", "en")
        results = app.docs_manager.search(query, lang)
        return web.json_response({"results": results})

    # get meshchatx docs list

    # get meshchatx docs list
    @routes.get("/api/v1/meshchatx-docs/list")
    async def meshchatx_docs_list(request):
        lang = request.query.get("lang", "en")
        return web.json_response(app.docs_manager.get_meshchatx_docs_list(lang))

    # get meshchatx doc content

    # get meshchatx doc content
    @routes.get("/api/v1/meshchatx-docs/content")
    async def meshchatx_doc_content(request):
        path = request.query.get("path")
        if not path:
            return web.json_response({"error": "No path provided"}, status=400)
        if not app.docs_manager._is_safe_doc_path(path):
            return web.json_response({"error": "Invalid path"}, status=400)

        content = app.docs_manager.get_doc_content(path)
        if not content:
            return web.json_response({"error": "Document not found"}, status=404)

        return web.json_response(content)

    # repository server (wheels + uploads, and optional in-process plain HTTP)

    # export docs
    @routes.get("/api/v1/docs/export")
    async def docs_export(request):
        try:
            zip_data = app.docs_manager.export_docs()
            filename = (
                f"meshchatx_docs_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.zip"
            )
            return web.Response(
                body=zip_data,
                content_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # export the active Reticulum manual in a layout the upload route accepts,
    # so users can share their bundled or customised manual with another peer.

    # export the active Reticulum manual in a layout the upload route accepts,
    # so users can share their bundled or customised manual with another peer.
    @routes.get("/api/v1/docs/export/reticulum")
    async def reticulum_docs_export(request):
        try:
            zip_data = app.docs_manager.export_reticulum_docs()
            if zip_data is None:
                return web.json_response(
                    {"error": "No Reticulum manual available to export"},
                    status=404,
                )
            version = app.docs_manager.get_current_version() or "manual"
            safe_version = re.sub(r"[^A-Za-z0-9._-]+", "_", str(version))
            filename = (
                "reticulum_manual_"
                f"{safe_version}_"
                f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.zip"
            )
            return web.Response(
                body=zip_data,
                content_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
