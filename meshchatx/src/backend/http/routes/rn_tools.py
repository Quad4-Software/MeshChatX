# SPDX-License-Identifier: 0BSD
"""HTTP routes: rn_tools."""

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


def register_rn_tools_routes(routes, app):

    def _rnsh_require_manager():
        manager = app.rnsh_manager
        if manager is None:
            return None, web.json_response(
                {"message": "RNSH manager is not available"},
                status=503,
            )
        return manager, None

    @routes.get("/api/v1/rnsh/sessions")
    async def rnsh_sessions_get(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        return web.json_response(manager.list_sessions())

    @routes.post("/api/v1/rnsh/sessions")
    async def rnsh_sessions_post(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        data = await request.json()
        try:
            session = manager.create_session(data or {})
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        autostart = bool((data or {}).get("autostart", True))
        if autostart:
            try:
                session.start()
            except Exception as e:
                with contextlib.suppress(Exception):
                    manager.remove_session(session.session_id)
                return web.json_response({"message": str(e)}, status=400)
        return web.json_response(
            {"session": session.to_dict(include_output_tail=True)},
        )

    @routes.delete("/api/v1/rnsh/sessions/{session_id}")
    async def rnsh_sessions_delete(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            manager.remove_session(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        return web.json_response({"message": "Session removed"})

    @routes.post("/api/v1/rnsh/sessions/{session_id}/start")
    async def rnsh_session_start(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.start_session(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnsh/sessions/{session_id}/stop")
    async def rnsh_session_stop(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.stop_session(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnsh/sessions/{session_id}/input")
    async def rnsh_session_input(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        data = await request.json()
        text = data.get("text")
        if not isinstance(text, str):
            return web.json_response(
                {"message": "Input text is required"},
                status=400,
            )
        add_newline = bool(data.get("newline", False))
        if add_newline and not text.endswith("\n"):
            text += "\n"
        try:
            session = manager.send_input(session_id, text)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnsh/sessions/{session_id}/resize")
    async def rnsh_session_resize(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        data = await request.json()
        rows = (data or {}).get("rows")
        cols = (data or {}).get("cols")
        try:
            session = manager.resize_session(session_id, rows, cols)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.get("/api/v1/rnsh/sessions/{session_id}/output")
    async def rnsh_session_output(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        cursor = request.query.get("cursor", 0)
        try:
            payload = manager.output_since(session_id, cursor)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response(payload)

    @routes.post("/api/v1/rnsh/sessions/{session_id}/clear")
    async def rnsh_session_clear(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.clear_output(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    def _rnx_require_manager():
        manager = app.rnx_manager
        if manager is None:
            return None, web.json_response(
                {"message": "RNX manager is not available"},
                status=503,
            )
        return manager, None

    @routes.get("/api/v1/rnx/sessions")
    async def rnx_sessions_get(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        return web.json_response(manager.list_sessions())

    @routes.post("/api/v1/rnx/sessions")
    async def rnx_sessions_post(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        data = await request.json()
        session = manager.create_session(data or {})
        autostart = bool((data or {}).get("autostart", True))
        if autostart:
            try:
                session.start()
            except Exception as e:
                with contextlib.suppress(Exception):
                    manager.remove_session(session.session_id)
                return web.json_response({"message": str(e)}, status=400)
        return web.json_response(
            {"session": session.to_dict(include_output_tail=True)},
        )

    @routes.delete("/api/v1/rnx/sessions/{session_id}")
    async def rnx_sessions_delete(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            manager.remove_session(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        return web.json_response({"message": "Session removed"})

    @routes.post("/api/v1/rnx/sessions/{session_id}/start")
    async def rnx_session_start(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.start_session(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnx/sessions/{session_id}/stop")
    async def rnx_session_stop(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.stop_session(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnx/sessions/{session_id}/input")
    async def rnx_session_input(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        data = await request.json()
        text = data.get("text")
        if not isinstance(text, str):
            return web.json_response(
                {"message": "Input text is required"},
                status=400,
            )
        add_newline = bool(data.get("newline", False))
        if add_newline and not text.endswith("\n"):
            text += "\n"
        try:
            session = manager.send_input(session_id, text)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnx/sessions/{session_id}/resize")
    async def rnx_session_resize(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        data = await request.json()
        rows = (data or {}).get("rows")
        cols = (data or {}).get("cols")
        try:
            session = manager.resize_session(session_id, rows, cols)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.get("/api/v1/rnx/sessions/{session_id}/output")
    async def rnx_session_output(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        cursor = request.query.get("cursor", 0)
        try:
            payload = manager.output_since(session_id, cursor)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response(payload)

    @routes.post("/api/v1/rnx/sessions/{session_id}/clear")
    async def rnx_session_clear(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.clear_output(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.post("/api/v1/rncp/send")
    async def rncp_send(request):
        data = await request.json()
        destination_hash_str = data.get("destination_hash", "")
        file_path = data.get("file_path", "")
        timeout_raw = data.get("timeout")
        try:
            timeout = float(timeout_raw) if timeout_raw not in (None, "") else None
        except (TypeError, ValueError):
            timeout = None
        no_compress = bool(data.get("no_compress", False))

        try:
            destination_hash = bytes.fromhex(destination_hash_str)
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid destination hash: {e}"},
                status=400,
            )

        transfer_id = None

        def on_transfer_started(tid):
            nonlocal transfer_id
            transfer_id = tid

        def on_progress(progress):
            if transfer_id:
                AsyncUtils.run_async(
                    app._broadcast_websocket_message(
                        {
                            "type": "rncp.transfer.progress",
                            "transfer_id": transfer_id,
                            "progress": progress,
                        },
                    ),
                )

        try:
            result = await app.rncp_handler.send_file(
                destination_hash=destination_hash,
                file_path=file_path,
                timeout=timeout,
                on_progress=on_progress,
                no_compress=no_compress,
                on_transfer_started=on_transfer_started,
            )
            AsyncUtils.run_async(
                app._broadcast_websocket_message(
                    {
                        "type": "rncp.send.completed",
                        "transfer_id": result["transfer_id"],
                        "file_path": result.get("file_path"),
                        "status": "completed",
                    },
                ),
            )
            return web.json_response(result)
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/rncp/fetch")
    async def rncp_fetch(request):
        data = await request.json()
        destination_hash_str = data.get("destination_hash", "")
        file_path = data.get("file_path", "")
        timeout_raw = data.get("timeout")
        try:
            timeout = float(timeout_raw) if timeout_raw not in (None, "") else None
        except (TypeError, ValueError):
            timeout = None
        save_path = data.get("save_path")
        allow_overwrite = bool(data.get("allow_overwrite", False))

        try:
            destination_hash = bytes.fromhex(destination_hash_str)
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid destination hash: {e}"},
                status=400,
            )

        transfer_id = None

        def on_transfer_started(tid):
            nonlocal transfer_id
            transfer_id = tid

        def on_progress(progress):
            if transfer_id:
                AsyncUtils.run_async(
                    app._broadcast_websocket_message(
                        {
                            "type": "rncp.transfer.progress",
                            "transfer_id": transfer_id,
                            "progress": progress,
                        },
                    ),
                )

        try:
            result = await app.rncp_handler.fetch_file(
                destination_hash=destination_hash,
                file_path=file_path,
                timeout=timeout,
                on_progress=on_progress,
                save_path=save_path,
                allow_overwrite=allow_overwrite,
                on_transfer_started=on_transfer_started,
            )
            AsyncUtils.run_async(
                app._broadcast_websocket_message(
                    {
                        "type": "rncp.fetch.completed",
                        "file_path": result.get("file_path"),
                        "status": "completed",
                    },
                ),
            )
            return web.json_response(result)
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.get("/api/v1/rncp/transfer/{transfer_id}")
    async def rncp_transfer_status(request):
        transfer_id = request.match_info.get("transfer_id", "")
        status = app.rncp_handler.get_transfer_status(transfer_id)
        if status:
            return web.json_response(status)
        return web.json_response(
            {"message": "Transfer not found"},
            status=404,
        )

    @routes.post("/api/v1/rncp/listen")
    async def rncp_listen(request):
        data = await request.json()
        allowed_hashes = data.get("allowed_hashes", [])
        fetch_allowed = bool(data.get("fetch_allowed", False))
        fetch_jail = data.get("fetch_jail")
        allow_overwrite = bool(data.get("allow_overwrite", False))

        try:
            destination_hash = app.rncp_handler.setup_receive_destination(
                allowed_hashes=allowed_hashes,
                fetch_allowed=fetch_allowed,
                fetch_jail=fetch_jail,
                allow_overwrite=allow_overwrite,
            )
            return web.json_response(
                {
                    "destination_hash": destination_hash,
                    "message": "RNCP listener started",
                },
            )
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.get("/api/v1/rncp/status")
    async def rncp_status(_request):
        return web.json_response(app.rncp_handler.get_listener_status())

    @routes.post("/api/v1/rncp/stop")
    async def rncp_stop(_request):
        try:
            app.rncp_handler.teardown_receive_destination()
            return web.json_response({"message": "RNCP listener stopped"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.post("/api/v1/rncp/cancel")
    async def rncp_cancel(request):
        data = {}
        with contextlib.suppress(Exception):
            data = await request.json()
        transfer_id = None
        if isinstance(data, dict):
            raw = data.get("transfer_id")
            if isinstance(raw, str) and raw.strip():
                transfer_id = raw.strip()
        try:
            result = app.rncp_handler.cancel_transfer(transfer_id)
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # --- RNS FileSync ---

    @routes.get("/api/v1/rnstatus")
    async def rnstatus(request):
        include_link_stats = request.query.get("include_link_stats", "false") in (
            "true",
            "1",
        )
        sorting = request.query.get("sorting")
        sort_reverse = request.query.get("sort_reverse", "false") in ("true", "1")
        remote = (request.query.get("remote") or "").strip()
        identity_path = (request.query.get("identity_path") or "").strip() or None
        identity_name = (request.query.get("identity_name") or "").strip() or None
        timeout_raw = request.query.get("timeout")

        not_ready = app._require_rns_tool_handler(
            app.rnstatus_handler,
            "RNStatus",
        )
        if not_ready is not None:
            return not_ready

        try:
            timeout = float(timeout_raw) if timeout_raw not in (None, "") else None
        except (TypeError, ValueError):
            return web.json_response({"message": "Invalid timeout"}, status=400)

        try:
            if remote:
                from meshchatx.src.backend.remote_management_client import (
                    fetch_remote_status,
                )

                if not identity_path and not identity_name:
                    return web.json_response(
                        {
                            "message": "identity_path or identity_name is required for remote queries",
                        },
                        status=400,
                    )
                stats, link_count = await asyncio.to_thread(
                    fetch_remote_status,
                    remote_transport_hash=remote,
                    identity_path=identity_path,
                    identity_name=identity_name,
                    reticulum_config_dir=getattr(app, "reticulum_config_dir", None),
                    include_link_stats=include_link_stats,
                    timeout=timeout,
                )
                status = app.rnstatus_handler.get_status(
                    include_link_stats=include_link_stats,
                    sorting=sorting,
                    sort_reverse=sort_reverse,
                    stats=stats,
                    link_count=link_count,
                    include_local_blackhole=False,
                )
                status["remote"] = remote
            else:
                status = app.rnstatus_handler.get_status(
                    include_link_stats=include_link_stats,
                    sorting=sorting,
                    sort_reverse=sort_reverse,
                )
            return web.json_response(status)
        except (ValueError, FileNotFoundError) as e:
            return web.json_response({"message": str(e)}, status=400)
        except TimeoutError as e:
            return web.json_response({"message": str(e)}, status=504)
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.get("/api/v1/rnpath/table")
    async def rnpath_table(request):
        def _optional_int(raw, field_name):
            if raw in (None, ""):
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                raise ValueError(f"Invalid {field_name}") from None

        try:
            max_hops = _optional_int(request.query.get("max_hops"), "max_hops")
            hops = _optional_int(request.query.get("hops"), "hops")
            page = int(request.query.get("page", 1))
            limit = int(request.query.get("limit", 50))
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)

        search = request.query.get("search")
        interface = request.query.get("interface")
        remote = (request.query.get("remote") or "").strip()
        identity_path = (request.query.get("identity_path") or "").strip() or None
        identity_name = (request.query.get("identity_name") or "").strip() or None
        timeout_raw = request.query.get("timeout")

        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready

        try:
            timeout = float(timeout_raw) if timeout_raw not in (None, "") else None
        except (TypeError, ValueError):
            return web.json_response({"message": "Invalid timeout"}, status=400)

        try:
            raw_table = None
            if remote:
                from meshchatx.src.backend.remote_management_client import (
                    fetch_remote_path_table,
                )

                if not identity_path and not identity_name:
                    return web.json_response(
                        {
                            "message": "identity_path or identity_name is required for remote queries",
                        },
                        status=400,
                    )
                raw_table = await asyncio.to_thread(
                    fetch_remote_path_table,
                    remote_transport_hash=remote,
                    identity_path=identity_path,
                    identity_name=identity_name,
                    reticulum_config_dir=getattr(app, "reticulum_config_dir", None),
                    max_hops=max_hops,
                    timeout=timeout,
                )
            result = app.rnpath_handler.get_path_table(
                max_hops=max_hops,
                search=search,
                interface=interface,
                hops=hops,
                page=page,
                limit=limit,
                raw_table=raw_table,
            )
            if remote:
                result["remote"] = remote
            return web.json_response(result)
        except (ValueError, FileNotFoundError) as e:
            return web.json_response({"message": str(e)}, status=400)
        except TimeoutError as e:
            return web.json_response({"message": str(e)}, status=504)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.get("/api/v1/rnpath/rates")
    async def rnpath_rates(request):
        remote = (request.query.get("remote") or "").strip()
        identity_path = (request.query.get("identity_path") or "").strip() or None
        identity_name = (request.query.get("identity_name") or "").strip() or None
        timeout_raw = request.query.get("timeout")

        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready

        try:
            timeout = float(timeout_raw) if timeout_raw not in (None, "") else None
        except (TypeError, ValueError):
            return web.json_response({"message": "Invalid timeout"}, status=400)

        try:
            raw_table = None
            if remote:
                from meshchatx.src.backend.remote_management_client import (
                    fetch_remote_rate_table,
                )

                if not identity_path and not identity_name:
                    return web.json_response(
                        {
                            "message": "identity_path or identity_name is required for remote queries",
                        },
                        status=400,
                    )
                raw_table = await asyncio.to_thread(
                    fetch_remote_rate_table,
                    remote_transport_hash=remote,
                    identity_path=identity_path,
                    identity_name=identity_name,
                    reticulum_config_dir=getattr(app, "reticulum_config_dir", None),
                    timeout=timeout,
                )
            rates = app.rnpath_handler.get_rate_table(raw_table=raw_table)
            payload = {"rates": rates}
            if remote:
                payload["remote"] = remote
            return web.json_response(payload)
        except (ValueError, FileNotFoundError) as e:
            return web.json_response({"message": str(e)}, status=400)
        except TimeoutError as e:
            return web.json_response({"message": str(e)}, status=504)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.post("/api/v1/rnpath/drop")
    async def rnpath_drop(request):
        data = await request.json()
        destination_hash = data.get("destination_hash")
        if not destination_hash:
            return web.json_response(
                {"message": "destination_hash is required"},
                status=400,
            )
        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready
        try:
            success = app.rnpath_handler.drop_path(destination_hash)
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.post("/api/v1/rnpath/drop-via")
    async def rnpath_drop_via(request):
        data = await request.json()
        transport_instance_hash = data.get("transport_instance_hash")
        if not transport_instance_hash:
            return web.json_response(
                {"message": "transport_instance_hash is required"},
                status=400,
            )
        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready
        try:
            success = app.rnpath_handler.drop_all_via(transport_instance_hash)
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.post("/api/v1/rnpath/drop-queues")
    async def rnpath_drop_queues(request):
        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready
        try:
            app.rnpath_handler.drop_announce_queues()
            return web.json_response({"success": True})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.post("/api/v1/rnpath/request")
    async def rnpath_request(request):
        data = await request.json()
        destination_hash = data.get("destination_hash")
        if not destination_hash:
            return web.json_response(
                {"message": "destination_hash is required"},
                status=400,
            )
        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready
        try:
            success = app.rnpath_handler.request_path(destination_hash)
            return web.json_response({"success": success})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.get("/api/v1/rnpath/trace/{destination_hash}")
    async def rnpath_trace(request):
        destination_hash = request.match_info.get("destination_hash")
        if not destination_hash:
            return web.json_response(
                {"error": "destination_hash is required"},
                status=400,
            )
        try:
            if not app.rnpath_trace_handler:
                return web.json_response(
                    {
                        "error": "RNPathTraceHandler not initialized for current context",
                    },
                    status=503,
                )
            result = await app.rnpath_trace_handler.trace_path(destination_hash)
            return web.json_response(result)
        except Exception:
            logger.exception("RN path trace route failed")
            return web.json_response({"error": "Trace failed"}, status=500)

    @routes.post("/api/v1/rnprobe")
    async def rnprobe(request):
        data = await request.json()
        destination_hash_str = data.get("destination_hash", "")
        full_name = data.get("full_name", "")
        try:
            size = int(data.get("size", RNProbeHandler.DEFAULT_PROBE_SIZE))
        except (TypeError, ValueError):
            return web.json_response({"message": "Invalid size"}, status=400)
        try:
            wait = float(data.get("wait", 0))
        except (TypeError, ValueError):
            return web.json_response({"message": "Invalid wait"}, status=400)
        try:
            probes = int(data.get("probes", 1))
        except (TypeError, ValueError):
            return web.json_response({"message": "Invalid probes"}, status=400)

        timeout = None
        raw_timeout = data.get("timeout", 0)
        if raw_timeout is not None:
            try:
                t = float(raw_timeout)
            except (TypeError, ValueError):
                return web.json_response({"message": "Invalid timeout"}, status=400)
            if t != 0:
                timeout = t

        try:
            destination_hash = bytes.fromhex(destination_hash_str)
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid destination hash: {e}"},
                status=400,
            )

        if not full_name:
            return web.json_response(
                {"message": "full_name is required"},
                status=400,
            )

        not_ready = app._require_rns_tool_handler(app.rnprobe_handler, "RNProbe")
        if not_ready is not None:
            return not_ready

        try:
            result = await app.rnprobe_handler.probe_destination(
                destination_hash=destination_hash,
                full_name=full_name,
                size=size,
                timeout=timeout,
                wait=wait,
                probes=probes,
            )
            return web.json_response(result)
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )
