# SPDX-License-Identifier: 0BSD
"""HTTP routes: websocket_upgrade."""

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


from meshchatx.src.backend.websocket_config_guard import websocket_origin_allowed


def _reject_forbidden_ws_origin(app, request):
    if websocket_origin_allowed(request, get_trusted_proxy_cidrs(app.storage_dir)):
        return None
    return web.json_response({"error": "Forbidden origin"}, status=403)


def register_websocket_upgrade_routes(routes, app):

    # handle websocket clients
    @routes.get("/ws")
    async def ws(request):
        forbidden = _reject_forbidden_ws_origin(app, request)
        if forbidden is not None:
            return forbidden
        max_clients = int(getattr(app, "max_websocket_clients", 64) or 64)
        if len(app.websocket_clients) >= max_clients:
            return web.json_response(
                {"error": "Too many websocket clients"},
                status=503,
            )

        # prepare websocket response
        websocket_response = web.WebSocketResponse(
            # set max message size accepted by server to 50 megabytes
            max_msg_size=50 * 1024 * 1024,
        )
        await websocket_response.prepare(request)
        # aiohttp WebSocketResponse does not expose .request, so keep it for
        # session checks on authenticated mutators (nomadnet downloads, etc).
        websocket_response._meshchatx_request = request

        # add client to connected clients list
        app.websocket_clients.append(websocket_response)
        session = app.active_sessions.add(
            ip=request.remote,
            user_agent=request.headers.get("User-Agent"),
        )
        websocket_response._meshchatx_session_id = session["id"]

        # send config to all clients
        await app.send_config_to_websocket_clients()
        await app.send_active_sessions_to_websocket_clients()

        # handle websocket messages until disconnected
        async for msg in websocket_response:
            message = cast("WSMessage", msg)
            if message.type == WSMsgType.TEXT:
                try:
                    data = json.loads(message.data)
                    await app.on_websocket_data_received(websocket_response, data)
                except Exception as e:
                    # ignore errors while handling message
                    print("failed to process client message")
                    print(e)
            elif message.type == WSMsgType.ERROR:
                # ignore errors while handling message
                print(f"ws connection error {websocket_response.exception()}")

        # websocket closed
        try:
            app.websocket_clients.remove(websocket_response)
        except ValueError:
            pass
        app._detach_active_session(websocket_response)
        app._cancel_rns_link_tasks_for_client(websocket_response)
        await app.send_active_sessions_to_websocket_clients()

        return websocket_response

    @routes.get("/ws/telephone/audio")
    async def telephone_audio_ws(request):
        forbidden = _reject_forbidden_ws_origin(app, request)
        if forbidden is not None:
            return forbidden
        websocket_response = web.WebSocketResponse(
            # Cap well above a normal PCM frame (tens of KB) but far below prior 5 MiB.
            max_msg_size=256 * 1024,
        )
        await websocket_response.prepare(request)

        if getattr(app, "demo_mode", False):
            await websocket_response.send_str(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Demo mode is read-only",
                        "code": "demo_readonly",
                    },
                ),
            )
            await websocket_response.close()
            return websocket_response

        # Chaquopy Android and headless/web deployments have no usable LXST
        # host audio device, so always allow the websocket bridge.
        web_audio_allowed = (
            app.web_audio_bridge.config_enabled() or app.web_audio_required()
        )
        if not web_audio_allowed:
            await websocket_response.send_str(
                json.dumps(
                    {"type": "error", "message": "Web audio is disabled in config"},
                ),
            )
            await websocket_response.close()
            return websocket_response

        await app.web_audio_bridge.send_status(websocket_response)
        attached = app.web_audio_bridge.attach_client(websocket_response)
        if not attached:
            await websocket_response.send_str(
                json.dumps(
                    {"type": "error", "message": "No active call to attach"},
                ),
            )

        async for msg in websocket_response:
            message = cast("WSMessage", msg)
            if message.type == WSMsgType.BINARY:
                # Only accept PCM after a successful attach for this socket.
                if websocket_response in app.web_audio_bridge.clients:
                    app.web_audio_bridge.push_client_frame(message.data)
            elif message.type == WSMsgType.TEXT:
                try:
                    data = json.loads(message.data)
                    if data.get("type") == "attach":
                        app.web_audio_bridge.attach_client(websocket_response)
                    elif data.get("type") == "ping":
                        await websocket_response.send_str(
                            json.dumps({"type": "pong"}),
                        )
                except Exception as e:
                    logging.exception(
                        f"Error processing websocket text message: {e}",
                    )
            elif message.type == WSMsgType.ERROR:
                print(f"telephone audio ws error {websocket_response.exception()}")

        app.web_audio_bridge.detach_client(websocket_response)
        return websocket_response
