# SPDX-License-Identifier: 0BSD
"""WebSocket handlers: handlers_nomad."""

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


async def handle_nomadnet_download_cancel(app, client, data):
    # get data from websocket client
    download_id = data.get("download_id")
    if download_id is None:
        return

    # cancel the download
    if download_id in app.active_downloads:
        downloader = app.active_downloads[download_id]
        downloader.cancel()
        del app.active_downloads[download_id]

        # notify client
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.download.cancelled",
                        "download_id": download_id,
                    },
                ),
            ),
        )

    # handle getting page archives


async def handle_nomadnet_page_archives_get(app, client, data):
    destination_hash = data.get("destination_hash")
    page_path = data.get("page_path")

    if not destination_hash or not page_path:
        return

    # Try relative path first
    archives = app.get_archived_page_versions(destination_hash, page_path)

    # If nothing found and path doesn't look like it's already absolute,
    # try searching with the destination hash prefix (support for old buggy archives)
    if not archives and not page_path.startswith(destination_hash):
        buggy_path = f"{destination_hash}:{page_path}"
        archives = app.get_archived_page_versions(destination_hash, buggy_path)

    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": "nomadnet.page.archives",
                    "destination_hash": destination_hash,
                    "page_path": page_path,
                    "archives": [
                        {
                            "id": archive["id"],
                            "hash": archive["hash"],
                            "destination_hash": archive["destination_hash"],
                            "page_path": archive["page_path"],
                            "created_at": archive["created_at"].isoformat()
                            if hasattr(archive["created_at"], "isoformat")
                            else str(archive["created_at"]),
                        }
                        for archive in archives
                    ],
                },
            ),
        ),
    )

    # handle loading a specific archived page version


async def handle_nomadnet_page_archive_load(app, client, data):
    archive_id = data.get("archive_id")
    download_id = data.get("download_id")
    if archive_id is None:
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.page.download",
                        "download_id": download_id,
                        "nomadnet_page_download": {
                            "status": "failure",
                            "destination_hash": "",
                            "page_path": "",
                            "failure_reason": "missing archive_id",
                        },
                    },
                ),
            ),
        )
        return

    archive = app.database.misc.get_archived_page_by_id(archive_id)

    if archive:
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.page.download",
                        "download_id": download_id,
                        "nomadnet_page_download": {
                            "status": "success",
                            "destination_hash": archive["destination_hash"],
                            "page_path": archive["page_path"],
                            "page_content": archive["content"],
                            "is_archived_version": True,
                            "archived_at": archive["created_at"],
                        },
                    },
                ),
            ),
        )
        return

    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": "nomadnet.page.download",
                    "download_id": download_id,
                    "nomadnet_page_download": {
                        "status": "failure",
                        "destination_hash": "",
                        "page_path": "",
                        "failure_reason": "archive not found",
                    },
                },
            ),
        ),
    )

    # handle flushing all archived pages


async def handle_nomadnet_page_archive_flush(app, client, data):
    app.flush_all_archived_pages()
    # notify config updated
    AsyncUtils.run_async(app.send_config_to_websocket_clients())

    # handle manual page archiving


async def handle_nomadnet_page_archive_add(app, client, data):
    destination_hash = data.get("destination_hash")
    page_path = data.get("page_path")
    content = data.get("content")

    if not destination_hash or not page_path or not content:
        return

    app.archive_page(destination_hash, page_path, content, is_manual=True)

    # notify client that page was archived
    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": "nomadnet.page.archive.added",
                    "destination_hash": destination_hash,
                    "page_path": page_path,
                },
            ),
        ),
    )

    # handle downloading a file from a nomadnet node


