# SPDX-License-Identifier: 0BSD
"""WebSocket handlers: handlers_lxmf."""

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


async def handle_lxmf_forwarding_rules_get(app, client, data):
    rules = app.database.misc.get_forwarding_rules()
    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": "lxmf.forwarding.rules",
                    "rules": [
                        {
                            "id": rule["id"],
                            "name": rule.get("name") or "",
                            "identity_hash": rule["identity_hash"],
                            "forward_to_hash": rule["forward_to_hash"],
                            "source_filter_hash": rule["source_filter_hash"],
                            "is_active": bool(rule["is_active"]),
                        }
                        for rule in rules
                    ],
                },
            ),
        ),
    )


async def handle_lxmf_forwarding_rule_add(app, client, data):
    rule_data = data.get("rule")
    if not rule_data or "forward_to_hash" not in rule_data:
        print(
            "Missing rule data or forward_to_hash in lxmf.forwarding.rule.add",
        )
        return

    app.database.misc.create_forwarding_rule(
        identity_hash=rule_data.get("identity_hash"),
        forward_to_hash=rule_data["forward_to_hash"],
        source_filter_hash=rule_data.get("source_filter_hash"),
        is_active=rule_data.get("is_active", True),
        name=rule_data.get("name"),
    )
    # notify updated
    AsyncUtils.run_async(
        app.on_websocket_data_received(
            client,
            {"type": "lxmf.forwarding.rules.get"},
        ),
    )


async def handle_lxmf_forwarding_rule_delete(app, client, data):
    rule_id = data.get("id")
    if rule_id is not None:
        app.database.misc.delete_forwarding_rule(rule_id)
        # notify updated
        AsyncUtils.run_async(
            app.on_websocket_data_received(
                client,
                {"type": "lxmf.forwarding.rules.get"},
            ),
        )


async def handle_lxmf_forwarding_rule_toggle(app, client, data):
    rule_id = data.get("id")
    if rule_id is not None:
        app.database.misc.toggle_forwarding_rule(rule_id)
        # notify updated
        AsyncUtils.run_async(
            app.on_websocket_data_received(
                client,
                {"type": "lxmf.forwarding.rules.get"},
            ),
        )

    # handle ingesting an lxmf uri (paper message)


