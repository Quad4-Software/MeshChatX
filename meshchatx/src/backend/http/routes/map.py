# SPDX-License-Identifier: 0BSD
"""HTTP routes: map."""

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


def register_map_routes(routes, app):

    # get offline map metadata
    @routes.get("/api/v1/map/offline")
    async def get_map_offline_metadata(request):
        metadata = app.map_manager.get_metadata()
        if metadata:
            return web.json_response(metadata)
        return web.json_response({"loaded": False})

    # get map tile

    # get map tile
    @routes.get("/api/v1/map/tiles/{z}/{x}/{y}")
    async def get_map_tile(request):
        try:
            z = int(request.match_info.get("z"))
            x = int(request.match_info.get("x"))
            y_str = request.match_info.get("y")
            # remove .png if present
            y_str = y_str.removesuffix(".png")
            y = int(y_str)

            tile_data = app.map_manager.get_tile(z, x, y)
            if tile_data:
                return web.Response(body=tile_data, content_type="image/png")

            # If tile not found, return a transparent 1x1 PNG instead of 404
            # to avoid browser console errors in offline mode.
            return web.Response(body=TRANSPARENT_TILE, content_type="image/png")
        except Exception:
            return web.Response(status=400)

    # list available MBTiles files

    # list available MBTiles files
    @routes.get("/api/v1/map/mbtiles")
    async def list_mbtiles(request):
        return web.json_response(app.map_manager.list_mbtiles())

    # delete an MBTiles file

    # delete an MBTiles file
    @routes.delete("/api/v1/map/mbtiles/{filename}")
    async def delete_mbtiles(request):
        filename = request.match_info.get("filename")
        if app.map_manager.delete_mbtiles(filename):
            return web.json_response({"message": "File deleted"})
        return web.json_response({"error": "File not found"}, status=404)

    # set active MBTiles file

    # set active MBTiles file
    @routes.post("/api/v1/map/mbtiles/active")
    async def set_active_mbtiles(request):
        data = await request.json()
        filename = data.get("filename")
        if not filename:
            app.config.map_offline_path.set(None)
            app.config.map_offline_enabled.set(False)
            return web.json_response({"message": "Offline map disabled"})

        mbtiles_dir = app.map_manager.get_mbtiles_dir()
        safe_name = os.path.basename(filename)
        file_path = os.path.join(mbtiles_dir, safe_name)
        if not is_path_within_dir(file_path, mbtiles_dir):
            return web.json_response({"error": "Invalid filename"}, status=400)
        if os.path.exists(file_path):
            app.map_manager.close()
            app.config.map_offline_path.set(file_path)
            app.config.map_offline_enabled.set(True)
            return web.json_response(
                {
                    "message": "Active map updated",
                    "metadata": app.map_manager.get_metadata(),
                },
            )
        return web.json_response({"error": "File not found"}, status=404)

    # map drawings

    # map drawings
    @routes.get("/api/v1/map/drawings")
    async def get_map_drawings(request):
        identity_hash = app.identity.hash.hex()
        rows = app.database.map_drawings.get_drawings(identity_hash)
        drawings = [dict(row) for row in rows]
        return web.json_response({"drawings": drawings})

    @routes.post("/api/v1/map/drawings")
    async def save_map_drawing(request):
        identity_hash = app.identity.hash.hex()
        data = await request.json()
        name = data.get("name")
        drawing_data = data.get("data")
        app.database.map_drawings.upsert_drawing(identity_hash, name, drawing_data)
        return web.json_response({"message": "Drawing saved successfully"})

    @routes.delete("/api/v1/map/drawings/{drawing_id}")
    async def delete_map_drawing(request):
        drawing_id = request.match_info.get("drawing_id")
        app.database.map_drawings.delete_drawing(drawing_id)
        return web.json_response({"message": "Drawing deleted successfully"})

    @routes.patch("/api/v1/map/drawings/{drawing_id}")
    async def update_map_drawing(request):
        drawing_id = request.match_info.get("drawing_id")
        data = await request.json()
        name = data.get("name")
        drawing_data = data.get("data")
        app.database.map_drawings.update_drawing(drawing_id, name, drawing_data)
        return web.json_response({"message": "Drawing updated successfully"})

    @routes.get("/api/v1/map/overlays")
    async def list_map_overlays(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        identity_hash = app.identity.hash.hex()
        overlays = app.map_overlay_manager.list_overlays(identity_hash)
        return web.json_response({"overlays": overlays})

    @routes.post("/api/v1/map/overlays")
    async def create_map_overlays(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        identity_hash = app.identity.hash.hex()
        try:
            result = await app.map_overlay_manager.create_overlays(
                identity_hash,
                data,
            )
        except OverlaySourceParseError as exc:
            return web.json_response({"error": exc.code}, status=400)
        except GeoValidationError as exc:
            return web.json_response({"error": exc.code}, status=400)
        return web.json_response(result)

    @routes.post("/api/v1/map/overlays/export")
    async def export_map_overlays_many(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        fmt = str(data.get("format") or "geojson").lower()
        ids = data.get("ids") or []
        if not isinstance(ids, list):
            return web.json_response({"error": "missing_ids"}, status=400)
        try:
            overlay_ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            return web.json_response({"error": "missing_ids"}, status=400)
        identity_hash = app.identity.hash.hex()
        try:
            body, content_type, filename = app.map_overlay_manager.export_many(
                identity_hash,
                overlay_ids,
                fmt,
            )
        except OverlayExportError as exc:
            status = 404 if exc.code == "cache_missing" else 400
            return web.json_response({"error": exc.code}, status=status)
        return web.Response(
            body=body,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    @routes.get("/api/v1/map/overlays/jobs/{job_id}")
    async def get_map_overlay_job(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        job_id = request.match_info.get("job_id")
        job = app.map_overlay_manager.get_job(job_id)
        if not job:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response(job)

    @routes.post("/api/v1/map/overlays/jobs/{job_id}/cancel")
    async def cancel_map_overlay_job(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        job_id = request.match_info.get("job_id")
        ok = app.map_overlay_manager.cancel_job(job_id)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"cancelled": True})

    @routes.post("/api/v1/map/overlays/{overlay_id}/refresh")
    async def refresh_map_overlay(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return web.json_response({"error": "not_found"}, status=404)
        identity_hash = app.identity.hash.hex()
        try:
            result = await app.map_overlay_manager.refresh_overlay(
                identity_hash,
                overlay_id,
            )
        except OverlaySourceParseError as exc:
            status = 404 if exc.code == "not_found" else 400
            return web.json_response({"error": exc.code}, status=status)
        return web.json_response(result)

    @routes.patch("/api/v1/map/overlays/{overlay_id}")
    async def patch_map_overlay(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return web.json_response({"error": "not_found"}, status=404)
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        identity_hash = app.identity.hash.hex()
        try:
            overlay = app.map_overlay_manager.patch_overlay(
                identity_hash,
                overlay_id,
                data,
            )
        except OverlaySourceParseError as exc:
            status = 404 if exc.code == "not_found" else 400
            return web.json_response({"error": exc.code}, status=status)
        return web.json_response({"overlay": overlay})

    @routes.delete("/api/v1/map/overlays/{overlay_id}")
    async def delete_map_overlay(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return web.json_response({"error": "not_found"}, status=404)
        identity_hash = app.identity.hash.hex()
        ok = app.map_overlay_manager.delete_overlay(identity_hash, overlay_id)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"deleted": True})

    @routes.get("/api/v1/map/overlays/{overlay_id}/content")
    async def get_map_overlay_content(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return web.json_response({"error": "not_found"}, status=404)
        identity_hash = app.identity.hash.hex()
        cached = app.map_overlay_manager.read_cache_bytes(
            identity_hash,
            overlay_id,
        )
        if not cached:
            return web.json_response({"error": "cache_missing"}, status=404)
        data, fmt = cached
        from meshchatx.src.backend.map_overlay_export import CONTENT_TYPES

        return web.Response(
            body=data,
            headers={
                "Content-Type": CONTENT_TYPES.get(fmt, "application/octet-stream"),
            },
        )

    @routes.get("/api/v1/map/overlays/{overlay_id}/export")
    async def export_map_overlay(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return web.json_response({"error": "not_found"}, status=404)
        fmt = str(request.rel_url.query.get("format") or "geojson").lower()
        identity_hash = app.identity.hash.hex()
        try:
            body, content_type, filename = app.map_overlay_manager.export_overlay(
                identity_hash,
                overlay_id,
                fmt,
            )
        except OverlayExportError as exc:
            status = 404 if exc.code == "cache_missing" else 400
            return web.json_response({"error": exc.code}, status=status)
        return web.Response(
            body=body,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    # upload offline map
    @routes.post("/api/v1/map/offline")
    async def upload_map_offline(request):
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field.name != "file":
                return web.json_response({"error": "No file field"}, status=400)

            filename = os.path.basename(field.filename or "")
            if not is_mbtiles_filename(filename):
                return web.json_response(
                    {"error": "Invalid file format, must be .mbtiles"},
                    status=400,
                )

            mbtiles_dir = app.map_manager.get_mbtiles_dir()
            if not os.path.exists(mbtiles_dir):
                os.makedirs(mbtiles_dir)

            dest_path = os.path.join(mbtiles_dir, filename)
            if not is_path_within_dir(dest_path, mbtiles_dir):
                return web.json_response(
                    {"error": "Invalid filename"},
                    status=400,
                )

            size = 0
            with open(dest_path, "wb") as f:
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    size += len(chunk)
                    f.write(chunk)

            # close old connection and clear cache before update
            app.map_manager.close()

            # update config
            app.config.map_offline_path.set(dest_path)
            app.config.map_offline_enabled.set(True)

            # validate
            metadata = app.map_manager.get_metadata()
            if not metadata:
                # delete if invalid
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                app.config.map_offline_path.set(None)
                app.config.map_offline_enabled.set(False)
                return web.json_response(
                    {
                        "error": "Invalid MBTiles file or unsupported format (vector maps not supported)",
                    },
                    status=400,
                )

            return web.json_response(
                {
                    "message": "Map uploaded successfully",
                    "metadata": metadata,
                },
            )
        except Exception as e:
            RNS.log(f"Error uploading map: {e}", RNS.LOG_ERROR)
            return web.json_response({"error": str(e)}, status=500)

    # start map export

    # start map export
    @routes.post("/api/v1/map/export")
    async def start_map_export(request):
        try:
            data = await request.json()
            bbox = data.get("bbox")  # [min_lon, min_lat, max_lon, max_lat]
            min_zoom = int(data.get("min_zoom", 0))
            max_zoom = int(data.get("max_zoom", 10))
            name = data.get("name", "Exported Map")

            if not bbox or len(bbox) != 4:
                return web.json_response({"error": "Invalid bbox"}, status=400)

            app._require_outbound_http("map tile export")

            tile_count = app.map_manager.count_export_tiles(
                bbox,
                min_zoom,
                max_zoom,
            )
            if tile_count > MAX_EXPORT_TILES:
                return web.json_response(
                    {
                        "error": (
                            f"Export would download {tile_count} tiles; "
                            f"maximum allowed is {MAX_EXPORT_TILES}. "
                            "Shrink the area or lower max zoom."
                        ),
                    },
                    status=400,
                )

            export_id = secrets.token_hex(8)
            app.map_manager.start_export(export_id, bbox, min_zoom, max_zoom, name)

            return web.json_response({"export_id": export_id})
        except OutboundHttpBlockedError as e:
            return web.json_response({"error": str(e)}, status=403)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # get map export status

    # get map export status
    @routes.get("/api/v1/map/export/{export_id}")
    async def get_map_export_status(request):
        export_id = request.match_info.get("export_id")
        status = app.map_manager.get_export_status(export_id)
        if status:
            return web.json_response(status)
        return web.json_response({"error": "Export not found"}, status=404)

    # download exported map

    # download exported map
    @routes.get("/api/v1/map/export/{export_id}/download")
    async def download_map_export(request):
        export_id = request.match_info.get("export_id")
        status = app.map_manager.get_export_status(export_id)
        if status and status.get("status") == "completed":
            file_path = status.get("file_path")
            if os.path.exists(file_path):
                return web.FileResponse(
                    path=file_path,
                    headers={
                        "Content-Disposition": f'attachment; filename="map_export_{export_id}.mbtiles"',
                    },
                )
        return web.json_response(
            {"error": "File not ready or not found"},
            status=404,
        )

    # cancel/delete map export

    # cancel/delete map export
    @routes.delete("/api/v1/map/export/{export_id}")
    async def delete_map_export(request):
        export_id = request.match_info.get("export_id")
        if app.map_manager.cancel_export(export_id):
            return web.json_response({"message": "Export cancelled/deleted"})
        return web.json_response({"error": "Export not found"}, status=404)

    # MIME type fix middleware - ensures JavaScript files have correct Content-Type
