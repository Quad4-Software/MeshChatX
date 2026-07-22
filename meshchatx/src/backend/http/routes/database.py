# SPDX-License-Identifier: 0BSD
"""HTTP routes: database."""

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


def register_database_routes(routes, app):

    # ── Database ─────────────────────────────────────────────────────

    @routes.post("/api/v1/database/snapshot")
    async def create_db_snapshot(request):
        try:
            data = await request.json()
            name = data.get("name", f"snapshot-{int(time.time())}")
            result = app.database.create_snapshot(app.storage_path, name)
            return web.json_response({"status": "success", "result": result})
        except Exception as e:
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    @routes.get("/api/v1/database/snapshots")
    async def list_db_snapshots(request):
        try:
            limit = int(request.query.get("limit", 100))
            offset = int(request.query.get("offset", 0))
            snapshots = app.database.list_snapshots(app.storage_path)
            total = len(snapshots)
            paginated_snapshots = snapshots[offset : offset + limit]
            return web.json_response(
                {
                    "snapshots": paginated_snapshots,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            )
        except Exception as e:
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    @routes.delete("/api/v1/database/snapshots/{filename}")
    async def delete_db_snapshot(request):
        try:
            filename = request.match_info.get("filename")
            if not filename.endswith(".zip"):
                filename += ".zip"
            app.database.delete_snapshot_or_backup(
                app.storage_path,
                filename,
                is_backup=False,
            )
            return web.json_response({"status": "success"})
        except Exception as e:
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/database/restore")
    async def restore_db_snapshot(request):
        try:
            content_type = request.headers.get("Content-Type", "")

            # multipart upload: restore from a user-provided backup/zip file
            if "multipart/form-data" in content_type:
                reader = await request.multipart()
                field = await reader.next()
                if field is None or field.name != "file":
                    return web.json_response(
                        {"status": "error", "message": "Restore file is required"},
                        status=400,
                    )

                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        tmp.write(chunk)
                    temp_path = tmp.name

                try:
                    result = app.restore_database(temp_path, relaunch=True)
                finally:
                    with contextlib.suppress(OSError):
                        os.remove(temp_path)

                return web.json_response(
                    {
                        "status": "success",
                        "result": result,
                        "database": result,
                        "requires_relaunch": True,
                        "message": "Database restored. Application will restart.",
                    },
                )

            # JSON body: restore from an on-disk snapshot/auto-backup path
            data = await request.json()
            path = data.get("path")
            if not path:
                return web.json_response(
                    {"status": "error", "message": "No path provided"},
                    status=400,
                )

            resolved = app._resolve_database_restore_path(path)
            if not resolved:
                return web.json_response(
                    {"status": "error", "message": "Snapshot not found"},
                    status=404,
                )

            result = app.restore_database(resolved, relaunch=True)
            return web.json_response(
                {
                    "status": "success",
                    "result": result,
                    "requires_relaunch": True,
                    "message": "Database restored. Application will restart.",
                },
            )
        except Exception as e:
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    @routes.get("/api/v1/database/backups")
    async def list_db_backups(request):
        try:
            limit = int(request.query.get("limit", 100))
            offset = int(request.query.get("offset", 0))
            backup_dir = os.path.join(app.storage_path, "database-backups")
            if not os.path.exists(backup_dir):
                return web.json_response(
                    {"backups": [], "total": 0, "limit": limit, "offset": offset},
                )

            backups = []
            for file in os.listdir(backup_dir):
                if file.endswith(".zip"):
                    full_path = os.path.join(backup_dir, file)
                    stats = os.stat(full_path)
                    backups.append(
                        {
                            "name": file,
                            "path": full_path,
                            "size": stats.st_size,
                            "created_at": datetime.fromtimestamp(
                                stats.st_mtime,
                                UTC,
                            ).isoformat(),
                        },
                    )
            sorted_backups = sorted(
                backups,
                key=lambda x: x["created_at"],
                reverse=True,
            )
            total = len(sorted_backups)
            paginated_backups = sorted_backups[offset : offset + limit]
            return web.json_response(
                {
                    "backups": paginated_backups,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            )
        except Exception as e:
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    @routes.delete("/api/v1/database/backups/{filename}")
    async def delete_db_backup(request):
        try:
            filename = request.match_info.get("filename")
            if not filename.endswith(".zip"):
                filename += ".zip"
            app.database.delete_snapshot_or_backup(
                app.storage_path,
                filename,
                is_backup=True,
            )
            return web.json_response({"status": "success"})
        except Exception as e:
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    @routes.get("/api/v1/database/backups/{filename}/download")
    async def download_db_backup(request):
        try:
            filename = request.match_info.get("filename")
            if not filename.endswith(".zip"):
                filename += ".zip"
            backup_dir = os.path.join(app.storage_path, "database-backups")
            full_path = safe_path_under_dir(backup_dir, filename)

            if not full_path or not os.path.isfile(full_path):
                return web.json_response(
                    {"status": "error", "message": "Backup not found"},
                    status=404,
                )

            return web.FileResponse(
                path=full_path,
                headers={
                    "Content-Disposition": f'attachment; filename="{os.path.basename(full_path)}"',
                },
            )
        except Exception as e:
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    @routes.get("/api/v1/database/snapshots/{filename}/download")
    async def download_db_snapshot(request):
        try:
            filename = request.match_info.get("filename")
            if not filename.endswith(".zip"):
                filename += ".zip"
            snapshot_dir = os.path.join(app.storage_path, "snapshots")
            full_path = safe_path_under_dir(snapshot_dir, filename)

            if not full_path or not os.path.isfile(full_path):
                return web.json_response(
                    {"status": "error", "message": "Snapshot not found"},
                    status=404,
                )

            return web.FileResponse(
                path=full_path,
                headers={
                    "Content-Disposition": f'attachment; filename="{os.path.basename(full_path)}"',
                },
            )
        except Exception as e:
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    @routes.get("/api/v1/database/health")
    async def database_health(request):
        try:
            return web.json_response(
                {
                    "database": app.database.get_database_health_snapshot(),
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to fetch database health: {e!s}",
                },
                status=500,
            )

    @routes.post("/api/v1/database/vacuum")
    async def database_vacuum(request):
        try:
            result = app.database.run_database_vacuum()
            return web.json_response(
                {
                    "message": "Database vacuum completed",
                    "database": result,
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to vacuum database: {e!s}",
                },
                status=500,
            )

    @routes.post("/api/v1/database/recover")
    async def database_recover(request):
        try:
            result = app.database.run_database_recovery()
            return web.json_response(
                {
                    "message": "Database recovery routine completed",
                    "database": result,
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to recover database: {e!s}",
                },
                status=500,
            )

    @routes.post("/api/v1/database/backup")
    async def database_backup(request):
        try:
            result = app.database.backup_database(app.storage_path)
            return web.json_response(
                {
                    "message": "Database backup created",
                    "backup": result,
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to create database backup: {e!s}",
                },
                status=500,
            )

    @routes.get("/api/v1/database/backup/download")
    async def database_backup_download(request):
        try:
            backup_info = app.database.backup_database(app.storage_path)
            file_path = backup_info["path"]
            with open(file_path, "rb") as f:
                data = f.read()
            return web.Response(
                body=data,
                headers={
                    "Content-Type": "application/zip",
                    "Content-Disposition": f'attachment; filename="{os.path.basename(file_path)}"',
                },
            )
        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to create database backup: {e!s}",
                },
                status=500,
            )
