# SPDX-License-Identifier: 0BSD
"""HTTP routes: lxmf."""

from __future__ import annotations

from meshchatx.src.backend.database.sqlite_errors import sqlite_error_is_retryable
from meshchatx.src.backend.http.db_availability import (
    http_for_database_exception,
    require_database,
)
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


def register_lxmf_routes(routes, app):
    @routes.get("/api/v1/lxmf/propagation-node/status")
    async def propagation_node_status(request):
        router = app.message_router
        current_state = None
        current_progress = 0.0
        transfer_size = None
        if router is not None:
            try:
                current_state = router.propagation_transfer_state
                current_progress = router.propagation_transfer_progress
                transfer_size = getattr(
                    router,
                    "propagation_transfer_size",
                    None,
                )
                # COMPLETE is terminal, so reset to idle so the UI does not keep
                # looking "busy" after a finished auto/manual sync.
                if current_state == router.PR_COMPLETE:
                    with contextlib.suppress(Exception):
                        router.propagation_transfer_state = router.PR_IDLE
                        router.propagation_transfer_progress = 0.0
                        if hasattr(router, "propagation_transfer_size"):
                            router.propagation_transfer_size = None
            except Exception:
                pass
        sync_metrics = app._collect_propagation_sync_metrics()
        progress_raw = current_progress
        try:
            progress_pct = float(progress_raw) * 100
        except (TypeError, ValueError):
            progress_pct = 0.0
        last_result = getattr(
            app.message_router,
            "propagation_transfer_last_result",
            None,
        )
        if not isinstance(last_result, (int, float, str, type(None))):
            last_result = None
        if current_state is None:
            current_state = 0
        transfer_size_bytes = None
        if isinstance(transfer_size, (int, float)) and transfer_size > 0:
            transfer_size_bytes = int(transfer_size)
        inbound_delivery_count = 0
        inbound_deliveries = []
        if router is not None:
            inbound_deliveries = list_inbound_deliveries(router)
            inbound_delivery_count = len(inbound_deliveries)
        return web.json_response(
            {
                "propagation_node_status": {
                    "state": convert_propagation_node_state_to_string(
                        current_state,
                    ),
                    "progress": progress_pct,
                    "transfer_size_bytes": transfer_size_bytes,
                    "inbound_delivery_count": inbound_delivery_count,
                    "inbound_deliveries": inbound_deliveries,
                    "messages_received": last_result,
                    "messages_stored": sync_metrics["messages_stored"],
                    "delivery_confirmations": sync_metrics["delivery_confirmations"],
                    "messages_hidden": sync_metrics["messages_hidden"],
                },
                "local_propagation_node": app.get_local_propagation_node_stats(),
            },
        )

    # sync propagation node

    # sync propagation node
    @routes.post("/api/v1/lxmf/propagation-node/sync")
    async def propagation_node_sync(request):
        from meshchatx.src.backend.demo_mode import demo_mode_block_response

        blocked = demo_mode_block_response(app)
        if blocked is not None:
            return blocked
        # ensure propagation node is configured before attempting to sync
        outbound_node = app.message_router.get_outbound_propagation_node()
        if outbound_node is None:
            return web.json_response(
                {
                    "message": "A propagation node must be configured to sync messages.",
                },
                status=400,
            )

        # proactively request path, but do not block/fail here.
        # LXMF internally manages PR_PATH_REQUESTED and retries.
        if not RNS.Transport.has_path(outbound_node):
            with contextlib.suppress(Exception):
                RNS.Transport.request_path(outbound_node)

        # request messages from propagation node
        await app.sync_propagation_nodes(force=True)

        return web.json_response(
            {
                "message": "Sync is starting",
            },
        )

    # stop syncing propagation node

    # stop syncing propagation node
    @routes.post("/api/v1/lxmf/propagation-node/stop-sync")
    async def propagation_node_stop_sync(request):
        from meshchatx.src.backend.demo_mode import demo_mode_block_response

        blocked = demo_mode_block_response(app)
        if blocked is not None:
            return blocked
        app.stop_propagation_node_sync()

        return web.json_response(
            {
                "message": "Sync is stopping",
            },
        )

    @routes.post("/api/v1/lxmf/propagation-node/cancel-inbound")
    async def propagation_node_cancel_inbound(request):
        router = app.message_router
        data = {}
        with contextlib.suppress(Exception):
            data = await request.json()
        if not isinstance(data, dict):
            data = {}
        resource_hash = data.get("resource_hash")
        result = cancel_inbound_deliveries(router, resource_hash=resource_hash)
        if not result.get("ok"):
            status = 503 if "unavailable" in str(result.get("error") or "") else 400
            return web.json_response(
                {
                    "message": result.get(
                        "error",
                        "Failed to cancel inbound deliveries",
                    ),
                    "cancelled": result.get("cancelled", 0),
                },
                status=status,
            )
        cancelled = int(result.get("cancelled") or 0)
        if resource_hash:
            message = (
                "Cancelled inbound delivery"
                if cancelled
                else "Inbound delivery was not active"
            )
        else:
            message = f"Cancelled {cancelled} inbound deliveries"
        return web.json_response(
            {
                "message": message,
                "cancelled": cancelled,
                "resource_hash": result.get("resource_hash"),
                "inbound_delivery_count": len(list_inbound_deliveries(router)),
                "inbound_deliveries": list_inbound_deliveries(router),
            },
        )

    @routes.post("/api/v1/lxmf/propagation-node/stop")
    async def propagation_node_stop(request):
        app.config.lxmf_local_propagation_node_enabled.set(False)
        app.stop_local_propagation_node()
        AsyncUtils.run_async(app.send_config_to_websocket_clients())
        return web.json_response(
            {
                "message": "Local propagation node stopped",
                "local_propagation_node": app.get_local_propagation_node_stats(),
            },
        )

    @routes.post("/api/v1/lxmf/propagation-node/restart")
    async def propagation_node_restart(request):
        app.config.lxmf_local_propagation_node_enabled.set(True)
        app.restart_local_propagation_node()
        AsyncUtils.run_async(app.send_config_to_websocket_clients())
        return web.json_response(
            {
                "message": "Local propagation node restarted",
                "local_propagation_node": app.get_local_propagation_node_stats(),
            },
        )

    # serve propagation nodes

    # serve propagation nodes
    @routes.get("/api/v1/lxmf/propagation-nodes")
    async def propagation_nodes_get(request):
        ctx = app.current_context
        if not ctx or not getattr(ctx, "running", False) or ctx.database is None:
            return web.json_response(
                {
                    "message": "Application is initializing or switching identity",
                },
                status=503,
            )
        database = ctx.database
        # get query params
        limit = request.query.get("limit", None)

        # get lxmf.propagation announces
        limit_int = None
        if limit is not None:
            try:
                limit_int = max(0, int(limit))
            except (ValueError, TypeError):
                limit_int = None
        results = database.announces.get_announces(
            aspect="lxmf.propagation",
            limit=limit_int,
        )

        related_index = database.announces.index_announces_by_identity_aspect(
            database.announces.get_announces_for_identity_hashes(
                [a.get("identity_hash") for a in results],
                aspects=["lxmf.delivery", "nomadnetwork.node"],
            ),
        )

        # process announces
        lxmf_propagation_nodes = []
        local_identity_hash = ctx.identity.hash.hex() if ctx else None
        local_destination_hash_raw = (
            getattr(ctx.message_router.propagation_destination, "hexhash", None)
            if ctx
            else None
        )
        if local_destination_hash_raw is None and ctx:
            local_destination_hash_raw = getattr(
                ctx.message_router.propagation_destination,
                "hash",
                None,
            )
        if isinstance(local_destination_hash_raw, bytes):
            local_destination_hash = local_destination_hash_raw.hex()
        elif isinstance(local_destination_hash_raw, str):
            local_destination_hash = local_destination_hash_raw
        else:
            local_destination_hash = None
        local_stats = app.get_local_propagation_node_stats(context=ctx) if ctx else None
        for announce in results:
            ident = announce.get("identity_hash")
            lxmf_delivery_announce = related_index.get((ident, "lxmf.delivery"))
            nomadnetwork_node_announce = related_index.get(
                (ident, "nomadnetwork.node"),
            )

            # get a display name from other announces belonging to the propagation nodes identity
            operator_display_name = None
            if (
                lxmf_delivery_announce is not None
                and lxmf_delivery_announce["app_data"] is not None
            ):
                operator_display_name = parse_lxmf_display_name(
                    lxmf_delivery_announce["app_data"],
                    None,
                )
            elif (
                nomadnetwork_node_announce is not None
                and nomadnetwork_node_announce["app_data"] is not None
            ):
                operator_display_name = parse_nomadnetwork_node_display_name(
                    nomadnetwork_node_announce["app_data"],
                    None,
                )

            # parse app_data so we can see if propagation is enabled or disabled for this node
            is_propagation_enabled = None
            per_transfer_limit = None
            propagation_node_data = parse_lxmf_propagation_node_app_data(
                announce["app_data"],
            )
            if propagation_node_data is not None:
                is_propagation_enabled = propagation_node_data["enabled"]
                per_transfer_limit = propagation_node_data["per_transfer_limit"]

            # ensure created_at and updated_at have Z suffix for UTC if they don't have a timezone
            created_at = str(announce["created_at"])
            if created_at and "+" not in created_at and "Z" not in created_at:
                created_at += "Z"

            updated_at = str(announce["updated_at"])
            if updated_at and "+" not in updated_at and "Z" not in updated_at:
                updated_at += "Z"

            is_local_node = (
                announce["identity_hash"] == local_identity_hash
                or announce["destination_hash"] == local_destination_hash
            )
            if is_local_node and isinstance(local_stats, dict):
                local_running = local_stats.get("is_running")
                if isinstance(local_running, bool):
                    is_propagation_enabled = local_running

            lxmf_propagation_nodes.append(
                {
                    "destination_hash": announce["destination_hash"],
                    "identity_hash": announce["identity_hash"],
                    "operator_display_name": operator_display_name,
                    "is_propagation_enabled": is_propagation_enabled,
                    "per_transfer_limit": per_transfer_limit,
                    "is_local_node": is_local_node,
                    "local_node_stats": (local_stats if is_local_node else None),
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            )

        if (
            ctx is not None
            and local_destination_hash is not None
            and not any(
                node["destination_hash"] == local_destination_hash
                for node in lxmf_propagation_nodes
            )
        ):
            now_iso = datetime.now(UTC).isoformat()
            lxmf_propagation_nodes.insert(
                0,
                {
                    "destination_hash": local_destination_hash,
                    "identity_hash": local_identity_hash,
                    "operator_display_name": ctx.config.display_name.get(),
                    "is_propagation_enabled": (
                        local_stats.get("is_running")
                        if isinstance(local_stats, dict)
                        and isinstance(local_stats.get("is_running"), bool)
                        else ctx.config.lxmf_local_propagation_node_enabled.get()
                    ),
                    "per_transfer_limit": int(
                        getattr(
                            ctx.message_router,
                            "propagation_per_transfer_limit",
                            0,
                        ),
                    ),
                    "is_local_node": True,
                    "local_node_stats": local_stats,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                },
            )

        return web.json_response(
            {
                "lxmf_propagation_nodes": lxmf_propagation_nodes,
            },
        )

    # get path to destination
    async def path_table(request):
        limit = request.query.get("limit", None)
        offset = request.query.get("offset", None)
        destination_hashes = None
        if request.method == "POST":
            try:
                body = await request.json()
                destination_hashes = body.get("destination_hashes")
                if destination_hashes and not isinstance(destination_hashes, list):
                    destination_hashes = None
            except Exception:
                pass

        all_paths = []
        if hasattr(app, "reticulum") and app.reticulum:
            try:
                all_paths = app.reticulum.get_path_table()
            except Exception:
                pass

        if destination_hashes:
            hash_set = {h.lower() for h in destination_hashes if isinstance(h, str)}
            all_paths = [p for p in all_paths if p["hash"].hex().lower() in hash_set]

        total_count = len(all_paths)

        # apply pagination if requested
        if limit is not None or offset is not None:
            try:
                start = int(offset) if offset else 0
                end = (start + int(limit)) if limit else total_count
                paginated_paths = all_paths[start:end]
            except (ValueError, TypeError):
                paginated_paths = all_paths
        else:
            paginated_paths = all_paths

        path_table = []
        for path in paginated_paths:
            path["hash"] = path["hash"].hex()
            path["via"] = path["via"].hex()
            path_table.append(path)

        return web.json_response(
            {
                "path_table": path_table,
                "total_count": total_count,
            },
        )

    # send lxmf message
    @routes.post("/api/v1/lxmf-messages/send")
    async def lxmf_messages_send(request):
        from meshchatx.src.backend.demo_mode import demo_mode_block_response

        blocked = demo_mode_block_response(app)
        if blocked is not None:
            return blocked
        # get request body as json
        data = await request.json()

        if not isinstance(data, dict) or "lxmf_message" not in data:
            return web.json_response(
                {"message": "lxmf_message is required"},
                status=400,
            )
        lm = data["lxmf_message"]
        if not isinstance(lm, dict):
            return web.json_response(
                {"message": "lxmf_message must be an object"},
                status=400,
            )

        # get delivery method
        delivery_method = None
        if "delivery_method" in data:
            delivery_method = data["delivery_method"]

        try:
            destination_hash = lm["destination_hash"]
            content = lm["content"]
        except (KeyError, TypeError):
            return web.json_response(
                {"message": "destination_hash and content are required"},
                status=400,
            )

        raw_fields = lm.get("fields")
        fields = dict(raw_fields) if isinstance(raw_fields, dict) else {}
        app_extensions_payload = fields.pop("app_extensions", None)
        validated_app_extensions = (
            app_extensions_payload if isinstance(app_extensions_payload, dict) else None
        )

        image_field = None
        audio_field = None
        file_attachments_field = None
        telemetry_data = None
        commands = None

        try:
            if "image" in fields and isinstance(fields.get("image"), dict):
                image_bytes = base64.b64decode(fields["image"]["image_bytes"])
                detected = detect_image_format_from_magic(image_bytes)
                if detected is None or detected in {"webm", "tgs"}:
                    return web.json_response(
                        {"message": "Invalid image attachment"},
                        status=400,
                    )
                image_type = "jpg" if detected == "jpeg" else detected
                image_field = LxmfImageField(image_type, image_bytes)

            if "audio" in fields and isinstance(fields.get("audio"), dict):
                audio_mode = fields["audio"]["audio_mode"]
                audio_bytes = base64.b64decode(fields["audio"]["audio_bytes"])
                audio_field = LxmfAudioField(audio_mode, audio_bytes)

            if "file_attachments" in fields and isinstance(
                fields.get("file_attachments"),
                list,
            ):
                file_attachments = []
                for file_attachment in fields["file_attachments"]:
                    if not isinstance(file_attachment, dict):
                        continue
                    file_name = file_attachment["file_name"]
                    file_bytes = base64.b64decode(file_attachment["file_bytes"])
                    file_attachments.append(
                        LxmfFileAttachment(file_name, file_bytes),
                    )

                file_attachments_field = LxmfFileAttachmentsField(file_attachments)

            if "telemetry" in fields:
                telemetry_val = fields["telemetry"]
                if isinstance(telemetry_val, dict):
                    telemetry_data = Telemeter.pack(location=telemetry_val)
                elif isinstance(telemetry_val, str):
                    telemetry_data = base64.b64decode(telemetry_val)

            if "commands" in fields and isinstance(fields.get("commands"), list):
                commands = []
                for cmd in fields["commands"]:
                    new_cmd = {}
                    if not isinstance(cmd, dict):
                        continue
                    for k, v in cmd.items():
                        try:
                            if k.startswith("0x"):
                                new_cmd[int(k, 16)] = v
                            else:
                                new_cmd[int(k)] = v
                        except (ValueError, TypeError):
                            new_cmd[k] = v
                    commands.append(new_cmd)
        except (KeyError, TypeError, ValueError, binascii.Error):
            return web.json_response(
                {"message": "Invalid lxmf_message.fields"},
                status=400,
            )

        reply_to_hash = None
        if "reply_to_hash" in lm:
            reply_to_hash = lm["reply_to_hash"]
        reply_quoted_content = lm.get("reply_quoted_content") or None

        try:
            # send lxmf message to destination
            lxmf_message = await app.send_message(
                destination_hash=destination_hash,
                content=content,
                image_field=image_field,
                audio_field=audio_field,
                file_attachments_field=file_attachments_field,
                telemetry_data=telemetry_data,
                commands=commands,
                delivery_method=delivery_method,
                reply_to_hash=reply_to_hash,
                reply_quoted_content=reply_quoted_content,
                app_extensions=validated_app_extensions,
            )

            is_local_self = app._is_self_lxmf_destination(destination_hash)
            return web.json_response(
                {
                    "lxmf_message": convert_lxmf_message_to_dict(
                        lxmf_message,
                        include_attachments=False,
                        reticulum=app.reticulum,
                        message_router=app.current_context.message_router
                        if app.current_context
                        else None,
                        state_override="delivered" if is_local_self else None,
                        method_override="local" if is_local_self else None,
                    ),
                },
            )

        except Exception as e:
            detail = str(e).strip() or "Sending failed"
            status = 503
            if isinstance(e, (ValueError, LookupError)):
                status = 400
            elif isinstance(e, TimeoutError):
                status = 503
            body: dict[str, object] = {"message": detail}
            lower = detail.lower()
            failure_hint = None
            if "could not recall" in lower:
                failure_hint = "recall"
            elif "preferred propagation node configured" in lower:
                failure_hint = "no_propagation_node"
            elif "path to preferred propagation" in lower:
                failure_hint = "no_path_propagation_node"
            elif "no path" in lower:
                failure_hint = "no_path"
            elif "invalid destination" in lower:
                failure_hint = "invalid"
            elif status == 503:
                failure_hint = "router_error"
            ctx = app.current_context
            helptips_on = (
                ctx is not None
                and ctx.config is not None
                and ctx.config.delivery_helptips_enabled.get()
            )
            if helptips_on and destination_hash and status in (400, 503):
                from meshchatx.src.backend.delivery_diagnostics import (
                    build_delivery_diagnostics,
                )

                body["diagnostics"] = build_delivery_diagnostics(
                    app,
                    destination_hash,
                    failure_hint=failure_hint,
                )
            return web.json_response(body, status=status)

    @routes.post("/api/v1/lxmf-messages/reactions")
    async def lxmf_messages_reactions(request):
        data = await request.json()
        destination_hash = data.get("destination_hash")
        target_message_hash = data.get("target_message_hash")
        emoji = data.get("emoji", "")
        if not destination_hash or not target_message_hash or not emoji:
            return web.json_response(
                {
                    "message": "destination_hash, target_message_hash, and emoji are required",
                },
                status=422,
            )
        try:
            lxmf_message = await app.send_reaction(
                destination_hash=destination_hash,
                target_message_hash=target_message_hash,
                emoji=emoji,
            )
            return web.json_response(
                {
                    "lxmf_message": convert_lxmf_message_to_dict(
                        lxmf_message,
                        include_attachments=False,
                        reticulum=app.reticulum,
                        message_router=app.current_context.message_router
                        if app.current_context
                        else None,
                    ),
                },
            )
        except Exception as e:
            detail = str(e).strip() or "Reaction failed"
            status = 503
            if isinstance(e, (ValueError, LookupError)):
                status = 400
            elif isinstance(e, TimeoutError):
                status = 503
            return web.json_response(
                {
                    "message": detail,
                },
                status=status,
            )

    # cancel sending lxmf message

    # cancel sending lxmf message
    @routes.post("/api/v1/lxmf-messages/{hash}/cancel")
    async def lxmf_messages_cancel(request):
        # get path params
        message_hash = request.match_info.get("hash", None)

        # convert hash to bytes
        hash_as_bytes = bytes.fromhex(message_hash)

        # cancel outbound message by lxmf message hash
        app.message_router.cancel_outbound(hash_as_bytes)

        # get lxmf message from database
        lxmf_message = None
        db_lxmf_message = app.database.messages.get_lxmf_message_by_hash(
            message_hash,
        )
        if db_lxmf_message is not None:
            lxmf_message = convert_db_lxmf_message_to_dict(db_lxmf_message)

        return web.json_response(
            {
                "message": "ok",
                "lxmf_message": lxmf_message,
            },
        )

    # identify self on existing nomadnetwork link

    # delete lxmf message
    @routes.delete("/api/v1/lxmf-messages/{hash}")
    async def lxmf_messages_delete(request):
        # get path params
        message_hash = request.match_info.get("hash", None)

        # hash is required
        if message_hash is None:
            return web.json_response(
                {
                    "message": "hash is required",
                },
                status=422,
            )

        # delete lxmf messages from db where hash matches
        app.database.messages.delete_lxmf_message_by_hash(message_hash)

        return web.json_response(
            {
                "message": "ok",
            },
        )

    # serve lxmf messages for conversation

    # serve lxmf messages for conversation
    @routes.get("/api/v1/lxmf-messages/conversation/{destination_hash}")
    async def lxmf_messages_conversation(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")
        order = request.query.get("order", "asc")
        count = request.query.get("count")
        after_id = request.query.get("after_id")

        local_hash = app.local_lxmf_destination.hash.hex()

        try:
            results = await asyncio.to_thread(
                app.message_handler.get_conversation_messages,
                local_hash,
                destination_hash,
                limit=app.message_handler.clamp_conversation_messages_limit(count),
                after_id=after_id if order == "asc" else None,
                before_id=after_id if order == "desc" else None,
            )
        except Exception as e:
            RNS.log(f"Error in lxmf_messages_conversation: {e}", RNS.LOG_ERROR)
            status = 503 if sqlite_error_is_retryable(e) else 500
            return web.json_response(
                {
                    "message": (
                        "Database temporarily unavailable. Retry shortly."
                        if status == 503
                        else "Failed to load conversation"
                    ),
                },
                status=status,
            )

        # convert to response json
        lxmf_messages = [
            convert_db_lxmf_message_to_dict(db_lxmf_message)
            for db_lxmf_message in results
        ]

        return web.json_response(
            {
                "lxmf_messages": lxmf_messages,
            },
        )

    # fetch lxmf message attachment

    # fetch lxmf message attachment
    @routes.get("/api/v1/lxmf-messages/attachment/{message_hash}/{attachment_type}")
    async def lxmf_message_attachment(request):
        message_hash = request.match_info.get("message_hash")
        attachment_type = request.match_info.get("attachment_type")
        file_index = request.query.get("file_index")

        # find message from database
        db_lxmf_message = app.database.messages.get_lxmf_message_by_hash(
            message_hash,
        )
        if db_lxmf_message is None:
            return web.json_response({"message": "Message not found"}, status=404)

        from meshchatx.src.backend.lxmf_utils import parse_stored_lxmf_fields

        fields = parse_stored_lxmf_fields(db_lxmf_message["fields"])
        if fields is None:
            return web.json_response(
                {"message": "Invalid attachment data"},
                status=400,
            )

        # handle image
        if attachment_type == "image" and "image" in fields:
            image_field = fields["image"]
            if not isinstance(image_field, dict):
                return web.json_response(
                    {"message": "Invalid image attachment"},
                    status=400,
                )
            image_bytes_b64 = image_field.get("image_bytes")
            if not isinstance(image_bytes_b64, str) or not image_bytes_b64:
                return web.json_response(
                    {"message": "Missing image data"},
                    status=400,
                )
            try:
                image_data = base64.b64decode(image_bytes_b64)
            except Exception:
                return web.json_response(
                    {"message": "Invalid image data"},
                    status=400,
                )
            allowed_image_types = {"png", "jpeg", "jpg", "gif", "webp", "bmp"}
            detected = detect_image_format_from_magic(image_data)
            if detected is None or detected not in allowed_image_types:
                return web.json_response(
                    {"message": "Invalid image attachment"},
                    status=400,
                )
            # Serve Content-Type from magic bytes, not the peer-declared type.
            image_type = "jpeg" if detected == "jpeg" else detected
            return web.Response(body=image_data, content_type=f"image/{image_type}")

        # handle audio
        if attachment_type == "audio" and "audio" in fields:
            audio_field = fields["audio"]
            if not isinstance(audio_field, dict):
                return web.json_response(
                    {"message": "Invalid audio attachment"},
                    status=400,
                )
            audio_bytes_b64 = audio_field.get("audio_bytes")
            if not isinstance(audio_bytes_b64, str) or not audio_bytes_b64:
                return web.json_response(
                    {"message": "Missing audio data"},
                    status=400,
                )
            try:
                audio_data = base64.b64decode(audio_bytes_b64)
            except Exception:
                return web.json_response(
                    {"message": "Invalid audio data"},
                    status=400,
                )
            return web.Response(
                body=audio_data,
                content_type="application/octet-stream",
            )

        # handle file attachments
        if attachment_type == "file" and "file_attachments" in fields:
            if file_index is not None:
                try:
                    index = int(file_index)
                    if index < 0:
                        return web.json_response(
                            {"message": "Invalid file index"},
                            status=400,
                        )
                    file_attachments = fields["file_attachments"]
                    if not isinstance(file_attachments, list) or index >= len(
                        file_attachments,
                    ):
                        return web.json_response(
                            {"message": "Invalid file index"},
                            status=400,
                        )
                    file_attachment = file_attachments[index]
                    if not isinstance(file_attachment, dict):
                        return web.json_response(
                            {"message": "Invalid file attachment"},
                            status=400,
                        )
                    file_bytes_b64 = file_attachment.get("file_bytes")
                    if not isinstance(file_bytes_b64, str) or not file_bytes_b64:
                        return web.json_response(
                            {"message": "Missing file data"},
                            status=400,
                        )
                    try:
                        file_data = base64.b64decode(file_bytes_b64)
                    except Exception:
                        return web.json_response(
                            {"message": "Invalid file data"},
                            status=400,
                        )
                    raw_name = file_attachment.get("file_name") or "download"
                    if not isinstance(raw_name, str):
                        raw_name = "download"
                    safe_name = (
                        os.path.basename(raw_name)
                        .replace('"', "_")
                        .replace("\r", "")
                        .replace("\n", "")
                        .replace("\x00", "")
                    ) or "download"
                    return web.Response(
                        body=file_data,
                        content_type="application/octet-stream",
                        headers={
                            "Content-Disposition": f'attachment; filename="{safe_name}"',
                        },
                    )
                except (ValueError, IndexError):
                    pass

        return web.json_response({"message": "Attachment not found"}, status=404)

    @routes.get("/api/v1/lxmf-messages/{message_hash}/uri")
    async def lxmf_message_uri(request):
        """Build a reticulum:// URI; prefer the router cache over DB-only state."""
        from meshchatx.src.backend.meshchat_utils import (
            find_lxm_by_content_hash_for_paper_uri,
            hex_identifier_to_bytes,
            lxmf_message_try_paper_uri_string,
            normalized_meshchat_lxmf_message_hash_hex,
        )

        raw_hash = request.match_info.get("message_hash")
        nh = normalized_meshchat_lxmf_message_hash_hex(raw_hash)
        if not nh:
            return web.json_response(
                {"message": "Invalid message hash"},
                status=400,
            )
        hb = hex_identifier_to_bytes(nh)
        if hb is None:
            return web.json_response(
                {"message": "Invalid message hash"},
                status=400,
            )

        lxm = find_lxm_by_content_hash_for_paper_uri(app.message_router, hb)

        if not lxm:
            return web.json_response(
                {
                    "message": "Original message bytes not available for URI generation",
                },
                status=404,
            )

        uri, err_detail = lxmf_message_try_paper_uri_string(lxm)
        if not uri:
            body = {
                "message": "Could not serialize this LXMF payload as a Paper URI",
            }
            if err_detail:
                body["detail"] = err_detail
            return web.json_response(body, status=422)

        return web.json_response({"uri": uri})

    # delete lxmf messages for conversation

    # delete lxmf messages for conversation
    @routes.delete("/api/v1/lxmf-messages/conversation/{destination_hash}")
    async def lxmf_messages_conversation_delete(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # get source hash from local lxmf destination
        local_hash = app.local_lxmf_destination.hash.hex()

        for message_hash in app.database.messages.list_message_hashes_for_peer(
            destination_hash,
        ):
            try:
                app.message_router.cancel_outbound(bytes.fromhex(message_hash))
            except Exception:
                pass

        # delete lxmf messages from db where "source to destination" or "destination to source"
        app.message_handler.delete_conversation(local_hash, destination_hash)

        return web.json_response(
            {
                "message": "ok",
            },
        )

    @routes.get("/api/v1/lxmf/conversation-pins")
    async def lxmf_conversation_pins_get(request):
        peer_hashes = app.database.messages.get_pinned_peer_hashes()
        return web.json_response({"peer_hashes": peer_hashes})

    @routes.post("/api/v1/lxmf/conversation-pins/toggle")
    async def lxmf_conversation_pins_toggle(request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"message": "invalid json"}, status=400)
        destination_hash = (
            data.get("destination_hash") if isinstance(data, dict) else None
        )
        if not destination_hash:
            return web.json_response(
                {"message": "missing destination_hash"},
                status=400,
            )
        pinned = app.database.messages.toggle_peer_pin(destination_hash)
        return web.json_response(
            {
                "peer_hashes": app.database.messages.get_pinned_peer_hashes(),
                "pinned": pinned,
            },
        )

    # get lxmf conversations

    # get lxmf conversations
    @routes.get("/api/v1/lxmf/conversations")
    async def lxmf_conversations_get(request):
        not_ready = app._require_identity_context_ready()
        if not_ready is not None:
            return not_ready

        # get query params
        search_query = request.query.get("search", request.query.get("q", None))
        filter_unread = parse_bool_query_param(
            request.query.get(
                "unread",
                request.query.get("filter_unread", "false"),
            ),
        )
        filter_failed = parse_bool_query_param(
            request.query.get(
                "failed",
                request.query.get("filter_failed", "false"),
            ),
        )
        filter_has_attachments = parse_bool_query_param(
            request.query.get(
                "has_attachments",
                request.query.get("filter_has_attachments", "false"),
            ),
        )
        folder_id = request.query.get("folder_id")
        if folder_id is not None:
            try:
                folder_id = int(folder_id)
            except ValueError:
                folder_id = None

        # get pagination params
        try:
            limit = request.query.get("limit")
            limit = int(limit) if limit is not None else None
        except ValueError:
            limit = None
        limit = app.message_handler.clamp_conversations_limit(limit)

        try:
            offset = request.query.get("offset")
            offset = int(offset) if offset is not None else 0
        except ValueError:
            offset = 0

        try:
            local_hash = app.local_lxmf_destination.hexhash

            db_conversations = await asyncio.to_thread(
                app.message_handler.get_conversations,
                local_hash,
                search=search_query,
                filter_unread=filter_unread,
                filter_failed=filter_failed,
                filter_has_attachments=filter_has_attachments,
                folder_id=folder_id,
                limit=limit,
                offset=offset,
            )

            row_dicts = []
            peer_hashes = []
            for row in db_conversations:
                if not isinstance(row, dict):
                    row = dict(row)
                other_user_hash = row["peer_hash"]
                if app._lxmf_sieve_hides_peer(
                    other_user_hash,
                    message_title=row.get("title"),
                    message_content=row.get("content"),
                ):
                    continue
                row_dicts.append(row)
                peer_hashes.append(other_user_hash)

            tracking_states = await asyncio.to_thread(
                app.database.telemetry.get_tracking_states,
                peer_hashes,
            )
            viewed_map = {}
            if filter_unread:
                viewed_map = await asyncio.to_thread(
                    app.database.messages.get_notification_last_viewed_at_map,
                    peer_hashes,
                )

            conversations = []
            for row in row_dicts:
                other_user_hash = row["peer_hash"]

                display_name = None
                if row.get("peer_app_data"):
                    display_name = parse_lxmf_display_name(
                        app_data_base64=row["peer_app_data"],
                        default_value=None,
                    )
                if not display_name and row.get("contact_name"):
                    display_name = row["contact_name"]
                if not display_name:
                    display_name = "Anonymous Peer"

                # user icon
                user_icon = None
                if row.get("icon_name"):
                    user_icon = {
                        "icon_name": row["icon_name"],
                        "foreground_colour": row["foreground_colour"],
                        "background_colour": row["background_colour"],
                    }

                # contact image blob stays out of the list payload
                has_contact_image = bool(row.get("has_contact_image", 0))

                try:
                    is_unread = compute_lxmf_conversation_unread_from_latest_row(
                        row,
                    )
                except Exception:
                    is_unread = False

                # Add extra check for notification viewed state if unread
                if is_unread and filter_unread:
                    if app.database.messages.notification_viewed_covers(
                        viewed_map.get(other_user_hash),
                        row["timestamp"],
                    ):
                        is_unread = False
                        if filter_unread:
                            continue  # Skip this conversation if filtering unread and it's actually viewed

                has_attachments = bool(
                    row.get("has_attachments") in (1, True, "1")
                    or message_fields_have_attachments(row.get("fields")),
                )

                # add to conversations
                conversations.append(
                    {
                        "display_name": display_name,
                        "custom_display_name": row["custom_display_name"],
                        "contact_image": None,
                        "has_contact_image": has_contact_image,
                        "destination_hash": other_user_hash,
                        "is_unread": is_unread,
                        "is_tracking": tracking_states.get(other_user_hash, False),
                        "failed_messages_count": row["failed_count"],
                        "has_attachments": has_attachments,
                        "latest_message_title": row["title"],
                        "latest_message_preview": lxmf_sidebar_preview_for_conversation_latest_row(
                            row,
                            local_hash=local_hash,
                            peer_display_name=(
                                row.get("custom_display_name")
                                or display_name
                                or "Anonymous Peer"
                            ),
                        ),
                        "latest_message_created_at": row["created_at"],
                        "lxmf_user_icon": user_icon,
                        "is_contact": bool(row.get("is_contact", 0)),
                        "updated_at": row["created_at"],
                    },
                )

            return web.json_response(
                {
                    "conversations": conversations,
                },
            )
        except Exception as e:
            RNS.log(f"Error in lxmf_conversations_get: {e}", RNS.LOG_ERROR)
            status = 503 if sqlite_error_is_retryable(e) else 500
            return web.json_response(
                {
                    "message": (
                        "Database temporarily unavailable. Retry shortly."
                        if status == 503
                        else "Failed to load conversations"
                    ),
                },
                status=status,
            )

    @routes.get("/api/v1/lxmf/folders")
    async def lxmf_folders_get(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        try:
            folders = app.database.messages.get_all_folders()
            return web.json_response([dict(f) for f in folders])
        except Exception as e:
            return http_for_database_exception(e)

    @routes.post("/api/v1/lxmf/folders")
    async def lxmf_folders_post(request):
        data = await request.json()
        name = data.get("name")
        if not name:
            return web.json_response({"message": "Name is required"}, status=400)
        try:
            app.database.messages.create_folder(name)
            return web.json_response({"message": "Folder created"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.patch("/api/v1/lxmf/folders/{id}")
    async def lxmf_folders_patch(request):
        folder_id = int(request.match_info["id"])
        data = await request.json()
        name = data.get("name")
        if not name:
            return web.json_response({"message": "Name is required"}, status=400)
        app.database.messages.rename_folder(folder_id, name)
        return web.json_response({"message": "Folder renamed"})

    @routes.delete("/api/v1/lxmf/folders/{id}")
    async def lxmf_folders_delete(request):
        folder_id = int(request.match_info["id"])
        app.database.messages.delete_folder(folder_id)
        return web.json_response({"message": "Folder deleted"})

    @routes.get("/api/v1/lxmf/sieve-filters")
    async def lxmf_sieve_filters_get(request):
        raw = app.config.lxmf_sieve_filters_json.get()
        return web.json_response(
            {
                "filters": parse_lxmf_sieve_filters_json(raw),
            },
        )

    @routes.put("/api/v1/lxmf/sieve-filters")
    async def lxmf_sieve_filters_put(request):
        data = await request.json()
        filters = data.get("filters")
        if not isinstance(filters, list):
            return web.json_response(
                {"message": "filters must be a list"},
                status=400,
            )
        normalized = normalize_lxmf_sieve_filters(filters)
        folder_rows = app.database.messages.get_all_folders()
        valid_folder_ids = {f["id"] for f in folder_rows}
        for r in normalized:
            if r["action"] == "folder" and r["folder_id"] not in valid_folder_ids:
                return web.json_response(
                    {"message": f"Unknown folder_id {r['folder_id']}"},
                    status=400,
                )
        app.config.lxmf_sieve_filters_json.set(json.dumps(normalized))
        return web.json_response({"filters": normalized})

    @routes.post("/api/v1/lxmf/conversations/move-to-folder")
    async def lxmf_conversations_move_to_folder(request):
        data = await request.json()
        peer_hashes = data.get("peer_hashes", [])
        folder_id = data.get("folder_id")  # Can be None to remove from folder
        if not peer_hashes:
            return web.json_response(
                {"message": "peer_hashes is required"},
                status=400,
            )
        app.database.messages.move_conversations_to_folder(peer_hashes, folder_id)
        return web.json_response({"message": "Conversations moved"})

    @routes.post("/api/v1/lxmf/conversations/bulk-mark-as-read")
    async def lxmf_conversations_bulk_mark_read(request):
        data = await request.json()
        mark_all = bool(data.get("mark_all"))
        destination_hashes = data.get("destination_hashes", [])
        if mark_all:
            app.database.messages.mark_all_conversations_as_read()
            app.database.messages.mark_all_notifications_as_viewed()
            return web.json_response(
                {"message": "All conversations marked as read"},
            )
        if not destination_hashes:
            return web.json_response(
                {"message": "destination_hashes is required"},
                status=400,
            )
        app.database.messages.mark_conversations_as_read(destination_hashes)
        # Keep notification viewed state in sync so the bell never
        # disagrees with the conversation list.
        app.database.messages.mark_all_notifications_as_viewed(destination_hashes)
        return web.json_response({"message": "Conversations marked as read"})

    @routes.post("/api/v1/lxmf/conversations/bulk-delete")
    async def lxmf_conversations_bulk_delete(request):
        data = await request.json()
        destination_hashes = data.get("destination_hashes", [])
        if not destination_hashes:
            return web.json_response(
                {"message": "destination_hashes is required"},
                status=400,
            )
        local_hash = app.local_lxmf_destination.hexhash
        for dest_hash in destination_hashes:
            for message_hash in app.database.messages.list_message_hashes_for_peer(
                dest_hash,
            ):
                try:
                    app.message_router.cancel_outbound(bytes.fromhex(message_hash))
                except Exception:
                    pass
            app.message_handler.delete_conversation(local_hash, dest_hash)
        return web.json_response({"message": "Conversations deleted"})

    @routes.get("/api/v1/lxmf/folders/export")
    async def lxmf_folders_export(request):
        folders = [dict(f) for f in app.database.messages.get_all_folders()]
        mappings = [
            dict(m) for m in app.database.messages.get_all_conversation_folders()
        ]
        return web.json_response({"folders": folders, "mappings": mappings})

    @routes.post("/api/v1/lxmf/folders/import")
    async def lxmf_folders_import(request):
        data = await request.json()
        folders = data.get("folders", [])
        mappings = data.get("mappings", [])

        # We'll try to recreate folders by name to avoid ID conflicts
        folder_name_to_new_id = {}
        for f in folders:
            try:
                app.database.messages.create_folder(f["name"])
            except Exception as e:
                logger.debug(f"Folder '{f['name']}' likely already exists: {e}")

        # Refresh folder list to get new IDs
        all_folders = app.database.messages.get_all_folders()
        for f in all_folders:
            folder_name_to_new_id[f["name"]] = f["id"]

        # Map old IDs to new IDs if possible, or just use names if we had them
        # Since IDs might change, we should have exported names too
        # Let's assume the export had folder names in mappings or we match by old folder info
        old_id_to_name = {f["id"]: f["name"] for f in folders}

        for m in mappings:
            peer_hash = m["peer_hash"]
            old_folder_id = m["folder_id"]
            folder_name = old_id_to_name.get(old_folder_id)
            if folder_name and folder_name in folder_name_to_new_id:
                new_folder_id = folder_name_to_new_id[folder_name]
                app.database.messages.move_conversation_to_folder(
                    peer_hash,
                    new_folder_id,
                )

        return web.json_response({"message": "Folders and mappings imported"})

    # mark lxmf conversation as read

    # mark lxmf conversation as read
    @routes.post("/api/v1/lxmf/conversations/{destination_hash}/mark-as-read")
    async def lxmf_conversations_mark_read(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # mark lxmf conversation as read
        app.database.messages.mark_conversation_as_read(destination_hash)
        # Keep notification viewed state in sync so the bell never
        # disagrees with the conversation list.
        app.database.messages.mark_notification_as_viewed(destination_hash)

        return web.json_response(
            {
                "message": "ok",
            },
        )

    # mark notifications as viewed
