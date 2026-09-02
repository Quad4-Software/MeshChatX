# SPDX-License-Identifier: 0BSD
"""HTTP routes: messages."""

from __future__ import annotations

from meshchatx.src.backend.database.sqlite_errors import sqlite_error_is_retryable
from meshchatx.src.backend.delivery_diagnostics import build_delivery_diagnostics
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


def register_messages_routes(routes, app):

    # get custom destination display name
    @routes.get("/api/v1/destination/{destination_hash}/custom-display-name")
    async def destination_custom_display_name_get(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        return web.json_response(
            {
                "custom_display_name": app.get_custom_destination_display_name(
                    destination_hash,
                ),
            },
        )

    # set custom destination display name

    # set custom destination display name
    @routes.post(
        "/api/v1/destination/{destination_hash}/custom-display-name/update",
    )
    async def destination_custom_display_name_update(request):
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

        # update display name if provided
        if len(display_name) > 0:
            app.database.announces.upsert_custom_display_name(
                destination_hash,
                display_name,
            )
            return web.json_response(
                {
                    "message": "Custom display name has been updated",
                },
            )

        # otherwise remove display name
        app.database.announces.delete_custom_display_name(destination_hash)
        return web.json_response(
            {
                "message": "Custom display name has been removed",
            },
        )

    # get lxmf stamp cost for the provided lxmf.delivery destination hash

    # get lxmf stamp cost for the provided lxmf.delivery destination hash
    @routes.get("/api/v1/destination/{destination_hash}/lxmf-stamp-info")
    async def destination_lxmf_stamp_info(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # convert destination hash to bytes
        try:
            destination_hash_bytes = bytes.fromhex(destination_hash)
        except (TypeError, ValueError):
            return web.json_response(
                {"message": "invalid destination_hash"},
                status=400,
            )

        # get lxmf stamp cost from announce in database
        lxmf_stamp_cost = None
        announce = app.database.announces.get_announce_by_hash(destination_hash)
        if announce is not None:
            lxmf_stamp_cost = parse_lxmf_stamp_cost(
                announce["app_data"],
            )

        # get outbound ticket expiry for this lxmf destination
        lxmf_outbound_ticket_expiry = app.message_router.get_outbound_ticket_expiry(
            destination_hash_bytes,
        )
        if lxmf_outbound_ticket_expiry is not None and not isinstance(
            lxmf_outbound_ticket_expiry,
            (int, float),
        ):
            lxmf_outbound_ticket_expiry = None

        return web.json_response(
            {
                "lxmf_stamp_info": {
                    "stamp_cost": lxmf_stamp_cost,
                    "outbound_ticket_expiry": lxmf_outbound_ticket_expiry,
                },
            },
        )

    @routes.get("/api/v1/destination/{destination_hash}/delivery-diagnostics")
    async def destination_delivery_diagnostics(request):
        destination_hash = request.match_info.get("destination_hash", "")
        if not destination_hash:
            return web.json_response(
                {"message": "destination_hash is required"},
                status=400,
            )
        return web.json_response(
            build_delivery_diagnostics(app, destination_hash),
        )

    # get interface stats

    # mark notifications as viewed
    @routes.post("/api/v1/notifications/mark-as-viewed")
    async def notifications_mark_as_viewed(request):
        data = await request.json()
        destination_hashes = data.get("destination_hashes", [])
        notification_ids = data.get("notification_ids", [])

        if destination_hashes:
            # mark LXMF conversations as viewed
            app.database.messages.mark_all_notifications_as_viewed(
                destination_hashes,
            )
            # Keep conversation read state in sync
            app.database.messages.mark_conversations_as_read(destination_hashes)
        else:
            # mark all LXMF conversations as viewed if no hashes provided
            # (this happens when "Clear All" is clicked)
            app.database.messages.mark_all_notifications_as_viewed()
            # Also mark all conversations as read
            app.database.messages.mark_all_conversations_as_read()

        if notification_ids:
            # mark system notifications as viewed
            app.database.misc.mark_notifications_as_viewed(notification_ids)
        else:
            # mark all system notifications as viewed if no ids provided
            app.database.misc.mark_notifications_as_viewed()

        return web.json_response(
            {
                "message": "ok",
            },
        )

    @routes.get("/api/v1/notifications")
    async def notifications_get(request):
        not_ready = app._require_identity_context_ready()
        if not_ready is not None:
            return not_ready
        try:
            filter_unread = parse_bool_query_param(
                request.query.get("unread", "false"),
            )
            try:
                limit = int(request.query.get("limit", 50))
            except (TypeError, ValueError):
                limit = 50
            if limit < 0:
                limit = 0
            elif limit > 500:
                limit = 500

            # 1. Fetch system notifications
            system_notifications = app.database.misc.get_notifications(
                filter_unread=filter_unread,
                limit=limit,
            )

            # 2. Fetch unread LXMF conversations if requested
            conversations = []
            user_facing_peer_hashes = set()
            total_unread_peer_hashes = set()
            if filter_unread:
                local_hash = app.local_lxmf_destination.hexhash
                db_conversations = app.message_handler.get_conversations(
                    local_hash,
                    filter_unread=True,
                )
                conv_rows = [
                    dict(db_message) if not isinstance(db_message, dict) else db_message
                    for db_message in db_conversations
                ]
                peer_hashes = []
                for db_message in conv_rows:
                    if db_message["source_hash"] == local_hash:
                        peer_hashes.append(db_message["destination_hash"])
                    else:
                        peer_hashes.append(db_message["source_hash"])
                viewed_map = app.database.messages.get_notification_last_viewed_at_map(
                    peer_hashes,
                )
                for db_message in conv_rows:
                    # determine other user hash
                    if db_message["source_hash"] == local_hash:
                        other_user_hash = db_message["destination_hash"]
                    else:
                        other_user_hash = db_message["source_hash"]

                    if not app._lxmf_sieve_suppresses_notifications(
                        other_user_hash,
                        message_title=db_message.get("title"),
                        message_content=db_message.get("content"),
                    ):
                        if not app.database.messages.notification_viewed_covers(
                            viewed_map.get(other_user_hash),
                            db_message["timestamp"],
                        ):
                            total_unread_peer_hashes.add(other_user_hash)

                    latest_for_preview = db_message
                    if not is_user_facing_lxmf_payload(
                        db_message.get("fields"),
                        db_message.get("content"),
                        db_message.get("title"),
                    ):
                        latest_user_facing = app.database.messages.get_latest_user_facing_incoming_message(
                            other_user_hash,
                        )
                        if latest_user_facing is None:
                            continue
                        # Compare against last_read_at on the original row
                        last_read_at_raw = db_message.get("last_read_at")
                        if last_read_at_raw:
                            try:
                                last_read_dt = datetime.fromisoformat(
                                    last_read_at_raw,
                                )
                                if last_read_dt.tzinfo is None:
                                    last_read_dt = last_read_dt.replace(
                                        tzinfo=UTC,
                                    )
                                if (
                                    latest_user_facing["timestamp"]
                                    <= last_read_dt.timestamp()
                                ):
                                    continue
                            except (ValueError, TypeError):
                                pass
                        latest_for_preview = latest_user_facing

                    if app._lxmf_sieve_suppresses_notifications(
                        other_user_hash,
                        message_title=latest_for_preview.get("title"),
                        message_content=latest_for_preview.get("content"),
                    ):
                        continue

                    # Check if notification has been viewed
                    if app.database.messages.notification_viewed_covers(
                        viewed_map.get(other_user_hash),
                        latest_for_preview["timestamp"],
                    ):
                        continue

                    user_facing_peer_hashes.add(other_user_hash)

                    # Determine display name
                    display_name = app.get_lxmf_conversation_name(
                        other_user_hash,
                    )
                    custom_display_name = (
                        app.database.announces.get_custom_display_name(
                            other_user_hash,
                        )
                    )

                    # Determine latest message data
                    latest_message_data = {
                        "content": latest_for_preview.get("content", ""),
                        "timestamp": latest_for_preview.get("timestamp", 0),
                        "is_incoming": latest_for_preview.get("is_incoming") == 1,
                    }

                    icon = app.database.misc.get_user_icon(other_user_hash)

                    peer_preview_name = (
                        custom_display_name or display_name or "Anonymous Peer"
                    )

                    conversations.append(
                        {
                            "type": "lxmf_message",
                            "destination_hash": other_user_hash,
                            "display_name": display_name,
                            "custom_display_name": custom_display_name,
                            "lxmf_user_icon": dict(icon) if icon else None,
                            "latest_message_preview": (
                                lxmf_sidebar_preview_for_conversation_latest_row(
                                    dict(latest_for_preview),
                                    local_hash=local_hash,
                                    peer_display_name=peer_preview_name,
                                )[:100]
                            ),
                            "updated_at": datetime.fromtimestamp(
                                latest_message_data["timestamp"] or 0,
                                UTC,
                            ).isoformat(),
                        },
                    )

            # Combine and sort by timestamp
            all_notifications = []

            for n in system_notifications:
                # Convert to dict if needed
                if not isinstance(n, dict):
                    n = dict(n)

                # Get remote user info if possible
                display_name = "Unknown"
                icon = None
                if n["type"] == "rrc_mention":
                    display_name = n.get("title") or "Relay Chat"
                elif n["remote_hash"]:
                    # Try to find associated LXMF hash for telephony identity hash
                    lxmf_hash = app.get_lxmf_destination_hash_for_identity_hash(
                        n["remote_hash"],
                    )
                    if not lxmf_hash:
                        # Fallback to direct name lookup by identity hash
                        display_name = (
                            app.get_name_for_identity_hash(n["remote_hash"])
                            or n["remote_hash"]
                        )
                    else:
                        display_name = app.get_lxmf_conversation_name(
                            lxmf_hash,
                        )
                        icon = app.database.misc.get_user_icon(lxmf_hash)

                all_notifications.append(
                    {
                        "id": n["id"],
                        "type": n["type"],
                        "destination_hash": n["remote_hash"],
                        "display_name": display_name,
                        "lxmf_user_icon": dict(icon) if icon else None,
                        "title": n["title"],
                        "content": n["content"],
                        "is_viewed": n["is_viewed"] == 1,
                        "updated_at": datetime.fromtimestamp(
                            n["timestamp"] or 0,
                            UTC,
                        ).isoformat(),
                    },
                )

            all_notifications.extend(conversations)

            # Sort by updated_at descending
            all_notifications.sort(key=lambda x: x["updated_at"], reverse=True)

            # Calculate actual unread count
            unread_count = app.database.misc.get_unread_notification_count()

            # Add LXMF unread count using the same user-facing filter as
            # the listing above so the badge can never disagree with the
            # dropdown contents (no false bell triggers from reactions,
            # telemetry, icon updates, or empty payloads).
            lxmf_unread_count = 0
            lxmf_total_unread_count = 0
            local_hash = app.local_lxmf_destination.hexhash
            if filter_unread:
                # Already computed during the listing pass.
                lxmf_unread_count = len(user_facing_peer_hashes)
                lxmf_total_unread_count = len(total_unread_peer_hashes)
            else:
                unread_conversations = app.message_handler.get_conversations(
                    local_hash,
                    filter_unread=True,
                )
                count_rows = [
                    dict(conv) if not isinstance(conv, dict) else conv
                    for conv in unread_conversations or []
                ]
                count_hashes = []
                for conv in count_rows:
                    if conv["source_hash"] == local_hash:
                        count_hashes.append(conv["destination_hash"])
                    else:
                        count_hashes.append(conv["source_hash"])
                viewed_map = app.database.messages.get_notification_last_viewed_at_map(
                    count_hashes,
                )
                for conv in count_rows:
                    if conv["source_hash"] == local_hash:
                        other_user_hash = conv["destination_hash"]
                    else:
                        other_user_hash = conv["source_hash"]

                    # Total unread count (regardless of user-facing)
                    if not app._lxmf_sieve_suppresses_notifications(
                        other_user_hash,
                        message_title=conv.get("title"),
                        message_content=conv.get("content"),
                    ):
                        if not app.database.messages.notification_viewed_covers(
                            viewed_map.get(other_user_hash),
                            conv["timestamp"],
                        ):
                            lxmf_total_unread_count += 1

                    latest_for_check = conv
                    if not is_user_facing_lxmf_payload(
                        conv.get("fields"),
                        conv.get("content"),
                        conv.get("title"),
                    ):
                        latest_user_facing = app.database.messages.get_latest_user_facing_incoming_message(
                            other_user_hash,
                        )
                        if latest_user_facing is None:
                            continue
                        last_read_at_raw = conv.get("last_read_at")
                        if last_read_at_raw:
                            try:
                                last_read_dt = datetime.fromisoformat(
                                    last_read_at_raw,
                                )
                                if last_read_dt.tzinfo is None:
                                    last_read_dt = last_read_dt.replace(
                                        tzinfo=UTC,
                                    )
                                if (
                                    latest_user_facing["timestamp"]
                                    <= last_read_dt.timestamp()
                                ):
                                    continue
                            except (ValueError, TypeError):
                                pass
                        latest_for_check = latest_user_facing

                    if app._lxmf_sieve_suppresses_notifications(
                        other_user_hash,
                        message_title=latest_for_check.get("title"),
                        message_content=latest_for_check.get("content"),
                    ):
                        continue

                    if not app.database.messages.notification_viewed_covers(
                        viewed_map.get(other_user_hash),
                        latest_for_check["timestamp"],
                    ):
                        lxmf_unread_count += 1

            total_unread_count = unread_count + lxmf_unread_count

            return web.json_response(
                {
                    "notifications": all_notifications[:limit],
                    "unread_count": total_unread_count,
                    "lxmf_total_unread_count": lxmf_total_unread_count,
                },
            )
        except Exception as e:
            RNS.log(f"Error in notifications_get: {e}", RNS.LOG_ERROR)
            status = 503 if sqlite_error_is_retryable(e) else 500
            return web.json_response(
                {
                    "error": (
                        "Database temporarily unavailable. Retry shortly."
                        if status == 503
                        else "Internal error"
                    ),
                },
                status=status,
            )

    # get blocked destinations
