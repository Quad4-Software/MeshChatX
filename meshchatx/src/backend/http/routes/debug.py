# SPDX-License-Identifier: 0BSD
"""HTTP routes: debug."""

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


def register_debug_routes(routes, app):
    # serve debug logs
    @routes.get("/api/v1/debug/logs")
    async def get_debug_logs(request):
        search = request.query.get("search")
        level = request.query.get("level")
        module = request.query.get("module")
        is_anomaly = parse_bool_query_param(request.query.get("is_anomaly"))
        limit = int(request.query.get("limit", 100))
        offset = int(request.query.get("offset", 0))

        logs = memory_log_handler.get_logs(
            limit=limit,
            offset=offset,
            search=search,
            level=level,
            module=module,
            is_anomaly=is_anomaly,
        )
        total = memory_log_handler.get_total_count(
            search=search,
            level=level,
            module=module,
            is_anomaly=is_anomaly,
        )

        return web.json_response(
            {
                "logs": logs,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )

    @routes.get("/api/v1/debug/websocket")
    async def get_websocket_debug(request):
        counters = getattr(app, "ws_counters", None)
        clients = getattr(app, "websocket_clients", None) or []
        snap = (
            counters.snapshot(client_count=len(clients))
            if counters is not None
            else {"clients": len(clients)}
        )
        seq_state = getattr(app, "ws_seq_state", None)
        if seq_state is not None:
            snap["seq"] = int(seq_state.seq)
        snap["max_msg_size"] = int(
            getattr(app, "websocket_max_msg_size", 0) or 0,
        )
        return web.json_response({"websocket": snap})

    @routes.get("/api/v1/debug/access-attempts")
    async def get_access_attempts(request):
        search = request.query.get("search")
        outcome = request.query.get("outcome") or None
        limit = int(request.query.get("limit", 100))
        offset = int(request.query.get("offset", 0))
        if not app.database:
            return web.json_response(
                {"attempts": [], "total": 0, "limit": limit, "offset": offset},
            )
        dao = app.database.access_attempts
        attempts = dao.list_attempts(
            limit=limit,
            offset=offset,
            search=search,
            outcome=outcome,
        )
        total = dao.count_attempts(search=search, outcome=outcome)
        return web.json_response(
            {
                "attempts": attempts,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )

    # ── Memory diagnostics (only when --memory-diag is active) ──────────

    # ── Memory diagnostics (only when --memory-diag is active) ──────────

    @routes.get("/api/v1/diagnostics/memory")
    async def get_memory_diagnostics(request):
        if app._mem_diag is None:
            return web.json_response(
                {"enabled": False, "message": "Pass --memory-diag to enable"},
            )
        # tracemalloc.snapshot() + gc.get_objects() are CPU-bound and
        # block the event loop for tens of seconds, so run off-loop.
        report = await asyncio.to_thread(app._mem_diag.report)
        return web.json_response(report)

    @routes.post("/api/v1/diagnostics/memory/snapshot")
    async def take_memory_snapshot(request):
        if app._mem_diag is None or not app._mem_diag.enabled:
            return web.json_response(
                {"error": "Memory diagnostics not enabled"},
                status=400,
            )
        await asyncio.to_thread(app._mem_diag.snapshot)
        gc_result = await asyncio.to_thread(app._mem_diag.find_cyclic_garbage)
        stats = await asyncio.to_thread(app._mem_diag.gc_stats)
        return web.json_response(
            {
                "status": "ok",
                "snapshot_count": len(app._mem_diag._snapshots),
                "gc_collected": gc_result,
                "gc_stats": stats,
            },
        )

    @routes.get("/api/v1/diagnostics/memory/heap")
    async def get_heap_analysis(request):
        if app._mem_diag is None or not app._mem_diag.enabled:
            return web.json_response(
                {"error": "Memory diagnostics not enabled"},
                status=400,
            )
        top_n = int(request.query.get("top_n", 40))
        by_type = await asyncio.to_thread(app._mem_diag.heap_by_type, top_n=top_n)
        by_cat = await asyncio.to_thread(app._mem_diag.heap_by_category)
        acc = await asyncio.to_thread(app._mem_diag.accumulating_types)
        growth = await asyncio.to_thread(app._mem_diag.type_growth_since_start)
        return web.json_response(
            {
                "by_type": by_type,
                "by_category": by_cat,
                "accumulating": acc,
                "growth_since_start": growth,
            },
        )

    @routes.get("/api/v1/diagnostics/memory/gc")
    async def get_gc_stats(request):
        if app._mem_diag is None or not app._mem_diag.enabled:
            return web.json_response(
                {"enabled": False, "message": "Pass --memory-diag to enable"},
            )
        stats = await asyncio.to_thread(app._mem_diag.gc_stats)
        return web.json_response(stats)

    @routes.post("/api/v1/diagnostics/memory/gc/collect")
    async def force_gc_collect(request):
        if app._mem_diag is None or not app._mem_diag.enabled:
            return web.json_response(
                {"error": "Memory diagnostics not enabled"},
                status=400,
            )
        result = await asyncio.to_thread(app._mem_diag.find_cyclic_garbage)
        if app._mem_diag.enabled:
            await asyncio.to_thread(app._mem_diag.snapshot)
        stats = await asyncio.to_thread(app._mem_diag.gc_stats)
        return web.json_response(
            {
                "status": "ok",
                "gc_collected": result,
                "gc_stats": stats,
                "snapshot_count": len(app._mem_diag._snapshots),
            },
        )

    @routes.get("/api/v1/diagnostics/memory/referrers")
    async def get_referrers(request):
        if app._mem_diag is None or not app._mem_diag.enabled:
            return web.json_response(
                {"error": "Memory diagnostics not enabled"},
                status=400,
            )
        type_name = request.query.get("type", "")
        if not type_name:
            return web.json_response(
                {"error": "Specify ?type=<TypeName>"},
                status=400,
            )
        result = await asyncio.to_thread(
            app._mem_diag.find_referrers,
            type_name,
        )
        return web.json_response(result)

    @routes.post("/api/v1/diagnostics/memory/reset")
    async def reset_memory_diagnostics(request):
        if app._mem_diag is None:
            return web.json_response(
                {"error": "Memory diagnostics not enabled"},
                status=400,
            )
        await asyncio.to_thread(app._mem_diag.reset)
        await asyncio.to_thread(app._mem_diag.start)
        return web.json_response({"status": "ok", "message": "Diagnostics reset"})

    # ── Database ─────────────────────────────────────────────────────
