# SPDX-License-Identifier: 0BSD
"""HTTP routes: bots."""

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


def register_bots_routes(routes, app):

    @routes.get("/api/v1/bots/status")
    async def bots_status(request):
        try:
            status = app.bot_handler.get_status()
            templates = app.bot_handler.get_available_templates()
            if app.database:
                for bot in status.get("bots") or []:
                    lxmf_addr = bot.get("lxmf_address") or bot.get("full_address")
                    if not lxmf_addr:
                        bot["last_announce_at"] = None
                        continue
                    lxmf_addr = str(lxmf_addr).strip().lower()
                    ann = app.database.announces.get_announce_by_hash(lxmf_addr)
                    if not ann:
                        bot["last_announce_at"] = None
                        continue
                    arow = dict(ann) if not isinstance(ann, dict) else ann
                    ts = arow.get("updated_at")
                    if ts is not None and hasattr(ts, "isoformat"):
                        bot["last_announce_at"] = ts.isoformat()
                    else:
                        bot["last_announce_at"] = str(ts) if ts is not None else None
            return web.json_response(
                {
                    "status": status,
                    "templates": templates,
                    "detection_error": status.get("detection_error"),
                },
            )
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/bots/start")
    async def bots_start(request):
        data = await request.json()
        template_id = data.get("template_id")
        name = data.get("name")
        bot_id = data.get("bot_id")

        if not template_id:
            return web.json_response(
                {"message": "template_id is required"},
                status=400,
            )

        try:
            bot_id = await asyncio.to_thread(
                app.bot_handler.start_bot,
                template_id,
                name,
                bot_id,
                None,
                data.get("lxmf_config"),
            )
            return web.json_response({"bot_id": bot_id, "success": True})
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/bots/stop")
    async def bots_stop(request):
        data = await request.json()
        bot_id = data.get("bot_id")

        if not bot_id:
            return web.json_response(
                {"message": "bot_id is required"},
                status=400,
            )

        try:
            success = await asyncio.to_thread(app.bot_handler.stop_bot, bot_id)
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/bots/restart")
    async def bots_restart(request):
        data = await request.json()
        bot_id = data.get("bot_id")

        if not bot_id:
            return web.json_response(
                {"message": "bot_id is required"},
                status=400,
            )

        try:
            new_id = await asyncio.to_thread(
                app.bot_handler.restart_bot,
                bot_id,
            )
            return web.json_response({"bot_id": new_id, "success": True})
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/bots/delete")
    async def bots_delete(request):
        data = await request.json()
        bot_id = data.get("bot_id")

        if not bot_id:
            return web.json_response(
                {"message": "bot_id is required"},
                status=400,
            )

        try:
            success = await asyncio.to_thread(app.bot_handler.delete_bot, bot_id)
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.get("/api/v1/bots/subprocess-log")
    async def bots_subprocess_log(request):
        bot_id = request.query.get("bot_id")

        if not bot_id:
            return web.json_response(
                {"message": "bot_id is required"},
                status=400,
            )

        try:
            result = await asyncio.to_thread(
                app.bot_handler.read_subprocess_log,
                bot_id,
            )
            return web.json_response(result)
        except ValueError as e:
            return web.json_response(
                {"message": str(e)},
                status=404,
            )
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.patch("/api/v1/bots/update")
    async def bots_update(request):
        data = await request.json()
        bot_id = data.get("bot_id")
        name = data.get("name")
        lxmf_config = data.get("lxmf_config")

        if not bot_id:
            return web.json_response(
                {"message": "bot_id is required"},
                status=400,
            )

        try:
            if name is not None:
                await asyncio.to_thread(
                    app.bot_handler.update_bot_name,
                    bot_id,
                    name,
                )
            if lxmf_config is not None:
                saved = await asyncio.to_thread(
                    app.bot_handler.update_bot_lxmf_config,
                    bot_id,
                    lxmf_config,
                )
                return web.json_response({"success": True, "lxmf_config": saved})
            return web.json_response({"success": True})
        except ValueError as e:
            return web.json_response(
                {"message": str(e)},
                status=400,
            )
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.patch("/api/v1/bots/lxmf-config")
    async def bots_lxmf_config(request):
        data = await request.json()
        bot_id = data.get("bot_id")
        lxmf_config = data.get("lxmf_config")

        if not bot_id:
            return web.json_response(
                {"message": "bot_id is required"},
                status=400,
            )
        if lxmf_config is None:
            return web.json_response(
                {"message": "lxmf_config is required"},
                status=400,
            )

        try:
            saved = await asyncio.to_thread(
                app.bot_handler.update_bot_lxmf_config,
                bot_id,
                lxmf_config,
            )
            return web.json_response({"success": True, "lxmf_config": saved})
        except ValueError as e:
            return web.json_response(
                {"message": str(e)},
                status=400,
            )
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/bots/announce")
    async def bots_announce(request):
        data = await request.json()
        bot_id = data.get("bot_id")

        if not bot_id:
            return web.json_response(
                {"message": "bot_id is required"},
                status=400,
            )

        try:
            await asyncio.to_thread(app.bot_handler.request_announce, bot_id)
            return web.json_response({"success": True})
        except ValueError as e:
            return web.json_response(
                {"message": str(e)},
                status=400,
            )
        except RuntimeError as e:
            return web.json_response(
                {"message": str(e)},
                status=409,
            )
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/bots/export")
    async def bots_export(request):
        bot_id = None
        try:
            data = await request.json()
            if isinstance(data, dict):
                bot_id = data.get("bot_id")
        except Exception:
            bot_id = None
        if not bot_id:
            bot_id = request.query.get("bot_id")

        if not bot_id:
            return web.json_response(
                {"message": "bot_id is required"},
                status=400,
            )

        try:
            id_path = app.bot_handler.get_bot_identity_path(bot_id)
            if not id_path or not os.path.exists(id_path):
                return web.json_response(
                    {"message": "Identity file not found"},
                    status=404,
                )

            return web.FileResponse(
                id_path,
                headers={
                    "Content-Disposition": f'attachment; filename="bot_{bot_id}_identity"',
                },
            )
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    # get custom destination display name
