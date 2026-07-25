# SPDX-License-Identifier: 0BSD
"""HTTP routes: reticulum_instance."""

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


def register_reticulum_instance_routes(routes, app):

    # get or update reticulum discovery configuration
    @routes.get("/api/v1/reticulum/discovery")
    async def reticulum_discovery_get(request):
        reticulum_config = app._get_reticulum_section()
        discovery_config = {
            "discover_interfaces": reticulum_config.get("discover_interfaces"),
            "interface_discovery_sources": reticulum_config.get(
                "interface_discovery_sources",
            ),
            "interface_discovery_whitelist": reticulum_config.get(
                "interface_discovery_whitelist",
            ),
            "interface_discovery_blacklist": reticulum_config.get(
                "interface_discovery_blacklist",
            ),
            "required_discovery_value": reticulum_config.get(
                "required_discovery_value",
            ),
            "autoconnect_discovered_interfaces": reticulum_config.get(
                "autoconnect_discovered_interfaces",
                ReticulumMeshChat.DEFAULT_AUTOCONNECT_DISCOVERED_INTERFACES,
            ),
            "default_gravity": reticulum_config.get("default_gravity"),
            "autoconnect_interface_mode": reticulum_config.get(
                "autoconnect_interface_mode",
            ),
            "autoconnect_interface_gravity": reticulum_config.get(
                "autoconnect_interface_gravity",
            ),
            "autoconnect_announces_to_internal": reticulum_config.get(
                "autoconnect_announces_to_internal",
            ),
            "default_bootstrap_only": bool(
                app.current_context.config.default_bootstrap_only.get()
                if app.current_context and app.current_context.config
                else False,
            ),
            "network_identity": reticulum_config.get("network_identity"),
        }

        return web.json_response({"discovery": discovery_config})

    @routes.patch("/api/v1/reticulum/discovery")
    async def reticulum_discovery_patch(request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"message": "Invalid request body"},
                status=400,
            )

        reticulum_config = app._get_reticulum_section()

        def update_config_value(key):
            if key not in data:
                return
            value = data.get(key)
            # Treat 0 for autoconnect_discovered_interfaces the same as unset,
            # since Reticulum interprets 0 as False, causing bootstrap_only
            # interfaces to flap (0 >= 0 evaluates to True).
            if (
                value is None
                or value == ""
                or (key == "autoconnect_discovered_interfaces" and value == 0)
            ):
                reticulum_config.pop(key, None)
            else:
                if key in (
                    "interface_discovery_whitelist",
                    "interface_discovery_blacklist",
                ):
                    sanitized = ReticulumMeshChat.sanitize_discovery_patterns(value)
                    if sanitized:
                        reticulum_config[key] = ",".join(sanitized)
                    else:
                        reticulum_config.pop(key, None)
                    return
                reticulum_config[key] = value

        for key in (
            "discover_interfaces",
            "interface_discovery_sources",
            "interface_discovery_whitelist",
            "interface_discovery_blacklist",
            "required_discovery_value",
            "autoconnect_discovered_interfaces",
            "network_identity",
        ):
            update_config_value(key)

        if "autoconnect_interface_mode" in data:
            mode_raw = data.get("autoconnect_interface_mode")
            if mode_raw is None or mode_raw == "":
                reticulum_config.pop("autoconnect_interface_mode", None)
            else:
                mode = InterfaceEditor.normalize_interface_mode(mode_raw)
                if mode is None:
                    return web.json_response(
                        {
                            "message": (
                                "autoconnect_interface_mode must be one of: "
                                "full, gateway, access_point, pointtopoint, "
                                "roaming, boundary, internal"
                            ),
                        },
                        status=422,
                    )
                reticulum_config["autoconnect_interface_mode"] = mode

        if "autoconnect_announces_to_internal" in data:
            yn = InterfaceEditor.request_yes_no(
                data.get("autoconnect_announces_to_internal"),
            )
            if yn is None:
                raw = data.get("autoconnect_announces_to_internal")
                if raw is None or raw == "":
                    reticulum_config.pop("autoconnect_announces_to_internal", None)
                else:
                    return web.json_response(
                        {
                            "message": (
                                "autoconnect_announces_to_internal must be "
                                "a boolean or yes/no value"
                            ),
                        },
                        status=422,
                    )
            else:
                reticulum_config["autoconnect_announces_to_internal"] = yn

        for gravity_key in ("default_gravity", "autoconnect_interface_gravity"):
            if gravity_key not in data:
                continue
            value = data.get(gravity_key)
            if value is None or value == "":
                reticulum_config.pop(gravity_key, None)
                continue
            try:
                gravity = int(value)
            except (TypeError, ValueError):
                return web.json_response(
                    {"message": f"{gravity_key} must be an integer"},
                    status=422,
                )
            if gravity < -10_000 or gravity > 10_000:
                return web.json_response(
                    {"message": f"{gravity_key} must be between -10000 and 10000"},
                    status=422,
                )
            reticulum_config[gravity_key] = gravity

        # When discover_interfaces is off, also disable autoconnect so RNS
        # does not connect to any discovered interfaces.
        if "discover_interfaces" in data:
            disc_val = data["discover_interfaces"]
            if disc_val is False or str(disc_val).lower() in ("false", "no", "0"):
                reticulum_config.pop("autoconnect_discovered_interfaces", None)

        # default_bootstrap_only is a MeshChatX-only setting, so do NOT write it
        # to Reticulum config so discovered/auto-connected interfaces are
        # never affected. Clean up any stale value in Reticulum config.
        reticulum_config.pop("default_bootstrap_only", None)
        if (
            app.current_context
            and app.current_context.config
            and "default_bootstrap_only" in data
        ):
            app.current_context.config.default_bootstrap_only.set(
                bool(data.get("default_bootstrap_only")),
            )

        if not app._write_reticulum_config():
            return web.json_response(
                {"message": "Failed to write Reticulum config"},
                status=500,
            )

        try:
            reloaded = await app.reload_reticulum()
            if reloaded is False:
                return web.json_response(
                    {
                        "message": "Discovery settings saved but RNS reload failed",
                        "reloaded": False,
                    },
                    status=500,
                )
        except Exception as e:
            logger.debug(f"Failed to reload RNS after discovery config update: {e}")
            return web.json_response(
                {
                    "message": f"Discovery settings saved but RNS reload failed: {e}",
                    "reloaded": False,
                },
                status=500,
            )

        discovery_config = {
            "discover_interfaces": reticulum_config.get("discover_interfaces"),
            "interface_discovery_sources": reticulum_config.get(
                "interface_discovery_sources",
            ),
            "interface_discovery_whitelist": reticulum_config.get(
                "interface_discovery_whitelist",
            ),
            "interface_discovery_blacklist": reticulum_config.get(
                "interface_discovery_blacklist",
            ),
            "required_discovery_value": reticulum_config.get(
                "required_discovery_value",
            ),
            "autoconnect_discovered_interfaces": reticulum_config.get(
                "autoconnect_discovered_interfaces",
                ReticulumMeshChat.DEFAULT_AUTOCONNECT_DISCOVERED_INTERFACES,
            ),
            "default_gravity": reticulum_config.get("default_gravity"),
            "autoconnect_interface_mode": reticulum_config.get(
                "autoconnect_interface_mode",
            ),
            "autoconnect_interface_gravity": reticulum_config.get(
                "autoconnect_interface_gravity",
            ),
            "autoconnect_announces_to_internal": reticulum_config.get(
                "autoconnect_announces_to_internal",
            ),
            "default_bootstrap_only": bool(
                app.current_context.config.default_bootstrap_only.get()
                if app.current_context and app.current_context.config
                else False,
            ),
            "network_identity": reticulum_config.get("network_identity"),
            "reloaded": True,
        }

        return web.json_response({"discovery": discovery_config})

    @routes.get("/api/v1/reticulum/discovered-interfaces")
    async def reticulum_discovered_interfaces(request):
        try:
            discovery = InterfaceDiscovery(discover_interfaces=False)
            interfaces = discovery.list_discovered_interfaces()
            reticulum_config = app._get_reticulum_section()
            whitelist_patterns = reticulum_config.get(
                "interface_discovery_whitelist",
            )
            blacklist_patterns = reticulum_config.get(
                "interface_discovery_blacklist",
            )
            max_disc = 500
            if app.current_context and app.current_context.config:
                mv = app.current_context.config.discovered_interfaces_max_return.get()
                if mv is not None and mv > 0:
                    max_disc = min(int(mv), 50_000)
            if len(interfaces) > max_disc:
                interfaces = interfaces[:max_disc]
            active = []
            stats = app._get_interface_stats_payload().get("interfaces", [])
            for s in stats:
                name = s.get("name") or ""
                parsed_host = None
                parsed_port = None
                if "/" in name:
                    try:
                        host_port = name.split("/")[-1].strip("[]")
                        if ":" in host_port:
                            parsed_host, parsed_port = host_port.rsplit(
                                ":",
                                1,
                            )
                            try:
                                parsed_port = int(parsed_port)
                            except Exception:
                                parsed_port = None
                        else:
                            parsed_host = host_port
                    except Exception:
                        parsed_host = None
                        parsed_port = None

                host = s.get("target_host") or s.get("remote") or parsed_host
                port = s.get("target_port") or s.get("listen_port") or parsed_port
                transport_id = s.get("transport_id")
                if isinstance(transport_id, (bytes, bytearray)):
                    transport_id = transport_id.hex()

                active.append(
                    {
                        "name": name,
                        "short_name": s.get("short_name"),
                        "type": s.get("type"),
                        "target_host": host,
                        "target_port": port,
                        "listen_ip": s.get("listen_ip"),
                        "connected": s.get("connected"),
                        "online": s.get("online"),
                        "status": s.get("status"),
                        "transport_id": transport_id,
                        "network_id": s.get("network_id"),
                        "autoconnect_source": s.get("autoconnect_source"),
                        "txb": s.get("txb"),
                        "rxb": s.get("rxb"),
                    },
                )

            if len(active) > max_disc:
                active = active[:max_disc]

            def to_jsonable(obj):
                if isinstance(obj, bytes):
                    return obj.hex()
                if isinstance(obj, dict):
                    return {k: to_jsonable(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [to_jsonable(v) for v in obj]
                return obj

            normalized_interfaces = ReticulumMeshChat.normalize_discovered_ifac_fields(
                to_jsonable(interfaces),
            )
            whitelist_sanitized = ReticulumMeshChat.sanitize_discovery_patterns(
                whitelist_patterns,
            )
            blacklist_sanitized = ReticulumMeshChat.sanitize_discovery_patterns(
                blacklist_patterns,
            )
            for iface in normalized_interfaces:
                if not isinstance(iface, dict):
                    continue
                iface["is_allowed"] = (
                    ReticulumMeshChat.matches_discovery_pattern(
                        whitelist_sanitized,
                        iface,
                    )
                    if whitelist_patterns
                    else True
                )
                iface["is_blacklisted"] = (
                    ReticulumMeshChat.matches_discovery_pattern(
                        blacklist_sanitized,
                        iface,
                    )
                    if blacklist_patterns
                    else False
                )

            return web.json_response(
                {
                    "interfaces": normalized_interfaces,
                    "active": to_jsonable(active),
                },
            )
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to load discovered interfaces: {e!s}"},
                status=500,
            )

    # enable transport mode

    # enable transport mode
    @routes.post("/api/v1/reticulum/enable-transport")
    async def reticulum_enable_transport(request):
        # enable transport mode
        reticulum_config = app._get_reticulum_section()
        reticulum_config["enable_transport"] = True
        if not app._write_reticulum_config():
            return web.json_response(
                {
                    "message": "Failed to write Reticulum config",
                },
                status=500,
            )

        if not await app.reload_reticulum():
            return web.json_response(
                {
                    "message": "Transport mode was enabled in config, but RNS reload failed.",
                },
                status=500,
            )

        return web.json_response(
            {
                "message": "Transport mode enabled and RNS restarted successfully.",
            },
        )

    # disable transport mode

    # disable transport mode
    @routes.post("/api/v1/reticulum/disable-transport")
    async def reticulum_disable_transport(request):
        # disable transport mode
        reticulum_config = app._get_reticulum_section()
        reticulum_config["enable_transport"] = False
        i2p_support.disable_i2p_when_transport_off(
            app._get_interfaces_section(),
            reticulum_config,
        )
        if not app._write_reticulum_config():
            return web.json_response(
                {
                    "message": "Failed to write Reticulum config",
                },
                status=500,
            )

        if not await app.reload_reticulum():
            return web.json_response(
                {
                    "message": "Transport mode was disabled in config, but RNS reload failed.",
                },
                status=500,
            )

        return web.json_response(
            {
                "message": "Transport mode disabled and RNS restarted successfully.",
            },
        )

    @routes.get("/api/v1/reticulum/instance")
    async def reticulum_instance_get(request):
        """Shared-instance, RPC, and hop-obfuscation settings (Sideband parity)."""
        return web.json_response(
            {"instance": app._build_reticulum_instance_settings()},
        )

    @routes.patch("/api/v1/reticulum/instance")
    async def reticulum_instance_patch(request):
        """Update [reticulum] shared-instance / hop-obfuscation options and reload."""
        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"message": "Invalid request body"},
                status=400,
            )
        if not isinstance(data, dict):
            return web.json_response(
                {"message": "Invalid request body"},
                status=400,
            )

        reticulum_config = app._get_reticulum_section()
        changed = False

        bool_keys = (
            "share_instance",
            "local_hops_delta",
            "respond_to_probes",
            "enable_remote_management",
        )
        for key in bool_keys:
            if key not in data:
                continue
            reticulum_config[key] = app._format_rns_config_bool(
                app._parse_rns_config_bool(data.get(key), default=False),
            )
            changed = True

        if "instance_name" in data:
            name = data.get("instance_name")
            if name is None or str(name).strip() == "":
                reticulum_config.pop("instance_name", None)
            else:
                cleaned = str(name).strip()
                if len(cleaned) > 64 or any(c.isspace() for c in cleaned):
                    return web.json_response(
                        {
                            "message": "instance_name must be 1-64 characters without whitespace",
                        },
                        status=400,
                    )
                reticulum_config["instance_name"] = cleaned
            changed = True

        if "shared_instance_type" in data:
            raw_type = data.get("shared_instance_type")
            if raw_type is None or str(raw_type).strip() == "":
                reticulum_config.pop("shared_instance_type", None)
            else:
                cleaned_type = str(raw_type).strip().lower()
                if cleaned_type not in ("tcp", "unix"):
                    return web.json_response(
                        {
                            "message": "shared_instance_type must be 'tcp' or 'unix'",
                        },
                        status=400,
                    )
                reticulum_config["shared_instance_type"] = cleaned_type
            changed = True

        if "remote_management_allowed" in data:
            try:
                allowed = app._parse_rns_hash_list(
                    data.get("remote_management_allowed"),
                )
            except ValueError as e:
                return web.json_response({"message": str(e)}, status=400)
            if allowed:
                reticulum_config["remote_management_allowed"] = allowed
            else:
                reticulum_config.pop("remote_management_allowed", None)
            changed = True

        if not changed:
            return web.json_response(
                {"instance": app._build_reticulum_instance_settings()},
            )

        if not app._write_reticulum_config():
            return web.json_response(
                {"message": "Failed to write Reticulum config"},
                status=500,
            )

        if not await app.reload_reticulum():
            return web.json_response(
                {
                    "message": "Instance settings were saved, but RNS reload failed.",
                    "instance": app._build_reticulum_instance_settings(),
                },
                status=500,
            )

        return web.json_response(
            {
                "message": "Reticulum instance settings updated and RNS restarted.",
                "instance": app._build_reticulum_instance_settings(),
            },
        )

    @routes.get("/api/v1/reticulum/management-identities")
    async def reticulum_management_identities_get(request):
        from meshchatx.src.backend.management_identities import (
            list_management_identities,
        )

        identities = list_management_identities(
            getattr(app, "reticulum_config_dir", None),
        )
        return web.json_response({"identities": identities})

    @routes.post("/api/v1/reticulum/management-identities")
    async def reticulum_management_identities_post(request):
        from meshchatx.src.backend.management_identities import (
            create_management_identity,
        )

        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"message": "Invalid request body"},
                status=400,
            )
        name = (data or {}).get("name")
        force = bool((data or {}).get("force", False))
        try:
            identity = create_management_identity(
                getattr(app, "reticulum_config_dir", None),
                name or "",
                force=force,
            )
        except FileExistsError as e:
            return web.json_response({"message": str(e)}, status=409)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        return web.json_response({"identity": identity})

    @routes.post("/api/v1/reticulum/reload")
    async def reticulum_reload(request):
        success = await app.reload_reticulum()
        if success:
            return web.json_response({"message": "Reticulum reloaded successfully"})
        return web.json_response(
            {"error": "Failed to reload Reticulum"},
            status=500,
        )

    @routes.get("/api/v1/reticulum/config/raw")
    async def reticulum_config_raw_get(request):
        """Return the raw text of the Reticulum config file.

        Used by the Reticulum Config Editor utility (mostly for mobile
        clients where the file is stored inside private app storage and
        cannot easily be opened with an external editor).
        """
        try:
            app._ensure_reticulum_config(materialize=False)
            config_path = app._reticulum_config_file_path()
            if not os.path.exists(config_path):
                return web.json_response(
                    {"error": f"Reticulum config not found at {config_path}"},
                    status=404,
                )
            with open(config_path) as f:
                content = f.read()
            return web.json_response(
                {
                    "content": content,
                    "path": config_path,
                },
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.put("/api/v1/reticulum/config/raw")
    async def reticulum_config_raw_put(request):
        """Persist new raw text to the Reticulum config file.

        The body must be JSON with a content string. Basic validation
        requires the [reticulum] and [interfaces] sections so we
        do not write a config that would prevent RNS from starting on the
        next reload.
        """
        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"error": "Invalid JSON body"},
                status=400,
            )

        content = data.get("content")
        if not isinstance(content, str):
            return web.json_response(
                {"error": "Missing or invalid 'content' field"},
                status=400,
            )

        if "[reticulum]" not in content or "[interfaces]" not in content:
            return web.json_response(
                {
                    "error": "Config must include [reticulum] and [interfaces] sections",
                },
                status=400,
            )

        try:
            config_dir = app._normalize_reticulum_config_dir(
                app.reticulum_config_dir,
            )
            if not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            config_path = app._reticulum_config_file_path()
            previous_interfaces = {}
            if os.path.isfile(config_path):
                try:
                    from RNS.vendor.configobj import ConfigObj

                    previous_interfaces = ConfigObj(config_path).get("interfaces") or {}
                except Exception:
                    previous_interfaces = {}
            i2p_raw_error = i2p_support.validate_raw_config_i2p_policy(
                content,
                previous_interfaces=previous_interfaces,
            )
            if i2p_raw_error is not None:
                return web.json_response(
                    {"error": i2p_raw_error},
                    status=422,
                )
            with open(config_path, "w") as f:
                f.write(content)
            i2p_support.guard_i2p_interfaces_in_config(config_path)
            return web.json_response(
                {
                    "message": "Reticulum config saved",
                    "path": config_path,
                },
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.post("/api/v1/reticulum/config/reset")
    async def reticulum_config_reset(request):
        """Restore the Reticulum config file to RNS stock defaults."""
        try:
            app.reticulum_config_dir = app._normalize_reticulum_config_dir(
                app.reticulum_config_dir,
            )
            config_path = app._reticulum_config_file_path()
            default_text = app._write_rns_reticulum_default_config_file(
                config_path,
            )
            return web.json_response(
                {
                    "message": "Reticulum config restored to defaults",
                    "content": default_text,
                    "path": config_path,
                },
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