async def handle_nomadnet_file_download(app, client, data):
    # get data from websocket client
    download_data = data.get("nomadnet_file_download")
    if not download_data:
        return

    destination_hash_hex = download_data.get("destination_hash")
    file_path = download_data.get("file_path")
    request_data = download_data.get("data")
    private = bool(download_data.get("private"))
    if isinstance(request_data, str):
        request_data = convert_nomadnet_string_data_to_map(request_data)
    elif request_data is None:
        request_data = {}

    if not destination_hash_hex or not file_path:
        return

    try:
        destination_hash = bytes.fromhex(destination_hash_hex)
    except ValueError:
        return

    local_file = app._try_serve_local_page_node_file(
        destination_hash,
        file_path,
    )
    if local_file is not None:
        file_name, file_bytes = local_file
        app.download_id_counter += 1
        download_id = app.download_id_counter
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.file.download",
                        "download_id": download_id,
                        "nomadnet_file_download": {
                            "status": "success",
                            "destination_hash": destination_hash.hex(),
                            "file_path": file_path,
                            "file_name": file_name,
                            "file_bytes": base64.b64encode(file_bytes).decode(
                                "utf-8",
                            ),
                            "private": private,
                        },
                    },
                ),
            ),
        )
        return

    # generate download id
    app.download_id_counter += 1
    download_id = app.download_id_counter

    # handle successful file download
    def on_file_download_success(file_name, file_bytes):
        # remove from active downloads
        if download_id in app.active_downloads:
            del app.active_downloads[download_id]

        # Track download speed
        download_size = len(file_bytes)
        if hasattr(downloader, "start_time") and downloader.start_time:
            download_duration = time.time() - downloader.start_time
            if download_duration > 0:
                app.download_speeds.append((download_size, download_duration))
                # Keep only last 100 downloads for average calculation
                if len(app.download_speeds) > 100:
                    app.download_speeds.pop(0)

        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.file.download",
                        "download_id": download_id,
                        "nomadnet_file_download": {
                            "status": "success",
                            "destination_hash": destination_hash.hex(),
                            "file_path": file_path,
                            "file_name": file_name,
                            "file_bytes": base64.b64encode(file_bytes).decode(
                                "utf-8",
                            ),
                        },
                    },
                ),
            ),
        )

    # handle file download failure
    def on_file_download_failure(failure_reason):
        # remove from active downloads
        if download_id in app.active_downloads:
            del app.active_downloads[download_id]

        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.file.download",
                        "download_id": download_id,
                        "nomadnet_file_download": {
                            "status": "failure",
                            "failure_reason": failure_reason,
                            "destination_hash": destination_hash.hex(),
                            "file_path": file_path,
                        },
                    },
                ),
            ),
        )

    # handle file download progress
    def on_file_download_progress(progress):
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.file.download",
                        "download_id": download_id,
                        "nomadnet_file_download": {
                            "status": "progress",
                            "progress": progress,
                            "destination_hash": destination_hash.hex(),
                            "file_path": file_path,
                        },
                    },
                ),
            ),
        )

    def on_file_download_phase(phase: str):
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.file.download",
                        "download_id": download_id,
                        "nomadnet_file_download": {
                            "status": "phase",
                            "load_phase": phase,
                            "destination_hash": destination_hash.hex(),
                            "file_path": file_path,
                        },
                    },
                ),
            ),
        )

    # download the file
    downloader = NomadnetFileDownloader(
        destination_hash,
        file_path,
        on_file_download_success,
        on_file_download_failure,
        on_file_download_progress,
        data=request_data,
        on_phase=on_file_download_phase,
        reticulum=getattr(app, "reticulum", None),
        private=private,
    )
    downloader.start_time = time.time()
    app.active_downloads[download_id] = downloader

    # notify client download started (await so phase updates cannot reorder ahead of started)
    await client.send_str(
        json.dumps(
            {
                "type": "nomadnet.file.download",
                "download_id": download_id,
                "nomadnet_file_download": {
                    "status": "started",
                    "destination_hash": destination_hash.hex(),
                    "file_path": file_path,
                },
            },
        ),
    )

    AsyncUtils.run_async(downloader.download())

    # handle downloading a page from a nomadnet node


