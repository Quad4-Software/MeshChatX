# SPDX-License-Identifier: 0BSD
"""HTTP routes: translator."""

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


def register_translator_routes(routes, app):

    @routes.get("/api/v1/translator/languages")
    async def translator_languages(request):
        try:
            libretranslate_url = request.query.get("libretranslate_url")
            if libretranslate_url or (
                app.translator_handler
                and app.translator_handler.translator_libretranslate_enabled
            ):
                app._require_outbound_http("translator language lookup")
            th = app.translator_handler
            out = th.get_translator_languages_response(
                libretranslate_url=libretranslate_url,
            )
            return web.json_response(
                {
                    "languages": out["languages"],
                    "has_argos": th.has_argos,
                    "has_argos_lib": th.has_argos_lib,
                    "has_argos_cli": th.has_argos_cli,
                    "libre_client_available": th.has_requests,
                    "libretranslate_reachable": out["libretranslate_reachable"],
                },
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except OutboundHttpBlockedError as e:
            return web.json_response({"message": str(e)}, status=403)
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/translator/translate")
    async def translator_translate(request):
        data = await request.json()
        text = data.get("text", "")
        source_lang = data.get("source_lang", "auto")
        target_lang = data.get("target_lang", "")
        use_argos = bool(data.get("use_argos", False))
        libretranslate_url = data.get("libretranslate_url")
        libretranslate_api_key = data.get("libretranslate_api_key")

        if not text:
            return web.json_response(
                {"message": "Text cannot be empty"},
                status=400,
            )

        if not target_lang:
            return web.json_response(
                {"message": "Target language is required"},
                status=400,
            )

        try:
            if not use_argos:
                app._require_outbound_http("LibreTranslate")
            result = app.translator_handler.translate_text(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                use_argos=use_argos,
                libretranslate_url=libretranslate_url,
                libretranslate_api_key=libretranslate_api_key,
            )
            return web.json_response(result)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except OutboundHttpBlockedError as e:
            return web.json_response({"message": str(e)}, status=403)
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/translator/install-languages")
    async def translator_install_languages(request):
        data = await request.json()
        package_name = data.get("package", "translate")

        try:
            app._require_outbound_http("Argos language package install")
            result = app.translator_handler.install_language_package(package_name)
            return web.json_response(result)
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )
