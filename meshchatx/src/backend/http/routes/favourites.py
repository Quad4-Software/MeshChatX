# SPDX-License-Identifier: 0BSD
"""HTTP routes: favourites."""

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


def register_favourites_routes(routes, app):

    # announce
    @routes.get("/api/v1/announce")
    async def announce_trigger(request):
        await app.announce()

        return web.json_response(
            {
                "message": "announcing",
            },
        )

    # serve announces

    # serve announces
    @routes.get("/api/v1/announces")
    async def announces_get(request):
        # get query params
        aspect = request.query.get("aspect", None)
        identity_hash = request.query.get("identity_hash", None)
        destination_hash = request.query.get("destination_hash", None)
        search_query = request.query.get("search", None)

        try:
            limit = request.query.get("limit")
            limit = int(limit) if limit is not None and limit != "" else None
        except ValueError:
            limit = None

        try:
            offset = request.query.get("offset")
            offset = int(offset) if offset is not None else 0
        except ValueError:
            offset = 0

        if not search_query and limit is None:
            limit = app._default_announce_fetch_limit(aspect)

        search_max = 2000
        if app.current_context and app.current_context.config:
            sm = app.current_context.config.announce_search_max_fetch.get()
            if sm is not None and sm > 0:
                search_max = min(int(sm), 10_000)

        include_blocked = (
            request.query.get("include_blocked", "false").lower() == "true"
        )

        blocked_identity_hashes = None
        if not include_blocked:
            blocked = await asyncio.to_thread(
                app.database.misc.get_blocked_destinations,
            )
            blocked_identity_hashes = [b["destination_hash"] for b in blocked]

        if search_query:
            # limit here is the caller's desired page size for the
            # paginated, filtered results below, not the number of rows
            # to scan for matches. Always scan up to search_max rows so
            # matches outside the most-recent page are still found.
            db_limit = search_max
        else:
            db_limit = limit
        db_offset = offset if not search_query else 0

        results = await asyncio.to_thread(
            app.announce_manager.get_filtered_announces,
            aspect=aspect,
            identity_hash=identity_hash,
            destination_hash=destination_hash,
            query=None,
            blocked_identity_hashes=blocked_identity_hashes,
            limit=db_limit,
            offset=db_offset,
        )

        total_count = 0
        if not search_query:
            if db_limit is None:
                total_count = len(results)
            else:
                total_count = await asyncio.to_thread(
                    app.announce_manager.get_filtered_announces_count,
                    aspect=aspect,
                    identity_hash=identity_hash,
                    destination_hash=destination_hash,
                    query=None,
                    blocked_identity_hashes=blocked_identity_hashes,
                )

        # pre-fetch icons and other data to avoid N+1 queries in convert_db_announce_to_dict
        all_announces = await asyncio.to_thread(
            app._batch_convert_announces_to_api_dicts,
            results,
            aspect,
        )

        # apply search query filter if provided
        if search_query:
            all_announces = filter_announced_dicts_by_search_query(
                all_announces,
                search_query,
            )

            # Re-calculate total_count after search filter
            total_count = len(all_announces)
            # apply pagination after search
            start = offset
            end = start + (limit if limit is not None else total_count)
            paginated_results = all_announces[start:end]
        else:
            # We already paginated in DB, and total_count was calculated before processing
            paginated_results = all_announces

        return web.json_response(
            {
                "announces": paginated_results,
                "total_count": total_count,
            },
        )

    @routes.post("/api/v1/announces/query")
    async def announces_query(request):
        try:
            data = await request.json()
        except Exception:
            data = {}
        destination_hashes = data.get("destination_hashes")
        aspects = data.get("aspects")
        if not isinstance(destination_hashes, list) or not destination_hashes:
            return web.json_response({"announces": [], "total_count": 0})
        if not isinstance(aspects, list) or not aspects:
            aspects = ["lxmf.delivery", "nomadnetwork.node"]

        blocked_identity_hashes = None
        if app.current_context and app.current_context.config:
            blocked = await asyncio.to_thread(
                app.database.misc.get_blocked_destinations,
            )
            blocked_identity_hashes = [b["destination_hash"] for b in blocked]

        results = await asyncio.to_thread(
            app.announce_manager.get_announces_for_destination_hashes,
            destination_hashes=destination_hashes,
            aspects=aspects,
            blocked_identity_hashes=blocked_identity_hashes,
        )
        all_announces = await asyncio.to_thread(
            app._batch_convert_announces_to_api_dicts,
            results,
            None,
            False,
        )
        return web.json_response(
            {
                "announces": all_announces,
                "total_count": len(all_announces),
            },
        )

    # serve favourites

    # serve favourites
    @routes.get("/api/v1/favourites")
    async def favourites_get(request):
        # get query params
        aspect = request.query.get("aspect", None)

        # get favourites from database
        results = app.database.announces.get_favourites(aspect=aspect)

        # process favourites
        favourites = [convert_db_favourite_to_dict(favourite) for favourite in results]

        return web.json_response(
            {
                "favourites": favourites,
            },
        )

    # add favourite

    # add favourite
    @routes.post("/api/v1/favourites/add")
    async def favourites_add(request):
        # get request data
        data = await request.json()
        destination_hash = data.get("destination_hash", None)
        display_name = data.get("display_name", None)
        aspect = data.get("aspect", None)

        # destination hash is required
        if destination_hash is None:
            return web.json_response(
                {
                    "message": "destination_hash is required",
                },
                status=422,
            )

        # display name is required
        if display_name is None:
            return web.json_response(
                {
                    "message": "display_name is required",
                },
                status=422,
            )

        # aspect is required
        if aspect is None:
            return web.json_response(
                {
                    "message": "aspect is required",
                },
                status=422,
            )

        # upsert favourite
        app.database.announces.upsert_favourite(
            destination_hash,
            display_name,
            aspect,
        )
        return web.json_response(
            {
                "message": "Favourite has been added!",
            },
        )

    # rename favourite

    # rename favourite
    @routes.post("/api/v1/favourites/{destination_hash}/rename")
    async def favourites_rename(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # get request data
        data = await request.json()
        raw_name = data.get("display_name")
        if raw_name is None:
            display_name = ""
        elif isinstance(raw_name, str):
            display_name = raw_name.strip()
        else:
            display_name = str(raw_name).strip()

        favourite = app.database.announces.get_favourite_by_destination_hash(
            destination_hash,
        )
        if favourite is None:
            return web.json_response(
                {"message": "Favourite not found"},
                status=404,
            )

        # update display name if provided
        if len(display_name) > 0:
            app.database.announces.upsert_custom_display_name(
                destination_hash,
                display_name,
            )
            app.database.announces.upsert_favourite(
                destination_hash,
                display_name,
                favourite["aspect"],
            )

        return web.json_response(
            {
                "message": "Favourite has been renamed",
            },
        )

    # delete favourite

    # delete favourite
    @routes.delete("/api/v1/favourites/{destination_hash}")
    async def favourites_delete(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # delete favourite
        app.database.announces.delete_favourite(destination_hash)
        return web.json_response(
            {
                "message": "Favourite has been deleted!",
            },
        )

    # bulk import favourites

    # bulk import favourites
    @routes.post("/api/v1/favourites/import")
    async def favourites_import(request):
        try:
            data = await request.json()
            entries = data.get("favourites", [])
            if not isinstance(entries, list):
                return web.json_response(
                    {
                        "message": "Invalid import format: favourites must be an array",
                    },
                    status=400,
                )
            seen = {}
            no_hash = []
            for entry in entries:
                h = entry.get("destination_hash")
                if h:
                    seen[h] = entry
                else:
                    no_hash.append(entry)
            unique_entries = list(seen.values()) + no_hash
            imported = 0
            skipped = 0
            for entry in unique_entries:
                dest_hash = entry.get("destination_hash")
                display_name = entry.get("display_name", "")
                aspect = entry.get("aspect")
                if not dest_hash or not aspect:
                    skipped += 1
                    continue
                try:
                    app.database.announces.upsert_favourite(
                        dest_hash,
                        display_name,
                        aspect,
                    )
                    imported += 1
                except Exception:
                    skipped += 1
            return web.json_response(
                {
                    "message": "Favourites import complete",
                    "imported": imported,
                    "skipped": skipped,
                },
            )
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to import favourites: {e!s}"},
                status=500,
            )

    @routes.get("/api/v1/favourites/layout")
    async def favourites_layout_get(request):
        layout = app.database.announces.get_favourites_layout()
        return web.json_response({"layout": layout})

    @routes.put("/api/v1/favourites/layout")
    async def favourites_layout_put(request):
        from meshchatx.src.backend.favourites_layout import layout_payload_too_large

        content_length = request.content_length
        if content_length is not None and layout_payload_too_large(
            content_length,
        ):
            return web.json_response(
                {"message": "favourites layout exceeds size limit"},
                status=413,
            )
        try:
            raw = await request.read()
        except Exception:
            return web.json_response(
                {"message": "Invalid request body"},
                status=400,
            )
        if layout_payload_too_large(len(raw)):
            return web.json_response(
                {"message": "favourites layout exceeds size limit"},
                status=413,
            )
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return web.json_response(
                {"message": "Invalid JSON body"},
                status=400,
            )
        layout = data.get("layout") if isinstance(data, dict) else None
        try:
            saved = app.database.announces.set_favourites_layout(layout)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"layout": saved})

    # serve archived pages