async def handle_nomadnet_page_download(app, client, data):
    # get data from websocket client
    page_download_data = data.get("nomadnet_page_download")
    if not page_download_data:
        return

    destination_hash = page_download_data.get("destination_hash")
    page_path = page_download_data.get("page_path")
    field_data = page_download_data.get("field_data")
    private = bool(page_download_data.get("private"))

    if not destination_hash or not page_path:
        return

    # generate download id
    app.download_id_counter += 1
    download_id = app.download_id_counter

    combined_data = {}
    # parse data from page path
    # example path then backtick then field1=123|field2=456
    page_data = None
    page_path_to_download = page_path
    if "`" in page_path:
        page_path_parts = page_path.split("`")
        page_path_to_download = page_path_parts[0]
        page_data = convert_nomadnet_string_data_to_map(page_path_parts[1])

    # Field data
    field_data = convert_nomadnet_field_data_to_map(field_data)

    # Combine page data and field data
    if page_data is not None:
        combined_data.update(page_data)
    if field_data is not None:
        combined_data.update(field_data)

    # convert destination hash to bytes
    try:
        destination_hash = bytes.fromhex(destination_hash)
    except (TypeError, ValueError):
        return

    local_page = app._try_serve_local_page_node(
        destination_hash,
        page_path_to_download,
        request_data=combined_data,
    )
    if local_page is not None:
        if not private:
            app.archive_page(destination_hash.hex(), page_path, local_page)
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.page.download",
                        "download_id": download_id,
                        "nomadnet_page_download": {
                            "status": "success",
                            "destination_hash": destination_hash.hex(),
                            "page_path": page_path,
                            "page_content": local_page,
                            "private": private,
                        },
                    },
                ),
            ),
        )
        return

    # handle successful page download
    def on_page_download_success(page_content):
        # remove from active downloads
        if download_id in app.active_downloads:
            del app.active_downloads[download_id]

        # archive the page if enabled (never for private browse)
        if not private:
            app.archive_page(destination_hash.hex(), page_path, page_content)

        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.page.download",
                        "download_id": download_id,
                        "nomadnet_page_download": {
                            "status": "success",
                            "destination_hash": destination_hash.hex(),
                            "page_path": page_path,
                            "page_content": page_content,
                            "private": private,
                        },
                    },
                ),
            ),
        )

    # handle page download failure
    def on_page_download_failure(failure_reason):
        # remove from active downloads
        if download_id in app.active_downloads:
            del app.active_downloads[download_id]

        # check if there are any archived versions (not offered in private browse)
        has_archives = False
        if not private:
            has_archives = (
                len(
                    app.get_archived_page_versions(
                        destination_hash.hex(),
                        page_path,
                    ),
                )
                > 0
            )

        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.page.download",
                        "download_id": download_id,
                        "nomadnet_page_download": {
                            "status": "failure",
                            "failure_reason": failure_reason,
                            "destination_hash": destination_hash.hex(),
                            "page_path": page_path,
                            "has_archives": has_archives,
                        },
                    },
                ),
            ),
        )

    # handle page download progress
    def on_page_download_progress(progress):
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.page.download",
                        "download_id": download_id,
                        "nomadnet_page_download": {
                            "status": "progress",
                            "progress": progress,
                            "destination_hash": destination_hash.hex(),
                            "page_path": page_path,
                        },
                    },
                ),
            ),
        )

    def on_page_download_phase(phase: str):
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.page.download",
                        "download_id": download_id,
                        "nomadnet_page_download": {
                            "status": "phase",
                            "load_phase": phase,
                            "destination_hash": destination_hash.hex(),
                            "page_path": page_path,
                        },
                    },
                ),
            ),
        )

    # download the page
    downloader = NomadnetPageDownloader(
        destination_hash,
        page_path_to_download,
        combined_data,
        on_page_download_success,
        on_page_download_failure,
        on_page_download_progress,
        on_phase=on_page_download_phase,
        reticulum=getattr(app, "reticulum", None),
        private=private,
    )
    app.active_downloads[download_id] = downloader

    # notify client download started (await so phase updates cannot reorder ahead of started)
    await client.send_str(
        json.dumps(
            {
                "type": "nomadnet.page.download",
                "download_id": download_id,
                "nomadnet_page_download": {
                    "status": "started",
                    "destination_hash": destination_hash.hex(),
                    "page_path": page_path,
                },
            },
        ),
    )

    AsyncUtils.run_async(downloader.download())

    # handle lxmf forwarding rules


HANDLERS = {
    "nomadnet.download.cancel": handle_nomadnet_download_cancel,
    "nomadnet.page.archives.get": handle_nomadnet_page_archives_get,
    "nomadnet.page.archive.load": handle_nomadnet_page_archive_load,
    "nomadnet.page.archive.flush": handle_nomadnet_page_archive_flush,
    "nomadnet.page.archive.add": handle_nomadnet_page_archive_add,
    "nomadnet.file.download": handle_nomadnet_file_download,
    "nomadnet.page.download": handle_nomadnet_page_download,
}
