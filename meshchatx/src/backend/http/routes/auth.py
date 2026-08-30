# SPDX-License-Identifier: 0BSD
"""HTTP routes: auth."""

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


def register_auth_routes(routes, app):

    @routes.get("/api/v1/auth/altcha/challenge")
    async def auth_altcha_challenge(request):
        if not app.altcha_enabled:
            return web.json_response({"error": "ALTCHA is not enabled"}, status=404)
        try:
            from meshchatx.src.backend.altcha_auth import create_altcha_challenge_dict

            challenge = create_altcha_challenge_dict()
        except RuntimeError as exc:
            return web.json_response({"error": str(exc)}, status=503)
        return web.json_response(challenge)

    @routes.get("/api/v1/server/security")
    async def server_security_get(request):
        settings = load_app_security_settings(app.storage_dir)
        return web.json_response(
            {
                "listen_host": app.listen_host,
                "listen_port": app.listen_port,
                "https_enabled": app.use_https,
                "is_loopback_bind": _is_loopback_bind_host(app.listen_host),
                "web_ui_ip_allowlist": settings.get("web_ui_ip_allowlist", ""),
                "trusted_proxy_cidrs": settings.get("trusted_proxy_cidrs", ""),
                **app._landlock_status_dict(),
                "privacy_mode_enabled": privacy_mode_enabled(app.config),
                "auth_enabled": app.auth_enabled,
            },
        )

    @routes.patch("/api/v1/server/security")
    async def server_security_patch(request):
        try:
            data = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return web.json_response({"error": "Invalid JSON body"}, status=400)
        if not isinstance(data, dict):
            return web.json_response({"error": "Invalid request body"}, status=400)
        try:
            updates = {}
            if "web_ui_ip_allowlist" in data:
                updates["web_ui_ip_allowlist"] = data.get("web_ui_ip_allowlist")
            if "trusted_proxy_cidrs" in data:
                updates["trusted_proxy_cidrs"] = data.get("trusted_proxy_cidrs")
            if updates:
                settings = save_app_security_settings(app.storage_dir, updates)
            else:
                settings = load_app_security_settings(app.storage_dir)
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        return web.json_response(
            {
                "listen_host": app.listen_host,
                "listen_port": app.listen_port,
                "https_enabled": app.use_https,
                "is_loopback_bind": _is_loopback_bind_host(app.listen_host),
                "web_ui_ip_allowlist": settings.get("web_ui_ip_allowlist", ""),
                "trusted_proxy_cidrs": settings.get("trusted_proxy_cidrs", ""),
                **app._landlock_status_dict(),
                "privacy_mode_enabled": privacy_mode_enabled(app.config),
                "auth_enabled": app.auth_enabled,
            },
        )

    @routes.get("/api/v1/auth/csrf")
    async def auth_csrf(request):
        try:
            session = await get_session(request)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
        token = ensure_session_csrf_token(session)
        return web.json_response({"csrf_token": token})

    # auth status

    # auth status
    @routes.get("/api/v1/auth/status")
    async def auth_status(request):
        if not app.current_context or not app.current_context.running:
            return web.json_response(
                {
                    "auth_enabled": app.auth_enabled,
                    "password_set": False,
                    "authenticated": False,
                    "network_ready": False,
                    "status": "starting",
                    "stage": app._startup_stage,
                    "demo_mode": app.demo_mode,
                    "altcha_enabled": app.altcha_enabled,
                    "auth_page_hint": app.auth_page_hint,
                },
            )
        try:
            session = await get_session(request)
            is_authenticated = session.get("authenticated", False)
            session_identity = session.get("identity_hash")

            # Verify that authentication is for the CURRENT active identity
            actually_authenticated = is_authenticated and (
                session_identity == app.identity.hash.hex()
            )

            return web.json_response(
                {
                    "auth_enabled": app.auth_enabled,
                    "password_set": app.config.auth_password_hash.get() is not None,
                    "authenticated": actually_authenticated,
                    "network_ready": True,
                    "demo_mode": app.demo_mode,
                    "altcha_enabled": app.altcha_enabled,
                    "auth_page_hint": app.auth_page_hint,
                },
            )
        except Exception as e:
            # Handle decryption failure gracefully by reporting as unauthenticated
            return web.json_response(
                {
                    "auth_enabled": app.auth_enabled,
                    "password_set": (
                        app.config.auth_password_hash.get() is not None
                        if app.config
                        else False
                    ),
                    "authenticated": False,
                    "network_ready": bool(
                        app.current_context and app.current_context.running,
                    ),
                    "demo_mode": app.demo_mode,
                    "altcha_enabled": app.altcha_enabled,
                    "auth_page_hint": app.auth_page_hint,
                    "error": str(e),
                },
            )

    # auth setup

    # auth setup
    @routes.post("/api/v1/auth/setup")
    async def auth_setup(request):
        blocked = app._enforce_login_access(request, SETUP_PATH)
        if blocked is not None:
            return blocked
        ip = _request_client_ip(request, get_trusted_proxy_cidrs(app.storage_dir))
        ua = request.headers.get("User-Agent", "") or ""
        ua_h = user_agent_hash(ua)
        id_hash = app.identity.hash.hex()
        dao = app.database.access_attempts if app.database else None

        if app.config.auth_password_hash.get() is not None:
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    SETUP_PATH,
                    request.method,
                    "setup_already_done",
                    "",
                )
            return web.json_response(
                {"error": "Initial setup already completed"},
                status=403,
            )

        try:
            data = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    SETUP_PATH,
                    request.method,
                    "invalid_json",
                    "",
                )
            return web.json_response(
                {"error": "Invalid JSON body"},
                status=400,
            )
        if not isinstance(data, dict):
            return web.json_response(
                {"error": "Invalid request body"},
                status=400,
            )
        from meshchatx.src.backend.altcha_auth import require_altcha_payload

        altcha_blocked = await require_altcha_payload(request, data)
        if altcha_blocked is not None:
            return altcha_blocked
        password = data.get("password")

        if not password or len(password) < 8:
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    SETUP_PATH,
                    request.method,
                    "weak_password",
                    "",
                )
            return web.json_response(
                {"error": "Password must be at least 8 characters long"},
                status=400,
            )

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        app.config.auth_password_hash.set(password_hash)

        session = await get_session(request)
        session.invalidate()
        session = await get_session(request)
        session["authenticated"] = True
        session["identity_hash"] = app.identity.hash.hex()
        rotate_session_csrf_token(session)

        if dao:
            dao.insert(
                id_hash,
                ip,
                ua,
                SETUP_PATH,
                request.method,
                "success",
                "",
            )
            dao.upsert_trusted(id_hash, ip, ua_h)

        return web.json_response({"message": "Setup completed successfully"})

    # auth login

    # auth login
    @routes.post("/api/v1/auth/login")
    async def auth_login(request):
        blocked = app._enforce_login_access(request, LOGIN_PATH)
        if blocked is not None:
            return blocked
        ip = _request_client_ip(request, get_trusted_proxy_cidrs(app.storage_dir))
        ua = request.headers.get("User-Agent", "") or ""
        ua_h = user_agent_hash(ua)
        id_hash = app.identity.hash.hex()
        dao = app.database.access_attempts if app.database else None

        try:
            data = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    LOGIN_PATH,
                    request.method,
                    "invalid_json",
                    "",
                )
            return web.json_response(
                {"error": "Invalid JSON body"},
                status=400,
            )
        if not isinstance(data, dict):
            return web.json_response(
                {"error": "Invalid request body"},
                status=400,
            )
        from meshchatx.src.backend.altcha_auth import require_altcha_payload

        altcha_blocked = await require_altcha_payload(request, data)
        if altcha_blocked is not None:
            return altcha_blocked
        password = data.get("password")

        password_hash = app.config.auth_password_hash.get()
        if password_hash is None:
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    LOGIN_PATH,
                    request.method,
                    "auth_not_setup",
                    "",
                )
            return web.json_response(
                {"error": "Auth not setup"},
                status=403,
            )

        if not password:
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    LOGIN_PATH,
                    request.method,
                    "password_required",
                    "",
                )
            return web.json_response(
                {"error": "Password required"},
                status=400,
            )

        if bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        ):
            session = await get_session(request)
            session.invalidate()
            session = await get_session(request)
            session["authenticated"] = True
            session["identity_hash"] = app.identity.hash.hex()
            rotate_session_csrf_token(session)
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    LOGIN_PATH,
                    request.method,
                    "success",
                    "",
                )
                dao.upsert_trusted(id_hash, ip, ua_h)
            return web.json_response({"message": "Login successful"})

        if dao:
            dao.insert(
                id_hash,
                ip,
                ua,
                LOGIN_PATH,
                request.method,
                "failed_password",
                "",
            )
        return web.json_response(
            {"error": "Invalid password"},
            status=401,
        )

    # auth logout

    # auth logout
    @routes.post("/api/v1/auth/logout")
    async def auth_logout(request):
        session = await get_session(request)
        session.invalidate()
        return web.json_response({"message": "Logged out successfully"})

    # fetch com ports
