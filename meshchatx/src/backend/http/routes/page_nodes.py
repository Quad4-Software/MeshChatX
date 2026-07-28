# SPDX-License-Identifier: 0BSD
"""HTTP routes: page_nodes."""

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


def register_page_nodes_routes(routes, app):

    # --- Page Node API ---

    @routes.get("/api/v1/page-nodes")
    async def page_nodes_list(request):
        return web.json_response(app.page_node_manager.list_nodes())

    @routes.post("/api/v1/page-nodes")
    async def page_nodes_create(request):
        data = await request.json()
        name = data.get("name", "").strip()
        if not name:
            return web.json_response({"message": "Name is required"}, status=400)
        announce_enabled = bool(data.get("announce_enabled", True))
        announce_interval_seconds = data.get("announce_interval_seconds")
        node = app.page_node_manager.create_node(
            name,
            announce_enabled=announce_enabled,
            announce_interval_seconds=announce_interval_seconds,
        )
        return web.json_response(node.get_status())

    @routes.get("/api/v1/page-nodes/{node_id}")
    async def page_nodes_get(request):
        node_id = request.match_info["node_id"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        return web.json_response(node.get_status())

    @routes.delete("/api/v1/page-nodes/{node_id}")
    async def page_nodes_delete(request):
        node_id = request.match_info["node_id"]
        if app.page_node_manager.delete_node(node_id):
            return web.json_response({"message": "Node deleted"})
        return web.json_response({"message": "Node not found"}, status=404)

    @routes.post("/api/v1/page-nodes/{node_id}/start")
    async def page_nodes_start(request):
        node_id = request.match_info["node_id"]
        try:
            dest_hash = app.page_node_manager.start_node(node_id)
            node = app.page_node_manager.get_node(node_id)
            if node and node.running:
                app._register_local_page_node_announce(node)
            return web.json_response(
                {"destination_hash": dest_hash, "message": "Node started"},
            )
        except KeyError:
            return web.json_response({"message": "Node not found"}, status=404)

    @routes.post("/api/v1/page-nodes/{node_id}/stop")
    async def page_nodes_stop(request):
        node_id = request.match_info["node_id"]
        try:
            app.page_node_manager.stop_node(node_id)
            return web.json_response({"message": "Node stopped"})
        except KeyError:
            return web.json_response({"message": "Node not found"}, status=404)

    @routes.post("/api/v1/page-nodes/{node_id}/announce")
    async def page_nodes_announce(request):
        node_id = request.match_info["node_id"]
        try:
            node = app.page_node_manager.get_node(node_id)
            if node is None or not node.running:
                return web.json_response(
                    {"message": "Node not running"},
                    status=400,
                )
            node.announce()
            app._register_local_page_node_announce(node)
            return web.json_response({"message": "Announced"})
        except KeyError:
            return web.json_response({"message": "Node not found"}, status=404)

    @routes.put("/api/v1/page-nodes/{node_id}/rename")
    async def page_nodes_rename(request):
        node_id = request.match_info["node_id"]
        data = await request.json()
        new_name = data.get("name", "").strip()
        if not new_name:
            return web.json_response({"message": "Name is required"}, status=400)
        try:
            app.page_node_manager.rename_node(node_id, new_name)
            return web.json_response({"message": "Renamed"})
        except KeyError:
            return web.json_response({"message": "Node not found"}, status=404)

    @routes.patch("/api/v1/page-nodes/{node_id}/announce-settings")
    async def page_nodes_update_announce_settings(request):
        node_id = request.match_info["node_id"]
        try:
            data = await request.json()
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid request body: {e}"},
                status=400,
            )
        announce_enabled = (
            data.get("announce_enabled") if "announce_enabled" in data else None
        )
        announce_interval_seconds = (
            data.get("announce_interval_seconds")
            if "announce_interval_seconds" in data
            else None
        )
        try:
            node = app.page_node_manager.set_announce_settings(
                node_id,
                announce_enabled=announce_enabled,
                announce_interval_seconds=announce_interval_seconds,
            )
            return web.json_response(node.get_status())
        except KeyError:
            return web.json_response({"message": "Node not found"}, status=404)

    @routes.get("/api/v1/page-nodes/{node_id}/pages")
    async def page_nodes_list_pages(request):
        node_id = request.match_info["node_id"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        return web.json_response({"pages": node.list_pages()})

    @routes.post("/api/v1/page-nodes/{node_id}/pages")
    async def page_nodes_add_page(request):
        node_id = request.match_info["node_id"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        try:
            data = await request.json()
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid request body: {e}"},
                status=400,
            )
        name = data.get("name", "")
        content = data.get("content", "")
        if not name:
            return web.json_response(
                {"message": "Page name is required"},
                status=400,
            )
        try:
            saved_name = node.add_page(name, content)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except OSError as e:
            return web.json_response(
                {"message": f"Failed to write page: {e}"},
                status=500,
            )
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to save page: {e}"},
                status=500,
            )
        return web.json_response({"name": saved_name, "message": "Page saved"})

    @routes.get("/api/v1/page-nodes/{node_id}/pages/{page_name}")
    async def page_nodes_get_page(request):
        node_id = request.match_info["node_id"]
        page_name = request.match_info["page_name"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        content = node.get_page_content(page_name)
        if content is None:
            return web.json_response({"message": "Page not found"}, status=404)
        return web.json_response({"name": page_name, "content": content})

    @routes.delete("/api/v1/page-nodes/{node_id}/pages/{page_name}")
    async def page_nodes_delete_page(request):
        node_id = request.match_info["node_id"]
        page_name = request.match_info["page_name"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        if node.remove_page(page_name):
            return web.json_response({"message": "Page deleted"})
        return web.json_response({"message": "Page not found"}, status=404)

    @routes.get("/api/v1/page-nodes/{node_id}/files")
    async def page_nodes_list_files(request):
        node_id = request.match_info["node_id"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        return web.json_response({"files": node.list_files()})

    @routes.post("/api/v1/page-nodes/{node_id}/files")
    async def page_nodes_upload_file(request):
        node_id = request.match_info["node_id"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        try:
            reader = await request.multipart()
            field = await reader.next()
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid upload request: {e}"},
                status=400,
            )
        if field is None:
            return web.json_response({"message": "No file uploaded"}, status=400)
        filename = field.filename or "upload"
        try:
            file_data = await field.read()
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to read upload: {e}"},
                status=400,
            )
        try:
            saved_name = node.add_file(filename, file_data)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except OSError as e:
            return web.json_response(
                {"message": f"Failed to write file: {e}"},
                status=500,
            )
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to save file: {e}"},
                status=500,
            )
        return web.json_response({"name": saved_name, "message": "File uploaded"})

    @routes.delete("/api/v1/page-nodes/{node_id}/files/{file_name}")
    async def page_nodes_delete_file(request):
        node_id = request.match_info["node_id"]
        file_name = request.match_info["file_name"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        if node.remove_file(file_name):
            return web.json_response({"message": "File deleted"})
        return web.json_response({"message": "File not found"}, status=404)
