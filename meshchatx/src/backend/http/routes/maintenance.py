# SPDX-License-Identifier: 0BSD
"""HTTP routes: maintenance."""

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


def register_maintenance_routes(routes, app):

    # maintenance - clear messages (all, or older than days / before date)
    @routes.delete("/api/v1/maintenance/messages")
    async def maintenance_clear_messages(request):
        try:
            cutoff = resolve_message_age_cutoff(
                older_than_days=request.query.get("older_than_days"),
                before=request.query.get("before"),
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        if cutoff is None:
            app.database.messages.delete_all_lxmf_messages()
            return web.json_response(
                {"message": "All messages cleared", "deleted": None},
            )

        def _cancel(h):
            try:
                if app.message_router is not None:
                    app.message_router.cancel_outbound(h)
            except Exception:
                pass

        deleted = await asyncio.to_thread(
            purge_messages_before_cutoff,
            app.database.messages,
            _cancel,
            cutoff,
        )
        return web.json_response(
            {
                "message": f"Deleted {deleted} messages older than cutoff",
                "deleted": deleted,
                "cutoff": cutoff,
            },
        )

    @routes.get("/api/v1/maintenance/messages/duplicates")
    async def maintenance_messages_duplicates_preview(request):
        count = await asyncio.to_thread(
            app.database.messages.count_duplicate_lxmf_messages_by_content,
        )
        return web.json_response({"count": count})

    @routes.delete("/api/v1/maintenance/messages/duplicates")
    async def maintenance_messages_duplicates_clear(request):
        def _clear():
            hashes = (
                app.database.messages.list_duplicate_lxmf_message_hashes_by_content()
            )
            if not hashes:
                return 0
            if app.message_router is not None:
                for h in hashes:
                    if not h or len(h) % 2 != 0:
                        continue
                    try:
                        app.message_router.cancel_outbound(bytes.fromhex(h))
                    except Exception:
                        pass
            app.database.messages.delete_lxmf_messages_by_hashes(hashes)
            app.database.messages.prune_conversation_metadata_for_peers_with_no_messages()
            return len(hashes)

        deleted = await asyncio.to_thread(_clear)
        return web.json_response(
            {
                "message": f"Deleted {deleted} duplicate messages",
                "deleted": deleted,
            },
        )

    @routes.get("/api/v1/maintenance/messages/purge-preview")
    async def maintenance_messages_purge_preview(request):
        try:
            cutoff = resolve_message_age_cutoff(
                older_than_days=request.query.get("older_than_days"),
                before=request.query.get("before"),
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        if cutoff is None:
            return web.json_response(
                {"message": "older_than_days or before is required"},
                status=400,
            )
        count = app.database.messages.count_lxmf_messages_with_timestamp_before(
            cutoff,
        )
        return web.json_response({"count": count, "cutoff": cutoff})

    # maintenance - clear announces

    # maintenance - clear announces
    @routes.delete("/api/v1/maintenance/announces")
    async def maintenance_clear_announces(request):
        aspect = request.query.get("aspect")
        app.database.announces.delete_all_announces(aspect=aspect)
        return web.json_response(
            {
                "message": f"Announces cleared{' for aspect ' + aspect if aspect else ''}",
            },
        )

    # maintenance - clear favorites

    # maintenance - clear favorites
    @routes.delete("/api/v1/maintenance/favourites")
    async def maintenance_clear_favourites(request):
        aspect = request.query.get("aspect")
        app.database.announces.delete_all_favourites(aspect=aspect)
        return web.json_response(
            {
                "message": f"Favourites cleared{' for aspect ' + aspect if aspect else ''}",
            },
        )

    # maintenance - clear archives

    # maintenance - clear archives
    @routes.delete("/api/v1/maintenance/archives")
    async def maintenance_clear_archives(request):
        app.database.misc.delete_archived_pages()
        return web.json_response({"message": "All archived pages cleared"})

    # maintenance - clear LXMF icons

    # maintenance - clear LXMF icons
    @routes.delete("/api/v1/maintenance/lxmf-icons")
    async def maintenance_clear_lxmf_icons(request):
        app.database.misc.delete_all_user_icons()
        return web.json_response({"message": "All LXMF icons cleared"})

    @routes.delete("/api/v1/maintenance/stickers")
    async def maintenance_clear_stickers(request):
        identity_hash = app.identity.hash.hex()
        n = app.database.stickers.delete_all_for_identity(identity_hash)
        return web.json_response({"message": "Stickers cleared", "deleted": n})

    @routes.delete("/api/v1/maintenance/gifs")
    async def maintenance_clear_gifs(request):
        identity_hash = app.identity.hash.hex()
        n = app.database.gifs.delete_all_for_identity(identity_hash)
        return web.json_response({"message": "GIFs cleared", "deleted": n})

    @routes.delete("/api/v1/maintenance/path-table")
    async def maintenance_clear_path_table(request):
        try:
            dropped = app.rnpath_handler.drop_all_paths()
            return web.json_response(
                {"message": "Path table cleared", "dropped": dropped},
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # maintenance - export messages (optional age filter for archive-before-purge)

    # maintenance - export messages (optional age filter for archive-before-purge)
    @routes.get("/api/v1/maintenance/messages/export")
    async def maintenance_export_messages(request):
        try:
            cutoff = resolve_message_age_cutoff(
                older_than_days=request.query.get("older_than_days"),
                before=request.query.get("before"),
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        messages_list = []
        page_size = 5000
        offset = 0
        while True:
            if cutoff is None:
                page = app.database.messages.get_all_lxmf_messages(
                    limit=page_size,
                    offset=offset,
                )
            else:
                page = app.database.messages.get_lxmf_messages_with_timestamp_before(
                    cutoff,
                    limit=page_size,
                    offset=offset,
                )
            messages_list.extend(dict(m) for m in page)
            if len(page) < page_size:
                break
            offset += page_size
        bundle = await asyncio.to_thread(
            build_messages_export_bundle,
            app.database,
            messages_list,
        )
        return web.json_response(bundle)

    def _message_import_response(result):
        if not result.get("ok", True) and result.get("error"):
            return web.json_response(
                {
                    "error": result["error"],
                    "imported": result.get("imported", 0),
                    "skipped": result.get("skipped", 0),
                },
                status=400,
            )
        imported = result["imported"]
        skipped = result["skipped"]
        errors = result.get("errors") or []
        if imported == 0 and errors:
            return web.json_response(
                {
                    "error": errors[0]["error"],
                    "imported": imported,
                    "skipped": skipped,
                    "errors": errors,
                },
                status=400,
            )
        response = {
            "message": f"Successfully imported {imported} messages",
            "imported": imported,
            "skipped": skipped,
            "contacts_added": result.get("contacts_added", 0),
            "contacts_skipped": result.get("contacts_skipped", 0),
            "display_names_imported": result.get("display_names_imported", 0),
            "read_state_imported": result.get("read_state_imported", 0),
        }
        if errors:
            response["errors"] = errors
        return web.json_response(response)

    # maintenance - import messages

    # maintenance - import messages
    @routes.post("/api/v1/maintenance/messages/import")
    async def maintenance_import_messages(request):
        try:
            data = await request.json()
            if app.database is None:
                return web.json_response(
                    {"error": "No active identity database"},
                    status=400,
                )

            result = await asyncio.to_thread(
                import_messages_export_bundle,
                app.database,
                data,
            )
            return _message_import_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    @routes.post("/api/v1/maintenance/messages/import-file")
    async def maintenance_import_messages_file(request):
        try:
            if app.database is None:
                return web.json_response(
                    {"error": "No active identity database"},
                    status=400,
                )

            reader = await request.multipart()
            field = await reader.next()
            if field is None or field.name != "file":
                return web.json_response(
                    {"error": "Import file is required"},
                    status=400,
                )

            chunks = []
            while True:
                chunk = await field.read_chunk(size=1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                return web.json_response(
                    {"error": f"Invalid JSON: {exc}"},
                    status=400,
                )

            result = await asyncio.to_thread(
                import_messages_export_bundle,
                app.database,
                payload,
            )
            return _message_import_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    # get config
