# SPDX-License-Identifier: 0BSD
"""HTTP routes: shell."""

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


def register_shell_routes(routes, app):
    @routes.get("/")
    async def index(request):
        index_path = app.get_public_path("index.html")
        if not os.path.exists(index_path):
            return web.Response(
                text="""
                    <html>
                        <head><title>MeshChatX - Frontend Missing</title></head>
                        <body style="font-family: sans-serif; padding: 2rem; line-height: 1.5; background: #0f172a; color: #f8fafc;">
                            <h1 style="color: #38bdf8;">Frontend Missing</h1>
                            <p>The MeshChatX web interface files were not found.</p>
                            <p>If you are running from source, you must build the frontend first:</p>
                            <pre style="background: #1e293b; padding: 1rem; border-radius: 4px; color: #e2e8f0; border: 1px solid #334155;">pnpm install && pnpm run build-frontend</pre>
                            <p>For more information, see the <a href="https://github.com/Quad4-Software/MeshChatX" style="color: #38bdf8;">README</a>.</p>
                        </body>
                    </html>
                    """,
                content_type="text/html",
                status=500,
            )
        return web.FileResponse(
            path=index_path,
            headers={
                # don't allow browser to store page in cache, otherwise new app versions may get stale ui
                "Cache-Control": "no-cache, no-store",
            },
        )

    # allow serving manifest.json and service-worker.js directly at root

    # allow serving manifest.json and service-worker.js directly at root
    @routes.get("/manifest.json")
    async def manifest(request):
        return web.FileResponse(app.get_public_path("manifest.json"))

    @routes.get("/service-worker.js")
    async def service_worker(request):
        return web.FileResponse(app.get_public_path("service-worker.js"))

    @routes.get("/call.html")
    async def call_html_redirect(request):
        return web.HTTPFound("/#/popout/call")

    # serve debug logs