async def handle_lxm_ingest_uri(app, client, data):
    uri = data.get("uri")
    if not uri:
        return

    local_delivery_signal = "local_delivery_occurred"
    duplicate_signal = "duplicate_lxm"

    try:
        uri_raw = uri.strip()
        lu = uri_raw.lower()
        if lu.startswith("meshchatx://map") or lu.startswith("meshchat://map"):
            from urllib.parse import parse_qsl, urlparse

            parsed = urlparse(uri_raw)
            q = dict(parse_qsl(parsed.query, keep_blank_values=True))
            try:
                lat = float(q.get("lat", "") or "")
                lon = float(q.get("lon", "") or "")
            except (TypeError, ValueError):
                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "lxm.ingest_uri.result",
                                "status": "error",
                                "message": "Invalid map link: lat and lon must be numbers.",
                            },
                        ),
                    ),
                )
                return
            zraw = q.get("z") or q.get("zoom") or "10"
            try:
                zoom = int(float(zraw))
            except (TypeError, ValueError):
                zoom = 10
            zoom = max(0, min(22, zoom))
            layers = (q.get("layers") or "").strip()
            label = (q.get("label") or "").strip()
            mq = {
                "lat": lat,
                "lon": lon,
                "zoom": zoom,
            }
            if layers:
                mq["layers"] = layers
            if label:
                mq["label"] = label
            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "lxm.ingest_uri.result",
                            "status": "success",
                            "message": "Opening map view.",
                            "ingest_type": "map_view",
                            "map_query": mq,
                        },
                    ),
                ),
            )
            return

        if uri_raw.lower().startswith(("meshchatx://", "meshchat://")):
            from urllib.parse import parse_qsl, unquote, urlparse

            _parsed = urlparse(uri_raw)
            _sch = (_parsed.scheme or "").lower()
            _host = (_parsed.netloc or "").lower()
            if _sch in ("meshchatx", "meshchat") and _host == "docs":
                _q = dict(parse_qsl(_parsed.query, keep_blank_values=True))
                rel = (_q.get("reticulum") or _q.get("path") or "").strip()
                if not rel and _parsed.path and _parsed.path != "/":
                    rel = unquote(_parsed.path.lstrip("/"))
                payload: dict = {
                    "type": "lxm.ingest_uri.result",
                    "status": "success",
                    "message": "Opening documentation.",
                    "ingest_type": "docs_view",
                }
                if rel:
                    payload["docs_query"] = {"reticulum": rel}
                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(payload),
                    ),
                )
                return

            # Known hosts (map/docs) are handled above. Relay and app
            # deep links are frontend-routed. Anything else must not
            # fall through to LXMF ingest.
            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "lxm.ingest_uri.result",
                            "status": "error",
                            "message": (
                                f"Unknown or unsupported meshchatx link host "
                                f"'{_host or '(empty)'}'. "
                                "Supported hosts include map, docs, relay, and app."
                            ),
                            "ingest_type": "unknown_meshchatx",
                            "host": _host,
                        },
                    ),
                ),
            )
            return

        # LXMA contact sharing URI:
        # lxma://<destination_hash_hex>:<public_key_hex>
        if uri_raw.lower().startswith("lxma://"):
            from meshchatx.src.backend.lxma_contact import bind_lxma_contact

            destination_hash_hex, identity = bind_lxma_contact(
                uri_raw,
                app._identity_from_public_key_bytes,
            )

            remote_identity_hash = identity.hash.hex()
            existing_contact = app.database.contacts.get_contact_by_identity_hash(
                remote_identity_hash,
            )
            contact_name = (
                existing_contact["name"]
                if existing_contact and existing_contact.get("name")
                else f"Contact {destination_hash_hex[:8]}"
            )

            app.database.contacts.add_contact(
                contact_name,
                remote_identity_hash,
                lxmf_address=destination_hash_hex,
            )
            app.sync_telephone_call_policy()

            # Persist pubkey so outbound LXMF works before any announce.
            try:
                RNS.Identity.remember(
                    None,
                    bytes.fromhex(destination_hash_hex),
                    identity.get_public_key(),
                    None,
                )
            except Exception as remember_exc:
                print(
                    f"LXMA remember failed for {destination_hash_hex}: "
                    f"{type(remember_exc).__name__}: {remember_exc!r}",
                )

            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "lxm.ingest_uri.result",
                            "status": "success",
                            "message": f"Contact imported from LXMA URI ({destination_hash_hex})",
                            "ingest_type": "lxma_contact",
                            "destination_hash": destination_hash_hex,
                        },
                    ),
                ),
            )
            return

        # ensure uri starts with lxmf:// or lxm://
        if not uri.lower().startswith(
            LXMF.LXMessage.URI_SCHEMA + "://",
        ) and not uri.lower().startswith("lxm://"):
            if ":" in uri and "//" not in uri:
                uri = LXMF.LXMessage.URI_SCHEMA + "://" + uri
            else:
                uri = LXMF.LXMessage.URI_SCHEMA + "://" + uri

        ingest_result = app.message_router.ingest_lxm_uri(
            uri,
            signal_local_delivery=local_delivery_signal,
            signal_duplicate=duplicate_signal,
        )

        if ingest_result is False:
            response = "The URI contained no decodable messages"
            status = "error"
        elif ingest_result == local_delivery_signal:
            response = "Message was decoded, decrypted successfully, and added to your conversation list."
            status = "success"
        elif ingest_result == duplicate_signal:
            response = "The decoded message has already been processed by the LXMF Router, and will not be ingested again."
            status = "info"
        else:
            response = "The decoded message was not addressed to your LXMF address, and has been discarded."
            status = "warning"

        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "lxm.ingest_uri.result",
                        "status": status,
                        "message": response,
                    },
                ),
            ),
        )
    except Exception as e:
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "lxm.ingest_uri.result",
                        "status": "error",
                        "message": f"Error ingesting message from URI: {e!s}",
                    },
                ),
            ),
        )

    # handle generating a paper message uri


async def handle_lxm_generate_paper_uri(app, client, data):
    destination_hash = data.get("destination_hash")
    content = data.get("content")
    title = data.get("title", "")

    if not destination_hash or not content:
        return

    try:
        destination_hash_bytes = bytes.fromhex(destination_hash)
        destination_identity = RNS.Identity.recall(destination_hash_bytes)

        if destination_identity is None:
            # try to find in database
            announce = app.database.announces.get_announce_by_hash(
                destination_hash,
            )
            if announce and announce.get("identity_public_key"):
                destination_identity = RNS.Identity.from_bytes(
                    base64.b64decode(announce["identity_public_key"]),
                )

        if destination_identity is None:
            raise Exception(
                "Recipient identity not found. Please wait for an announce or add them as a contact.",
            )

        lxmf_destination = RNS.Destination(
            destination_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        lxm = LXMF.LXMessage(
            lxmf_destination,
            app.local_lxmf_destination,
            content,
            title=title,
            desired_method=LXMF.LXMessage.PAPER,
        )

        # generate uri
        uri = lxm.as_uri()

        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "lxm.generate_paper_uri.result",
                        "status": "success",
                        "uri": uri,
                    },
                ),
            ),
        )
    except Exception as e:
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "lxm.generate_paper_uri.result",
                        "status": "error",
                        "message": f"Error generating paper message: {e!s}",
                    },
                ),
            ),
        )

    # handle getting keyboard shortcuts


HANDLERS = {
    "lxmf.forwarding.rules.get": handle_lxmf_forwarding_rules_get,
    "lxmf.forwarding.rule.add": handle_lxmf_forwarding_rule_add,
    "lxmf.forwarding.rule.delete": handle_lxmf_forwarding_rule_delete,
    "lxmf.forwarding.rule.toggle": handle_lxmf_forwarding_rule_toggle,
    "lxm.ingest_uri": handle_lxm_ingest_uri,
    "lxm.generate_paper_uri": handle_lxm_generate_paper_uri,
}
