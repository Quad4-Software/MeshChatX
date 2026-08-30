# SPDX-License-Identifier: 0BSD
"""WebSocket handlers: handlers_core."""

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


async def handle_ping(app, client, data):
    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": "pong",
                },
            ),
        ),
    )

    # handle updating config


async def handle_config_set(app, client, data):
    config = sanitize_websocket_config_update(data.get("config"))

    try:
        await app.update_config(config)
        try:
            AsyncUtils.run_async(app.send_config_to_websocket_clients())
        except Exception as e:
            print(f"Failed to broadcast config update: {e}")
    except Exception:
        import traceback

        print("config.set failed:\n" + traceback.format_exc())

    # handle canceling a download


async def handle_keyboard_shortcuts_get(app, client, data):
    shortcuts = app.database.misc.get_keyboard_shortcuts(
        app.identity.hash.hex(),
    )
    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": "keyboard_shortcuts",
                    "shortcuts": [
                        {
                            "action": s["action"],
                            "keys": json.loads(s["keys"]),
                        }
                        for s in shortcuts
                    ],
                },
            ),
        ),
    )

    # handle updating/upserting a keyboard shortcut


async def handle_keyboard_shortcuts_set(app, client, data):
    action = data["action"]
    keys = json.dumps(data["keys"])
    app.database.misc.upsert_keyboard_shortcut(
        app.identity.hash.hex(),
        action,
        keys,
    )
    # notify updated
    AsyncUtils.run_async(
        app.on_websocket_data_received(
            client,
            {"type": "keyboard_shortcuts.get"},
        ),
    )

    # handle deleting a keyboard shortcut


async def handle_keyboard_shortcuts_delete(app, client, data):
    action = data["action"]
    app.database.misc.delete_keyboard_shortcut(
        app.identity.hash.hex(),
        action,
    )
    # notify updated
    AsyncUtils.run_async(
        app.on_websocket_data_received(
            client,
            {"type": "keyboard_shortcuts.get"},
        ),
    )


HANDLERS = {
    "ping": handle_ping,
    "config.set": handle_config_set,
    "keyboard_shortcuts.get": handle_keyboard_shortcuts_get,
    "keyboard_shortcuts.set": handle_keyboard_shortcuts_set,
    "keyboard_shortcuts.delete": handle_keyboard_shortcuts_delete,
}
