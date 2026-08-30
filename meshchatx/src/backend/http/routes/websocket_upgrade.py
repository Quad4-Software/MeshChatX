# SPDX-License-Identifier: 0BSD
"""HTTP routes: websocket_upgrade."""

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
from meshchatx.src.backend.websocket_config_guard import websocket_origin_allowed
from meshchatx.src.backend.websocket_runtime import (
    WS_RATE_ABUSE_STRIKES,
    WS_RATE_RETRY_AFTER_SEC,
    client_is_idle,
    get_client_bucket,
    init_client_runtime,
    message_rate_cost,
    send_ws_error,
    touch_client_activity,
    websocket_origin_policy_allows,
)


async def _reject_forbidden_ws_session(app, request):
    """Defense in depth: identity-bound session when password auth is on."""
    if not getattr(app, "auth_enabled", False):
        return None
    try:
        session = await get_session(request)
    except Exception:
        return web.json_response({"error": "Authentication required"}, status=401)
    identity_hash = None
    identity = getattr(app, "identity", None)
    if identity is not None and getattr(identity, "hash", None) is not None:
        identity_hash = identity.hash.hex()
    if not (
        session.get("authenticated", False)
        and identity_hash
        and session.get("identity_hash") == identity_hash
    ):
        return web.json_response({"error": "Authentication required"}, status=401)
    return None


def _reject_forbidden_ws_origin(app, request):
    listen_host = getattr(app, "listen_host", None)
    auth_enabled = bool(getattr(app, "auth_enabled", False))
    if websocket_origin_policy_allows(
        request,
        listen_host=listen_host,
        auth_enabled=auth_enabled,
        trusted_proxy_cidrs=get_trusted_proxy_cidrs(app.storage_dir),
        origin_allowed_fn=websocket_origin_allowed,
        is_loopback_fn=_is_loopback_bind_host,
    ):
        return None
    return web.json_response({"error": "Forbidden origin"}, status=403)


def register_websocket_upgrade_routes(routes, app):
    # handle websocket clients
    @routes.get("/ws")
    async def ws(request):
        forbidden = _reject_forbidden_ws_origin(app, request)
        if forbidden is not None:
            return forbidden
        forbidden_session = await _reject_forbidden_ws_session(app, request)
        if forbidden_session is not None:
            return forbidden_session
        max_clients = int(getattr(app, "max_websocket_clients", 64) or 64)
        if len(app.websocket_clients) >= max_clients:
            return web.json_response(
                {"error": "Too many websocket clients"},
                status=503,
            )

        # Control + chunked Nomad frames. Whole-file success under the Nomad
        # app cap still fits (10 MiB raw + base64) under 50 MiB legacy until
        # Phase 4 fully switches large transfers to chunks only.
        max_msg = int(
            getattr(app, "websocket_max_msg_size", None) or (50 * 1024 * 1024),
        )
        websocket_response = web.WebSocketResponse(
            max_msg_size=max_msg,
        )
        await websocket_response.prepare(request)
        # aiohttp WebSocketResponse does not expose .request, so keep it for
        # session checks on authenticated mutators (nomadnet downloads, etc).
        websocket_response._meshchatx_request = request
        init_client_runtime(websocket_response)

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
                touch_client_activity(websocket_response)
                try:
                    data = json.loads(message.data)
                except Exception as e:
                    print("failed to process client message")
                    print(e)
                    await send_ws_error(
                        websocket_response,
                        message="Invalid JSON",
                        code="invalid_json",
                    )
                    continue
                counters = getattr(app, "ws_counters", None)
                if counters is not None:
                    counters.msgs_in += 1
                bucket = get_client_bucket(websocket_response)
                msg_type = data.get("type") if isinstance(data, dict) else None
                cost = message_rate_cost(
                    msg_type if isinstance(msg_type, str) else None
                )
                if not bucket.consume(cost):
                    if counters is not None:
                        counters.rate_limit_hits += 1
                    strikes = int(
                        getattr(websocket_response, "_meshchatx_rate_strikes", 0) or 0,
                    )
                    strikes += 1
                    websocket_response._meshchatx_rate_strikes = strikes
                    await send_ws_error(
                        websocket_response,
                        message="Rate limit exceeded",
                        code="rate_limited",
                        request_id=data.get("request_id")
                        if isinstance(data, dict)
                        else None,
                        retry_after=WS_RATE_RETRY_AFTER_SEC,
                    )
                    if strikes >= WS_RATE_ABUSE_STRIKES:
                        await websocket_response.close()
                        break
                    continue
                websocket_response._meshchatx_rate_strikes = 0
                try:
                    await app.on_websocket_data_received(websocket_response, data)
                except Exception as e:
                    print("failed to process client message")
                    print(e)
                    await send_ws_error(
                        websocket_response,
                        message="Handler failed",
                        code="handler_failed",
                        request_id=data.get("request_id")
                        if isinstance(data, dict)
                        else None,
                    )
            elif message.type == WSMsgType.BINARY:
                touch_client_activity(websocket_response)
                try:
                    await app.on_websocket_binary_received(
                        websocket_response,
                        message.data,
                    )
                except Exception as e:
                    print("failed to process binary client message")
                    print(e)
            elif message.type == WSMsgType.ERROR:
                print(f"ws connection error {websocket_response.exception()}")

            if client_is_idle(websocket_response):
                counters = getattr(app, "ws_counters", None)
                if counters is not None:
                    counters.idle_closes += 1
                try:
                    await websocket_response.close()
                except Exception:
                    pass
                break

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
        forbidden_session = await _reject_forbidden_ws_session(app, request)
        if forbidden_session is not None:
            return forbidden_session
        websocket_response = web.WebSocketResponse(
            # Cap well above a normal PCM frame (tens of KB) but far below prior 5 MiB.
            max_msg_size=256 * 1024,
        )
        await websocket_response.prepare(request)
        init_client_runtime(websocket_response)

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
            touch_client_activity(websocket_response)
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
