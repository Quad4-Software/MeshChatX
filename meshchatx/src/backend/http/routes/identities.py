# SPDX-License-Identifier: 0BSD
"""HTTP routes: identities."""

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


def register_identities_routes(routes, app):

    @routes.get("/api/v1/identity/backup/download")
    async def identity_backup_download(request):
        try:
            info = app.backup_identity()
            with open(info["path"], "rb") as f:
                data = f.read()
            return web.Response(
                body=data,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Disposition": 'attachment; filename="identity.bin"',
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to create identity backup: {e!s}",
                },
                status=500,
            )

    @routes.get("/api/v1/identity/backup/base32")
    async def identity_backup_base32(request):
        try:
            return web.json_response(
                {
                    "identity_base32": app.backup_identity_base32(),
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to export identity: {e!s}",
                },
                status=500,
            )

    @routes.post("/api/v1/identity/restore")
    async def identity_restore(request):
        try:
            content_type = request.headers.get("Content-Type", "")
            # multipart file upload
            if "multipart/form-data" in content_type:
                reader = await request.multipart()
                identity_bytes = None
                display_name = None
                field = await reader.next()
                while field is not None:
                    if field.name == "file":
                        with tempfile.NamedTemporaryFile(delete=False) as tmp:
                            while True:
                                chunk = await field.read_chunk()
                                if not chunk:
                                    break
                                tmp.write(chunk)
                            temp_path = tmp.name
                        try:
                            with open(temp_path, "rb") as f:
                                identity_bytes = f.read()
                        finally:
                            with contextlib.suppress(OSError):
                                os.remove(temp_path)
                    elif field.name == "display_name":
                        display_name = (await field.text()).strip() or None
                    field = await reader.next()
                if identity_bytes is None:
                    return web.json_response(
                        {"message": "Identity file is required"},
                        status=400,
                    )
                result = app.restore_identity_from_bytes(
                    identity_bytes,
                    display_name=display_name,
                )
            else:
                data = await request.json()
                base32_value = data.get("base32")
                if not base32_value:
                    return web.json_response(
                        {"message": "base32 value is required"},
                        status=400,
                    )
                result = app.restore_identity_from_base32(
                    base32_value,
                    display_name=data.get("display_name"),
                )

            return web.json_response(
                {
                    "message": "Identity restored. Restart app to use the new identity.",
                    "identity": result,
                },
            )
        except ValueError as e:
            return web.json_response(
                {
                    "message": str(e),
                },
                status=400,
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to restore identity: {e!s}",
                },
                status=500,
            )

    @routes.get("/api/v1/identities")
    async def identities_list(request):
        try:
            identities = app.list_identities()
            if app.database:
                for item in identities:
                    if item.get("is_current"):
                        item["message_count"] = (
                            app.database.messages.count_lxmf_messages()
                        )
                        break
            return web.json_response(
                {
                    "identities": identities,
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to list identities: {e!s}",
                },
                status=500,
            )

    @routes.get("/api/v1/identities/export-all")
    async def identities_export_all(request):
        try:
            all_bytes = app.identity_manager.get_all_identity_backup_bytes()
            if not all_bytes:
                return web.json_response(
                    {"message": "No identities to export"},
                    status=400,
                )
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for identity_hash, data in all_bytes.items():
                    zf.writestr(f"identity_{identity_hash}", data)
            buf.seek(0)
            return web.Response(
                body=buf.read(),
                headers={
                    "Content-Type": "application/zip",
                    "Content-Disposition": 'attachment; filename="identities_export.zip"',
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to export identities: {e!s}",
                },
                status=500,
            )

    @routes.post("/api/v1/identities/create")
    async def identities_create(request):
        try:
            data = await request.json()
            display_name = data.get("display_name")
            result = app.create_identity(display_name)
            return web.json_response(
                {
                    "message": "Identity created successfully",
                    "identity": result,
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to create identity: {e!s}",
                },
                status=500,
            )

    @routes.delete("/api/v1/identities/{identity_hash}")
    async def identities_delete(request):
        try:
            identity_hash = normalize_identity_storage_hash(
                request.match_info.get("identity_hash"),
            )
            if not identity_hash:
                return web.json_response(
                    {"message": "Invalid identity hash"},
                    status=400,
                )
            if app.delete_identity(identity_hash):
                return web.json_response(
                    {
                        "message": "Identity deleted successfully",
                    },
                )
            return web.json_response(
                {
                    "message": "Identity not found",
                },
                status=404,
            )
        except ValueError as e:
            return web.json_response(
                {
                    "message": str(e),
                },
                status=400,
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to delete identity: {e!s}",
                },
                status=500,
            )

    @routes.post("/api/v1/identities/switch")
    async def identities_switch(request):
        try:
            data = await request.json()
            identity_hash = normalize_identity_storage_hash(
                data.get("identity_hash"),
            )
            if not identity_hash:
                return web.json_response(
                    {"message": "Invalid identity hash"},
                    status=400,
                )
            keep_alive = data.get("keep_alive", False)

            # attempt hotswap first
            success = await app.hotswap_identity(
                identity_hash,
                keep_alive=keep_alive,
            )

            if success:
                display_name = (
                    app.config.display_name.get()
                    if hasattr(app, "config")
                    else "Unknown"
                )
                return web.json_response(
                    {
                        "message": "Identity switched successfully.",
                        "hotswapped": True,
                        "identity_hash": identity_hash,
                        "display_name": display_name,
                    },
                )
            # fallback to restart if hotswap failed
            # (this part should probably be unreachable if hotswap is reliable)
            main_identity_file = app.identity_file_path or os.path.join(
                app.storage_dir,
                "identity",
            )
            identities_root = os.path.join(app.storage_dir, "identities")
            identity_dir = os.path.join(identities_root, identity_hash)
            identity_file = os.path.join(identity_dir, "identity")
            if not is_path_within_dir(identity_dir, identities_root):
                return web.json_response(
                    {"message": "Invalid identity hash"},
                    status=400,
                )

            shutil.copy2(identity_file, main_identity_file)

            def restart():
                time.sleep(1)
                try:
                    os.execv(sys.executable, [sys.executable] + sys.argv)  # noqa: S606
                except Exception as e:
                    print(f"Failed to restart: {e}")
                    os._exit(0)

            threading.Thread(target=restart).start()

            return web.json_response(
                {
                    "message": "Identity switch scheduled. Application will restart.",
                    "hotswapped": False,
                    "should_restart": True,
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to switch identity: {e!s}",
                },
                status=500,
            )

    # maintenance - clear messages (all, or older than days / before date)
