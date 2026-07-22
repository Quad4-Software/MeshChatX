# SPDX-License-Identifier: 0BSD
"""HTTP routes: path_probe."""

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


def register_path_probe_routes(routes, app):

    # get path to destination
    @routes.get("/api/v1/destination/{destination_hash}/path")
    async def destination_path(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # convert destination hash to bytes
        destination_hash = bytes.fromhex(destination_hash)
        destination_hash_hex = destination_hash.hex()
        local_hashes: set[str] = set()
        with contextlib.suppress(Exception):
            if app.current_context and app.current_context.identity:
                local_hashes.add(app.current_context.identity.hash.hex())
        with contextlib.suppress(Exception):
            if app.local_lxmf_destination is not None:
                local_hashes.add(app.local_lxmf_destination.hash.hex())
        with contextlib.suppress(Exception):
            if app.current_context and app.current_context.message_router:
                pdest = app.current_context.message_router.propagation_destination
                if pdest is not None and getattr(pdest, "hash", None):
                    local_hashes.add(pdest.hash.hex())

        if destination_hash_hex in local_hashes:
            return web.json_response(
                {
                    "path": {
                        "hops": 0,
                        "next_hop": destination_hash_hex,
                        "next_hop_interface": "Local",
                    },
                    "path_stale": False,
                    "path_unresponsive": False,
                },
            )

        # check if user wants to request the path from the network right now
        request_query_param = request.query.get("request", "false")
        should_request_now = request_query_param in ("true", "1")
        if should_request_now:
            # determine how long we should wait for a path response
            timeout_seconds = int(request.query.get("timeout", 15))
            timeout_after_seconds = time.time() + timeout_seconds

            reticulum = app.reticulum if hasattr(app, "reticulum") else None
            reticulum_pathfinding.prepare_fresh_path_request(
                reticulum,
                destination_hash,
            )

            # wait until we have a path, or give up after the configured timeout
            while (
                not RNS.Transport.has_path(destination_hash)
                and time.time() < timeout_after_seconds
            ):
                await asyncio.sleep(0.1)

        # ensure path is known
        if not RNS.Transport.has_path(destination_hash):
            pm = reticulum_pathfinding.path_metadata_for_api(destination_hash)
            return web.json_response(
                {
                    "path": None,
                    **pm,
                },
            )

        # determine next hop and hop count
        hops = RNS.Transport.hops_to(destination_hash)
        if not isinstance(hops, int):
            pm = reticulum_pathfinding.path_metadata_for_api(destination_hash)
            return web.json_response(
                {
                    "path": None,
                    **pm,
                },
            )
        next_hop_bytes = None
        if hasattr(app, "reticulum") and app.reticulum:
            next_hop_bytes = app.reticulum.get_next_hop(destination_hash)
        if next_hop_bytes is not None and not isinstance(
            next_hop_bytes,
            (bytes, bytearray),
        ):
            next_hop_bytes = None

        # ensure next hop provided
        if next_hop_bytes is None:
            pm = reticulum_pathfinding.path_metadata_for_api(destination_hash)
            return web.json_response(
                {
                    "path": None,
                    **pm,
                },
            )

        next_hop = next_hop_bytes.hex()
        next_hop_interface = (
            app.reticulum.get_next_hop_if_name(destination_hash)
            if hasattr(app, "reticulum") and app.reticulum
            else None
        )

        pm = reticulum_pathfinding.path_metadata_for_api(destination_hash)
        return web.json_response(
            {
                "path": {
                    "hops": hops,
                    "next_hop": next_hop,
                    "next_hop_interface": next_hop_interface,
                },
                **pm,
            },
        )

    # drop path to destination

    # drop path to destination
    @routes.post("/api/v1/destination/{destination_hash}/drop-path")
    async def destination_drop_path(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # convert destination hash to bytes
        destination_hash = bytes.fromhex(destination_hash)

        # drop path
        if hasattr(app, "reticulum") and app.reticulum:
            app.reticulum.drop_path(destination_hash)

        return web.json_response(
            {
                "message": "Path has been dropped",
            },
        )

    # proactively ask Reticulum to resolve or refresh path (non-blocking HTTP, and discovery runs in background)

    # proactively ask Reticulum to resolve or refresh path (non-blocking HTTP, and discovery runs in background)
    @routes.post("/api/v1/destination/{destination_hash}/request-path")
    async def destination_request_path_fire(request):
        destination_hash = request.match_info.get("destination_hash", "")
        try:
            destination_hash_bytes = bytes.fromhex(destination_hash)
        except Exception:
            return web.json_response(
                {
                    "message": "invalid destination hash",
                },
                status=400,
            )
        reticulum = app.reticulum if hasattr(app, "reticulum") else None
        reticulum_pathfinding.prepare_fresh_path_request(
            reticulum,
            destination_hash_bytes,
        )

        # if path is already available, resend failed messages for this destination
        if RNS.Transport.has_path(destination_hash_bytes):
            for _ctx in list(app.contexts.values()):
                if (
                    _ctx.running
                    and _ctx.config.auto_resend_failed_messages_when_announce_received.get()
                ):
                    AsyncUtils.run_async(
                        app.resend_failed_messages_for_destination(
                            destination_hash,
                            context=_ctx,
                        ),
                    )

        return web.json_response(
            {
                "message": "ok",
            },
        )

    # get signal metrics for a destination by checking the latest announce or lxmf message received from them

    # get signal metrics for a destination by checking the latest announce or lxmf message received from them
    @routes.get("/api/v1/destination/{destination_hash}/signal-metrics")
    async def destination_signal_metrics(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # signal metrics to return
        snr = None
        rssi = None
        quality = None
        updated_at = None

        # get latest announce from database for the provided destination hash
        latest_announce = app.database.announces.get_announce_by_hash(
            destination_hash,
        )

        # get latest lxmf message from database sent to us from the provided destination hash
        local_hash = app.local_lxmf_destination.hexhash
        messages = app.message_handler.get_conversation_messages(
            local_hash,
            destination_hash,
            limit=1,
        )
        # Filter for incoming messages only
        latest_lxmf_message = next(
            (m for m in messages if m["source_hash"] == destination_hash),
            None,
        )

        # determine when latest announce was received
        latest_announce_at = None
        if latest_announce is not None:
            latest_announce_at = datetime.fromisoformat(
                latest_announce["updated_at"],
            )
            if latest_announce_at.tzinfo is not None:
                latest_announce_at = latest_announce_at.replace(tzinfo=None)

        # determine when latest lxmf message was received
        latest_lxmf_message_at = None
        if latest_lxmf_message is not None:
            latest_lxmf_message_at = datetime.fromisoformat(
                latest_lxmf_message["created_at"],
            )
            if latest_lxmf_message_at.tzinfo is not None:
                latest_lxmf_message_at = latest_lxmf_message_at.replace(tzinfo=None)

        # get signal metrics from latest announce
        if latest_announce is not None:
            snr = latest_announce["snr"]
            rssi = latest_announce["rssi"]
            quality = latest_announce["quality"]
            # using updated_at from announce because this is when the latest announce was received
            updated_at = latest_announce["updated_at"]

        # get signal metrics from latest lxmf message if it's more recent than the announce
        if latest_lxmf_message is not None and (
            latest_announce_at is None or latest_lxmf_message_at > latest_announce_at
        ):
            snr = latest_lxmf_message["snr"]
            rssi = latest_lxmf_message["rssi"]
            quality = latest_lxmf_message["quality"]
            # using created_at from lxmf message because this is when the message was received
            updated_at = latest_lxmf_message["created_at"]

        return web.json_response(
            {
                "signal_metrics": {
                    "snr": snr,
                    "rssi": rssi,
                    "quality": quality,
                    "updated_at": updated_at,
                },
            },
        )

    # pings an lxmf.delivery destination by sending empty data and waiting for the recipient to send a proof back
    # the lxmf router proves all received packets, then drops them if they can't be decoded as lxmf messages
    # this allows us to ping/probe any active lxmf.delivery destination and get rtt/snr/rssi data on demand
    # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L234
    # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L1374

    # pings an lxmf.delivery destination by sending empty data and waiting for the recipient to send a proof back
    # the lxmf router proves all received packets, then drops them if they can't be decoded as lxmf messages
    # this allows us to ping/probe any active lxmf.delivery destination and get rtt/snr/rssi data on demand
    # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L234
    # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L1374
    @routes.get("/api/v1/ping/{destination_hash}/lxmf.delivery")
    async def ping_lxmf_delivery(request):
        # get path params
        destination_hash_str = request.match_info.get("destination_hash", "")

        try:
            destination_hash = bytes.fromhex(destination_hash_str)
        except Exception:
            return web.json_response(
                {"message": "Ping failed. Invalid destination hash."},
                status=400,
            )

        try:
            timeout_seconds = int(request.query.get("timeout", 15))
        except (TypeError, ValueError):
            return web.json_response(
                {"message": "Ping failed. Timeout must be an integer."},
                status=400,
            )
        if timeout_seconds < 1:
            return web.json_response(
                {"message": "Ping failed. Timeout must be at least 1 second."},
                status=400,
            )

        # Split the budget so path discovery cannot consume the whole timeout.
        path_budget_seconds = max(1, timeout_seconds // 2)
        delivery_budget_seconds = max(1, timeout_seconds - path_budget_seconds)
        path_deadline = time.time() + path_budget_seconds

        # request path if we don't have it
        if not RNS.Transport.has_path(destination_hash):
            RNS.Transport.request_path(destination_hash)

        # wait until we have a path, or give up after the path budget
        while (
            not RNS.Transport.has_path(destination_hash) and time.time() < path_deadline
        ):
            await asyncio.sleep(0.1)

        if not RNS.Transport.has_path(destination_hash):
            return web.json_response(
                {
                    "message": "Ping failed. Could not find path to destination.",
                },
                status=503,
            )

        # find destination identity (pass string hash, not bytes)
        destination_identity = app.recall_identity(destination_hash_str)
        if destination_identity is None:
            return web.json_response(
                {
                    "message": "Ping failed. Could not recall destination identity.",
                },
                status=503,
            )

        # create outbound destination
        request_destination = RNS.Destination(
            destination_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        # send empty packet to destination
        packet = RNS.Packet(request_destination, b"")
        receipt = packet.send()

        delivery_deadline = time.time() + delivery_budget_seconds
        # wait until delivered, or give up after the delivery budget
        while (
            receipt.status != RNS.PacketReceipt.DELIVERED
            and time.time() < delivery_deadline
        ):
            await asyncio.sleep(0.1)

        # ping failed if not delivered
        if receipt.status != RNS.PacketReceipt.DELIVERED:
            return web.json_response(
                {
                    "message": f"Ping failed. Timed out after {timeout_seconds} seconds.",
                },
                status=503,
            )

        # get number of hops to destination and back from destination
        hops_there = RNS.Transport.hops_to(destination_hash)
        hops_back = receipt.proof_packet.hops

        # get rssi
        rssi = receipt.proof_packet.rssi
        if rssi is None and hasattr(app, "reticulum") and app.reticulum:
            rssi = app.reticulum.get_packet_rssi(receipt.proof_packet.packet_hash)

        # get snr
        snr = receipt.proof_packet.snr
        if snr is None and hasattr(app, "reticulum") and app.reticulum:
            snr = app.reticulum.get_packet_snr(receipt.proof_packet.packet_hash)

        # get signal quality
        quality = receipt.proof_packet.q
        if quality is None and hasattr(app, "reticulum") and app.reticulum:
            quality = app.reticulum.get_packet_q(receipt.proof_packet.packet_hash)

        # get and format round trip time
        rtt = receipt.get_rtt()
        rtt_milliseconds = round(rtt * 1000, 3)
        rtt_duration_string = f"{rtt_milliseconds} ms"

        # resend any previously failed messages to this destination now that path is available
        for _ctx in list(app.contexts.values()):
            if (
                _ctx.running
                and _ctx.config.auto_resend_failed_messages_when_announce_received.get()
            ):
                AsyncUtils.run_async(
                    app.resend_failed_messages_for_destination(
                        destination_hash_str,
                        context=_ctx,
                    ),
                )

        return web.json_response(
            {
                "message": f"Valid reply from {receipt.destination.hash.hex()}\nDuration: {rtt_duration_string}\nHops There: {hops_there}\nHops Back: {hops_back}",
                "ping_result": {
                    "rtt": rtt,
                    "hops_there": hops_there,
                    "hops_back": hops_back,
                    "rssi": rssi,
                    "snr": snr,
                    "quality": quality,
                    "receiving_interface": str(
                        receipt.proof_packet.receiving_interface,
                    ),
                },
            },
        )

    # get path table
    @routes.get("/api/v1/path-table")
    @routes.post("/api/v1/path-table")
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
