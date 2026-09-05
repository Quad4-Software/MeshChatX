# SPDX-License-Identifier: 0BSD
"""HTTP routes: archives."""

from __future__ import annotations

from meshchatx.src.backend.crawler_manager import make_snippet
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
    nomad_link_identity_kwargs,
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


def _resolve_node_name(app, destination_hash: str) -> str:
    node_name = app.get_custom_destination_display_name(destination_hash)
    if not node_name:
        db_announce = app.database.announces.get_announce_by_hash(destination_hash)
        if db_announce and db_announce["aspect"] == "nomadnetwork.node":
            node_name = parse_nomadnetwork_node_display_name(db_announce["app_data"])
    return node_name or "Unknown Node"


def register_archives_routes(routes, app):
    @routes.get("/api/v1/nomadnet/archives")
    async def get_all_archived_pages(request):
        query = request.query.get("q", "").strip()
        destination_hash = request.query.get("destination_hash", "").strip() or None
        include_content_raw = request.query.get("include_content")
        if include_content_raw is None:
            include_content = False
        else:
            include_content = parse_bool_query_param(include_content_raw)
        try:
            page = max(1, int(request.query.get("page", 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            limit = max(1, min(100, int(request.query.get("limit", 25))))
        except (ValueError, TypeError):
            limit = 25
        offset = (page - 1) * limit

        total_count = app.database.misc.count_archived_pages(
            destination_hash=destination_hash,
            query=query or None,
        )
        total_pages = (total_count + limit - 1) // limit if total_count else 0

        # Fetch a wider window when searching so token ranking can reorder.
        fetch_limit = limit
        fetch_offset = offset
        if query:
            fetch_limit = min(200, max(limit * 4, limit))
            fetch_offset = max(0, offset - limit)

        rows = app.database.misc.get_archived_pages_paginated(
            destination_hash=destination_hash,
            query=query or None,
            limit=fetch_limit,
            offset=fetch_offset,
            include_content=True if query else include_content,
        )

        crawler = (
            getattr(app.current_context, "crawler_manager", None)
            if app.current_context
            else None
        )
        if query and crawler:
            rows = crawler.rank_archives_by_query(rows, query)
            # Re-slice to the requested page after ranking.
            start = offset - fetch_offset
            rows = rows[start : start + limit]
        elif query and not include_content:
            # Rank helper needed content. Drop bodies for the list payload.
            pass

        archives = []
        for archive in rows:
            content = archive.get("content")
            preview = archive.get("content_preview")
            if content is None and preview is not None:
                content = preview
            raw_preview = (content or "")[:2000]
            snippet = make_snippet(content, query or None)
            entry = {
                "id": archive["id"],
                "destination_hash": archive["destination_hash"],
                "node_name": _resolve_node_name(app, archive["destination_hash"]),
                "page_path": archive["page_path"],
                "hash": archive["hash"],
                "created_at": archive["created_at"],
                "snippet": snippet,
                "preview": raw_preview,
            }
            if include_content:
                entry["content"] = archive.get("content") or ""
            archives.append(entry)

        return web.json_response(
            {
                "archives": archives,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": total_pages,
                },
            },
        )

    @routes.get("/api/v1/nomadnet/archives/{archive_id}")
    async def get_archived_page(request):
        try:
            archive_id = int(request.match_info["archive_id"])
        except (TypeError, ValueError):
            return web.json_response({"message": "Invalid archive id"}, status=400)
        archive = app.database.misc.get_archived_page_by_id(archive_id)
        if not archive:
            return web.json_response({"message": "Archive not found"}, status=404)
        return web.json_response(
            {
                "archive": {
                    "id": archive["id"],
                    "destination_hash": archive["destination_hash"],
                    "node_name": _resolve_node_name(app, archive["destination_hash"]),
                    "page_path": archive["page_path"],
                    "content": archive["content"],
                    "hash": archive["hash"],
                    "created_at": archive["created_at"],
                    "snippet": make_snippet(archive["content"], None),
                },
            },
        )

    @routes.delete("/api/v1/nomadnet/archives")
    async def delete_archived_pages(request):
        data = await request.json()
        ids = data.get("ids", [])

        if not ids:
            return web.json_response(
                {
                    "message": "No archive IDs provided!",
                },
                status=400,
            )

        app.database.misc.delete_archived_pages(ids=ids)

        return web.json_response(
            {
                "message": f"Deleted {len(ids)} archives!",
            },
        )

    @routes.get("/api/v1/nomadnet/crawl/opt-outs")
    async def list_crawl_opt_outs(_request):
        rows = app.database.misc.list_crawl_opt_outs()
        return web.json_response(
            {
                "opt_outs": [
                    {
                        "destination_hash": row["destination_hash"],
                        "reason": row["reason"],
                        "source": row["source"],
                        "created_at": row["created_at"],
                        "node_name": _resolve_node_name(app, row["destination_hash"]),
                    }
                    for row in rows
                ],
            },
        )

    @routes.post("/api/v1/nomadnet/crawl/opt-outs")
    async def add_crawl_opt_out(request):
        data = await request.json()
        destination_hash = (data.get("destination_hash") or "").strip().lower()
        if len(destination_hash) != 32:
            return web.json_response(
                {"message": "destination_hash must be 32 hex characters"},
                status=400,
            )
        reason = (data.get("reason") or "user").strip()[:200] or "user"
        crawler = (
            getattr(app.current_context, "crawler_manager", None)
            if app.current_context
            else None
        )
        if crawler:
            crawler.record_opt_out(destination_hash, reason=reason, source="user")
        else:
            app.database.misc.upsert_crawl_opt_out(
                destination_hash,
                reason=reason,
                source="user",
            )
            app.database.misc.cancel_crawl_tasks_for_destination(destination_hash)
        return web.json_response(
            {"message": "opt-out recorded", "destination_hash": destination_hash},
        )

    @routes.delete("/api/v1/nomadnet/crawl/opt-outs/{destination_hash}")
    async def remove_crawl_opt_out(request):
        destination_hash = (
            (request.match_info.get("destination_hash") or "").strip().lower()
        )
        if len(destination_hash) != 32:
            return web.json_response(
                {"message": "destination_hash must be 32 hex characters"},
                status=400,
            )
        crawler = (
            getattr(app.current_context, "crawler_manager", None)
            if app.current_context
            else None
        )
        if crawler:
            crawler.remove_opt_out(destination_hash)
        else:
            app.database.misc.delete_crawl_opt_out(destination_hash)
        return web.json_response(
            {"message": "opt-out removed", "destination_hash": destination_hash},
        )

    @routes.post("/api/v1/nomadnet/archives/recrawl")
    async def recrawl_archived_page(request):
        """Fetch a Nomad page now and store a fresh archive snapshot."""
        data = await request.json()
        destination_hash = (data.get("destination_hash") or "").strip().lower()
        page_path = (data.get("page_path") or "").strip()
        if len(destination_hash) != 32:
            return web.json_response(
                {"message": "destination_hash must be 32 hex characters"},
                status=400,
            )
        if not page_path:
            page_path = (
                app.config.nomad_default_page_path.get() if app.config else None
            ) or "/page/index.mu"

        crawler = (
            getattr(app.current_context, "crawler_manager", None)
            if app.current_context
            else None
        )
        if crawler and crawler.is_opted_out(destination_hash):
            return web.json_response(
                {"message": "Node is on the crawl opt-out list"},
                status=403,
            )

        done_event = asyncio.Event()
        success = [False]
        content_received = [None]
        failure_reason = ["timeout"]

        def on_success(content):
            success[0] = True
            content_received[0] = content
            done_event.set()

        def on_failure(reason):
            failure_reason[0] = reason or "download failed"
            done_event.set()

        downloader = NomadnetPageDownloader(
            destination_hash=bytes.fromhex(destination_hash),
            page_path=page_path.split("`", 1)[0],
            data=None,
            on_page_download_success=on_success,
            on_page_download_failure=on_failure,
            on_progress_update=lambda _p: None,
            timeout=120,
            reticulum=getattr(app, "reticulum", None),
            **nomad_link_identity_kwargs(
                app,
                bytes.fromhex(destination_hash),
                private=False,
            ),
        )

        try:
            download_task = asyncio.create_task(downloader.download())
            try:
                await asyncio.wait_for(done_event.wait(), timeout=180)
            except TimeoutError:
                failure_reason[0] = "timeout"
                downloader.cancel()
            await download_task
        except Exception as exc:
            return web.json_response(
                {"message": f"Recrawl failed: {exc}"},
                status=502,
            )

        if not success[0]:
            return web.json_response(
                {"message": f"Recrawl failed: {failure_reason[0]}"},
                status=502,
            )

        app.archive_page(
            destination_hash,
            page_path,
            content_received[0] or "",
            is_manual=True,
        )
        if crawler:
            crawler.queue_if_allowed(
                destination_hash,
                page_path,
                depth=0,
                force=True,
            )

        versions = app.database.misc.get_archived_page_versions(
            destination_hash,
            page_path,
        )
        latest = versions[0] if versions else None
        if not latest:
            return web.json_response(
                {"message": "Page fetched but archive was not stored"},
                status=500,
            )
        return web.json_response(
            {
                "message": "Recrawled",
                "archive": {
                    "id": latest["id"],
                    "destination_hash": latest["destination_hash"],
                    "node_name": _resolve_node_name(app, latest["destination_hash"]),
                    "page_path": latest["page_path"],
                    "content": latest["content"],
                    "hash": latest["hash"],
                    "created_at": latest["created_at"],
                    "snippet": make_snippet(latest["content"], None),
                    "preview": (latest["content"] or "")[:2000],
                },
            },
        )
