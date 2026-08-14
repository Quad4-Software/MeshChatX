# SPDX-License-Identifier: 0BSD
"""HTTP routes: interfaces."""

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

from meshchatx.src.backend.interface_enabled_flag import apply_interface_enabled_flag
from meshchatx.src.backend.serial_comports import list_serial_comports


def register_interfaces_routes(routes, app):

    # fetch com ports
    @routes.get("/api/v1/comports")
    async def comports(request):
        return web.json_response(
            {
                "comports": list_serial_comports(),
            },
        )

    @routes.get("/api/v1/system/network-interfaces")
    async def system_network_interfaces(request):
        interfaces, unavailable_reason = list_host_network_interfaces()
        payload = {
            "interfaces": interfaces,
            "unavailable_reason": unavailable_reason,
        }
        return web.json_response(payload)

    # fetch reticulum interfaces

    # fetch reticulum interfaces
    @routes.get("/api/v1/reticulum/interfaces")
    async def reticulum_interfaces(request):
        app._sync_interfaces_from_disk()
        interfaces = app._get_interfaces_snapshot()

        processed_interfaces = {}
        for interface_name, interface in interfaces.items():
            if not isinstance(interface, dict):
                continue
            try:
                interface_data = copy.deepcopy(interface)
            except Exception:
                interface_data = dict(interface)

            # handle sub-interfaces for RNodeMultiInterface
            if interface_data.get("type") == "RNodeMultiInterface":
                sub_interfaces = []
                for sub_name, sub_config in interface_data.items():
                    if sub_name not in {
                        "type",
                        "port",
                        "interface_enabled",
                        "selected_interface_mode",
                        "configured_bitrate",
                    }:
                        if isinstance(sub_config, dict):
                            sub_config["name"] = sub_name
                            sub_interfaces.append(sub_config)

                # add sub-interfaces to the main interface data
                interface_data["sub_interfaces"] = sub_interfaces

                for sub in sub_interfaces:
                    del interface_data[sub["name"]]

            processed_interfaces[interface_name] = interface_data

        return web.json_response(
            {
                "interfaces": processed_interfaces,
            },
        )

    @routes.post("/api/v1/reticulum/interfaces/bitrates")
    async def reticulum_interfaces_bitrates(request):
        """Set forced bitrate (bps) on named interfaces and optionally reload RNS."""
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"message": "Invalid JSON"}, status=400)
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON object"}, status=400)

        bitrates = data.get("bitrates")
        if not isinstance(bitrates, dict) or not bitrates:
            return web.json_response(
                {"message": "bitrates object is required"},
                status=422,
            )

        reload_stack = bool(data.get("reload", False))
        interfaces = app._get_interfaces_section()
        interfaces_before_write = app._get_interfaces_snapshot()
        updated = []
        missing = []
        for raw_name, raw_bps in bitrates.items():
            name = InterfaceEditor.sanitize_interface_section_name(str(raw_name))
            if not name or name not in interfaces:
                missing.append(str(raw_name))
                continue
            details = interfaces[name]
            if raw_bps is None or raw_bps == "":
                details.pop("bitrate", None)
            else:
                try:
                    bps = int(raw_bps)
                except (TypeError, ValueError):
                    return web.json_response(
                        {"message": f"Invalid bitrate for {name}"},
                        status=422,
                    )
                if bps < 0:
                    return web.json_response(
                        {"message": f"Bitrate must be >= 0 for {name}"},
                        status=422,
                    )
                details["bitrate"] = str(bps)
            updated.append(name)

        if not updated and missing:
            return web.json_response(
                {"message": "No matching interfaces", "missing": missing},
                status=404,
            )

        if updated and not app._write_reticulum_config(
            rollback_interfaces=interfaces_before_write,
        ):
            return web.json_response(
                {"message": "Failed to write Reticulum config"},
                status=500,
            )

        reloaded = False
        if reload_stack and updated:
            try:
                await app.reload_reticulum()
                reloaded = True
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Bitrates saved but RNS reload failed: {e}",
                        "updated": updated,
                        "missing": missing,
                        "reloaded": False,
                    },
                    status=500,
                )

        return web.json_response(
            {
                "message": "Interface bitrates updated",
                "updated": updated,
                "missing": missing,
                "reloaded": reloaded,
            },
        )

    # fetch community interfaces

    # enable reticulum interface
    @routes.post("/api/v1/reticulum/interfaces/enable")
    async def reticulum_interfaces_enable(request):
        # get request data
        data = await request.json()
        interface_name = data.get("name")

        if interface_name is None or interface_name == "":
            return web.json_response(
                {
                    "message": "Interface name is required",
                },
                status=422,
            )

        # enable interface
        app._sync_interfaces_from_disk()
        interfaces_before_write = app._get_interfaces_snapshot()
        interfaces = app._get_interfaces_section()
        if interface_name not in interfaces:
            return web.json_response(
                {
                    "message": "Interface not found",
                },
                status=404,
            )
        interface = interfaces[interface_name]
        i2p_error = i2p_support.validate_i2p_enable(
            interfaces,
            app._get_reticulum_section(),
            interface_name=interface_name,
        )
        if i2p_error is not None:
            return web.json_response({"message": i2p_error}, status=422)

        apply_interface_enabled_flag(interface, enabled=True)

        keys_to_remove = []
        for key, value in interface.items():
            if value is None:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del interface[key]

        # save config
        if not app._write_reticulum_config(
            rollback_interfaces=interfaces_before_write,
        ):
            return web.json_response(
                {
                    "message": "Failed to write Reticulum config",
                },
                status=500,
            )

        return web.json_response(
            {
                "message": "Interface is now enabled",
            },
        )

    # disable reticulum interface

    # disable reticulum interface
    @routes.post("/api/v1/reticulum/interfaces/disable")
    async def reticulum_interfaces_disable(request):
        # get request data
        data = await request.json()
        interface_name = data.get("name")

        if interface_name is None or interface_name == "":
            return web.json_response(
                {
                    "message": "Interface name is required",
                },
                status=422,
            )

        # disable interface
        app._sync_interfaces_from_disk()
        interfaces_before_write = app._get_interfaces_snapshot()
        interfaces = app._get_interfaces_section()
        if interface_name not in interfaces:
            return web.json_response(
                {
                    "message": "Interface not found",
                },
                status=404,
            )
        interface = interfaces[interface_name]
        apply_interface_enabled_flag(interface, enabled=False)

        keys_to_remove = []
        for key, value in interface.items():
            if value is None:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del interface[key]

        # save config
        if not app._write_reticulum_config(
            rollback_interfaces=interfaces_before_write,
        ):
            return web.json_response(
                {
                    "message": "Failed to write Reticulum config",
                },
                status=500,
            )

        return web.json_response(
            {
                "message": "Interface is now disabled",
            },
        )

    # delete reticulum interface

    # delete reticulum interface
    @routes.post("/api/v1/reticulum/interfaces/delete")
    async def reticulum_interfaces_delete(request):
        # get request data
        data = await request.json()
        interface_name = data.get("name")

        if interface_name is None or interface_name == "":
            return web.json_response(
                {
                    "message": "Interface name is required",
                },
                status=422,
            )

        app._sync_interfaces_from_disk()
        interfaces_before_write = app._get_interfaces_snapshot()
        interfaces = app._get_interfaces_section()
        if interface_name not in interfaces:
            return web.json_response(
                {
                    "message": "Interface not found",
                },
                status=404,
            )

        # delete interface
        del interfaces[interface_name]

        # save config
        if not app._write_reticulum_config(
            rollback_interfaces=interfaces_before_write,
        ):
            return web.json_response(
                {
                    "message": "Failed to write Reticulum config",
                },
                status=500,
            )

        return web.json_response(
            {
                "message": "Interface has been deleted",
            },
        )

    @routes.get("/api/v1/reticulum/interface-modules")
    async def reticulum_interface_modules_list(_request):
        from meshchatx.src.backend.interface_module_store import (
            list_interface_modules,
        )

        try:
            payload = list_interface_modules(app.reticulum_config_dir)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to list interface modules: {e!s}"},
                status=500,
            )
        return web.json_response(payload)

    @routes.post("/api/v1/reticulum/interface-modules")
    async def reticulum_interface_modules_install(request):
        from meshchatx.src.backend.interface_module_store import (
            install_interface_module,
        )

        try:
            content_type = request.headers.get("Content-Type", "")
            filename = None
            data = b""
            overwrite = False
            if "multipart/form-data" in content_type:
                reader = await request.multipart()
                field = await reader.next()
                while field is not None:
                    if field.name == "file":
                        filename = field.filename or filename
                        chunks = []
                        while True:
                            chunk = await field.read_chunk()
                            if not chunk:
                                break
                            chunks.append(chunk)
                        data = b"".join(chunks)
                    elif field.name == "overwrite":
                        overwrite = (await field.text()).strip().lower() in (
                            "1",
                            "true",
                            "yes",
                            "on",
                        )
                    elif field.name == "filename":
                        filename = (await field.text()).strip() or filename
                    field = await reader.next()
            else:
                body = await request.json()
                filename = body.get("filename") or body.get("type")
                raw = body.get("content") or body.get("data") or ""
                if isinstance(raw, str):
                    try:
                        data = base64.b64decode(raw, validate=False)
                    except (binascii.Error, ValueError):
                        data = raw.encode("utf-8")
                elif isinstance(raw, (bytes, bytearray)):
                    data = bytes(raw)
                overwrite = bool(body.get("overwrite", False))
            if not data:
                return web.json_response(
                    {"message": "Interface module file is required"},
                    status=400,
                )
            result = install_interface_module(
                app.reticulum_config_dir,
                filename=filename,
                data=data,
                overwrite=overwrite,
            )
            return web.json_response(
                {
                    "message": (
                        f"Installed {result['filename']}. "
                        "Reload Reticulum or restart MeshChatX to load it."
                    ),
                    **result,
                },
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=422)
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to install interface module: {e!s}"},
                status=500,
            )

    @routes.delete("/api/v1/reticulum/interface-modules/{type_name}")
    async def reticulum_interface_modules_delete(request):
        from meshchatx.src.backend.interface_module_store import (
            delete_interface_module,
        )

        type_name = request.match_info.get("type_name")
        try:
            result = delete_interface_module(app.reticulum_config_dir, type_name)
        except FileNotFoundError as e:
            return web.json_response({"message": str(e)}, status=404)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=422)
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to delete interface module: {e!s}"},
                status=500,
            )
        return web.json_response(
            {
                "message": f"Deleted {result['filename']}",
                **result,
            },
        )

    # add reticulum interface

    # add reticulum interface
    @routes.post("/api/v1/reticulum/interfaces/add")
    async def reticulum_interfaces_add(request):
        # get request data
        data = await request.json()
        interface_name = InterfaceEditor.sanitize_interface_section_name(
            data.get("name"),
        )
        interface_type = data.get("type")
        allow_overwriting_interface = data.get("allow_overwriting_interface", False)

        # ensure name is provided
        if interface_name is None or interface_name == "":
            return web.json_response(
                {
                    "message": "Name is required",
                },
                status=422,
            )

        # ensure type name provided
        if interface_type is None or interface_type == "":
            return web.json_response(
                {
                    "message": "Type is required",
                },
                status=422,
            )

        # get existing interfaces
        app._sync_interfaces_from_disk()
        interfaces = app._get_interfaces_section()

        # ensure name is not for an existing interface, to prevent overwriting
        if allow_overwriting_interface is False and interface_name in interfaces:
            return web.json_response(
                {
                    "message": "Name is already in use by another interface",
                },
                status=422,
            )

        i2p_error = i2p_support.validate_i2p_add_or_update(
            interfaces,
            app._get_reticulum_section(),
            interface_name=interface_name,
            interface_type=interface_type,
            updating_existing=bool(allow_overwriting_interface),
        )
        if i2p_error is not None:
            return web.json_response({"message": i2p_error}, status=422)

        # get existing interface details if available
        interface_details = {}
        if interface_name in interfaces:
            interface_details = interfaces[interface_name]

        # update interface details
        interface_details["type"] = interface_type

        if interface_type == "RNodeMultiInterface":
            # RNS has no Android-specific implementation of RNodeMultiInterface,
            # so it always crashes on Android regardless of transport.
            if _is_chaquopy_android():
                return web.json_response(
                    {
                        "message": (
                            "RNodeMultiInterface is not supported on Android "
                            "(Reticulum has no Android-specific implementation of it)."
                        ),
                    },
                    status=422,
                )

        elif interface_type == "RNodeInterface":
            # RNodeIPInterface always maps to an RNodeInterface with a tcp://
            # port, which needs no native Android modules and always works.
            from meshchatx.src.backend.rnode_support import (
                rnode_transport_supported,
            )

            probe_interface = {
                "port": data.get("port"),
                "allow_bluetooth": data.get("allow_bluetooth"),
            }
            if not rnode_transport_supported(
                probe_interface,
                is_android=_is_chaquopy_android(),
            ):
                if _is_chaquopy_android():
                    message = (
                        "This RNode connection type is not available on this device. "
                        "On Android, USB serial and classic Bluetooth need the bundled "
                        "USB host stack, and BLE needs the bundled able stack. "
                        "RNode over IP (TCP) is unaffected."
                    )
                else:
                    message = (
                        "This RNode connection type is not available on this device. "
                        "USB serial and classic Bluetooth need pyserial; BLE needs bleak. "
                        "RNode over IP (TCP) is unaffected."
                    )
                return web.json_response(
                    {"message": message},
                    status=422,
                )

        # if interface doesn't have enabled or interface_enabled setting already, enable it by default
        if (
            "enabled" not in interface_details
            and "interface_enabled" not in interface_details
        ):
            interface_details["interface_enabled"] = "true"

        # handle AutoInterface
        if interface_type == "AutoInterface":
            # validate scope value if provided
            discovery_scope_value = data.get("discovery_scope")
            if discovery_scope_value not in (None, ""):
                if str(discovery_scope_value).lower() not in {
                    "link",
                    "admin",
                    "site",
                    "organisation",
                    "global",
                }:
                    return web.json_response(
                        {
                            "message": (
                                "Discovery scope must be one of: link, admin, "
                                "site, organisation, global"
                            ),
                        },
                        status=422,
                    )

            multicast_address_type_value = data.get("multicast_address_type")
            if multicast_address_type_value not in (None, "") and str(
                multicast_address_type_value,
            ).lower() not in {"temporary", "permanent"}:
                return web.json_response(
                    {
                        "message": (
                            "Multicast address type must be either 'temporary' or 'permanent'"
                        ),
                    },
                    status=422,
                )

            # validate ports if provided and ensure they are not in use
            discovery_port_value = data.get("discovery_port")
            if discovery_port_value not in (None, "") and is_port_in_use(
                None,
                discovery_port_value,
                kind="udp",
            ):
                return web.json_response(
                    {
                        "message": describe_port_conflict(
                            None,
                            discovery_port_value,
                            kind="udp",
                            interface_name=interface_name,
                        ),
                    },
                    status=409,
                )
            data_port_value = data.get("data_port")
            if data_port_value not in (None, "") and is_port_in_use(
                None,
                data_port_value,
                kind="udp",
            ):
                return web.json_response(
                    {
                        "message": describe_port_conflict(
                            None,
                            data_port_value,
                            kind="udp",
                            interface_name=interface_name,
                        ),
                    },
                    status=409,
                )

            # set optional AutoInterface options
            InterfaceEditor.update_value(interface_details, data, "group_id")
            InterfaceEditor.update_value(
                interface_details,
                data,
                "multicast_address_type",
            )
            InterfaceEditor.update_value(interface_details, data, "devices")
            InterfaceEditor.update_value(interface_details, data, "ignored_devices")
            InterfaceEditor.update_value(interface_details, data, "discovery_scope")
            InterfaceEditor.update_value(interface_details, data, "discovery_port")
            InterfaceEditor.update_value(interface_details, data, "data_port")
            InterfaceEditor.update_value(
                interface_details,
                data,
                "configured_bitrate",
            )

        # handle TCPClientInterface
        if interface_type == "TCPClientInterface":
            # ensure target host provided
            interface_target_host = data.get("target_host")
            if interface_target_host is None or interface_target_host == "":
                return web.json_response(
                    {
                        "message": "Target Host is required",
                    },
                    status=422,
                )

            # ensure target port provided
            interface_target_port = data.get("target_port")
            if interface_target_port is None or interface_target_port == "":
                return web.json_response(
                    {
                        "message": "Target Port is required",
                    },
                    status=422,
                )

            # set required TCPClientInterface options
            interface_details["target_host"] = interface_target_host
            interface_details["target_port"] = interface_target_port

            # set optional TCPClientInterface options
            InterfaceEditor.update_value(interface_details, data, "kiss_framing")
            InterfaceEditor.update_value(interface_details, data, "i2p_tunneled")
            InterfaceEditor.update_value(
                interface_details,
                data,
                "connect_timeout",
            )
            InterfaceEditor.update_value(
                interface_details,
                data,
                "max_reconnect_tries",
            )
            fixed_mtu_error = InterfaceEditor.apply_fixed_mtu(
                interface_details,
                data,
            )
            if fixed_mtu_error is not None:
                return web.json_response(
                    {"message": fixed_mtu_error},
                    status=422,
                )

        if interface_type == "BackboneInterface":
            # BackboneInterface supports two distinct configurations:
            # - listener mode: bind to listen_ip/listen_port to accept peers
            # - connector mode: dial out to remote/target_port for a relay
            listen_port_value = data.get("listen_port")
            listen_ip_value = data.get("listen_ip")
            listen_device_value = data.get("device")
            if (listen_port_value not in (None, "")) and (
                listen_ip_value not in (None, "")
                or listen_device_value not in (None, "")
            ):
                if is_port_in_use(
                    listen_ip_value,
                    listen_port_value,
                    kind="tcp",
                ):
                    return web.json_response(
                        {
                            "message": describe_port_conflict(
                                listen_ip_value,
                                listen_port_value,
                                kind="tcp",
                                interface_name=interface_name,
                            ),
                        },
                        status=409,
                    )
                interface_details["listen_port"] = listen_port_value
                if listen_ip_value not in (None, ""):
                    interface_details["listen_ip"] = listen_ip_value
                InterfaceEditor.update_value(interface_details, data, "device")
                InterfaceEditor.update_value(
                    interface_details,
                    data,
                    "prefer_ipv6",
                )
                flap_error = InterfaceEditor.apply_backbone_fast_flapping(
                    interface_details,
                    data,
                )
                if flap_error is not None:
                    return web.json_response(
                        {
                            "message": flap_error,
                        },
                        status=422,
                    )
            else:
                remote = data.get("remote") or data.get("target_host")
                if remote is None or str(remote).strip() == "":
                    return web.json_response(
                        {
                            "message": "Remote host is required",
                        },
                        status=422,
                    )
                interface_target_port = data.get("target_port")
                if interface_target_port is None or interface_target_port == "":
                    return web.json_response(
                        {
                            "message": "Target Port is required",
                        },
                        status=422,
                    )
                interface_details["remote"] = str(remote).strip()
                interface_details["target_port"] = interface_target_port
                InterfaceEditor.update_value(
                    interface_details,
                    data,
                    "transport_identity",
                )

        # handle I2P interface
        if interface_type == "I2PInterface":
            connectable_value = data.get("connectable")
            if connectable_value is None or connectable_value == "":
                interface_details["connectable"] = "False"
            else:
                interface_details["connectable"] = (
                    "True"
                    if str(connectable_value).lower() in {"true", "yes", "1", "on", "y"}
                    else "False"
                )
            peers = data.get("peers")
            cleaned_peers: list[str] = []
            if isinstance(peers, list):
                cleaned_peers = [str(p).strip() for p in peers if str(p).strip()]
            elif peers is not None and str(peers).strip() != "":
                cleaned_peers = [
                    s.strip() for s in str(peers).replace(",", " ").split() if s.strip()
                ]
            if not cleaned_peers:
                return web.json_response(
                    {
                        "message": "At least one I2P peer is required",
                    },
                    status=422,
                )
            interface_details["peers"] = cleaned_peers

        # handle tcp server interface
        if interface_type == "TCPServerInterface":
            # ensure listen ip provided
            interface_listen_ip = data.get("listen_ip")
            if (
                interface_listen_ip is not None
                and str(interface_listen_ip).strip() != ""
            ):
                interface_listen_ip = str(interface_listen_ip).strip()
            else:
                interface_listen_ip = ""
            if interface_listen_ip == "":
                return web.json_response(
                    {
                        "message": "Listen IP is required",
                    },
                    status=422,
                )

            # ensure listen port provided
            interface_listen_port = data.get("listen_port")
            if interface_listen_port is None or interface_listen_port == "":
                return web.json_response(
                    {
                        "message": "Listen Port is required",
                    },
                    status=422,
                )

            # ensure listen port is not currently in use by another process
            if is_port_in_use(
                interface_listen_ip,
                interface_listen_port,
                kind="tcp",
            ):
                return web.json_response(
                    {
                        "message": describe_port_conflict(
                            interface_listen_ip,
                            interface_listen_port,
                            kind="tcp",
                            interface_name=interface_name,
                        ),
                    },
                    status=409,
                )

            # set required TCPServerInterface options
            interface_details["listen_ip"] = interface_listen_ip
            interface_details["listen_port"] = interface_listen_port

            # set optional TCPServerInterface options
            InterfaceEditor.update_value(interface_details, data, "device")
            InterfaceEditor.update_value(interface_details, data, "prefer_ipv6")
            InterfaceEditor.update_value(interface_details, data, "i2p_tunneled")

        # handle udp interface
        if interface_type == "UDPInterface":
            # ensure listen ip provided
            interface_listen_ip = data.get("listen_ip")
            if (
                interface_listen_ip is not None
                and str(interface_listen_ip).strip() != ""
            ):
                interface_listen_ip = str(interface_listen_ip).strip()
            else:
                interface_listen_ip = ""
            if interface_listen_ip == "":
                return web.json_response(
                    {
                        "message": "Listen IP is required",
                    },
                    status=422,
                )

            # ensure listen port provided
            interface_listen_port = data.get("listen_port")
            if interface_listen_port is None or interface_listen_port == "":
                return web.json_response(
                    {
                        "message": "Listen Port is required",
                    },
                    status=422,
                )

            # ensure forward ip provided
            interface_forward_ip = data.get("forward_ip")
            if interface_forward_ip is None or interface_forward_ip == "":
                return web.json_response(
                    {
                        "message": "Forward IP is required",
                    },
                    status=422,
                )

            # ensure forward port provided
            interface_forward_port = data.get("forward_port")
            if interface_forward_port is None or interface_forward_port == "":
                return web.json_response(
                    {
                        "message": "Forward Port is required",
                    },
                    status=422,
                )

            # ensure listen port is not currently in use by another process
            if is_port_in_use(
                interface_listen_ip,
                interface_listen_port,
                kind="udp",
            ):
                return web.json_response(
                    {
                        "message": describe_port_conflict(
                            interface_listen_ip,
                            interface_listen_port,
                            kind="udp",
                            interface_name=interface_name,
                        ),
                    },
                    status=409,
                )

            # set required UDPInterface options
            interface_details["listen_ip"] = interface_listen_ip
            interface_details["listen_port"] = interface_listen_port
            interface_details["forward_ip"] = interface_forward_ip
            interface_details["forward_port"] = interface_forward_port

            # set optional UDPInterface options
            InterfaceEditor.update_value(interface_details, data, "device")

        # handle RNodeInterface and RNodeIPInterface
        if interface_type in ("RNodeInterface", "RNodeIPInterface"):
            # map RNodeIPInterface to RNodeInterface for Reticulum config
            interface_details["type"] = "RNodeInterface"

            # ensure port provided
            interface_port = data.get("port")
            if interface_port is None or interface_port == "":
                return web.json_response(
                    {
                        "message": "Port is required",
                    },
                    status=422,
                )

            interface_tcp_host = None
            if str(interface_port).strip().lower().startswith("tcp://"):
                interface_port = InterfaceEditor.normalize_rnode_tcp_port(
                    str(interface_port),
                )
                host_part = str(interface_port)[len("tcp://") :].strip().strip(":")
                if not host_part:
                    return web.json_response(
                        {
                            "message": "TCP host is required for RNode over IP",
                        },
                        status=422,
                    )
                interface_tcp_host = host_part

            # ensure frequency provided
            interface_frequency = data.get("frequency")
            if interface_frequency is None or interface_frequency == "":
                return web.json_response(
                    {
                        "message": "Frequency is required",
                    },
                    status=422,
                )

            # ensure bandwidth provided
            interface_bandwidth = data.get("bandwidth")
            if interface_bandwidth is None or interface_bandwidth == "":
                return web.json_response(
                    {
                        "message": "Bandwidth is required",
                    },
                    status=422,
                )

            # ensure txpower provided and within Reticulum limits
            interface_txpower = data.get("txpower")
            txpower_error = InterfaceEditor.validate_rnode_txpower(
                interface_txpower,
            )
            if txpower_error is not None:
                return web.json_response(
                    {
                        "message": txpower_error,
                    },
                    status=422,
                )

            # ensure spreading factor provided
            interface_spreadingfactor = data.get("spreadingfactor")
            if interface_spreadingfactor is None or interface_spreadingfactor == "":
                return web.json_response(
                    {
                        "message": "Spreading Factor is required",
                    },
                    status=422,
                )

            # ensure coding rate provided
            interface_codingrate = data.get("codingrate")
            if interface_codingrate is None or interface_codingrate == "":
                return web.json_response(
                    {
                        "message": "Coding Rate is required",
                    },
                    status=422,
                )

            # set required RNodeInterface options
            interface_details["port"] = interface_port
            if interface_tcp_host is not None:
                # RNS's Android-specific RNodeInterface reads tcp_host as its
                # own config key instead of parsing it out of port like the
                # desktop implementation does, so both must be set for RNode
                # over IP to work on Android.
                interface_details["tcp_host"] = interface_tcp_host
            else:
                interface_details.pop("tcp_host", None)
            interface_details["frequency"] = InterfaceEditor.coerce_rnode_frequency_hz(
                interface_frequency,
            )
            interface_details["bandwidth"] = interface_bandwidth
            interface_details["txpower"] = InterfaceEditor.normalize_rnode_txpower(
                interface_txpower,
            )
            interface_details["spreadingfactor"] = interface_spreadingfactor
            interface_details["codingrate"] = interface_codingrate

            # set optional RNodeInterface options
            InterfaceEditor.update_value(interface_details, data, "callsign")
            InterfaceEditor.update_value(interface_details, data, "id_callsign")
            InterfaceEditor.update_value(interface_details, data, "id_interval")
            InterfaceEditor.update_value(interface_details, data, "flow_control")
            InterfaceEditor.update_value(
                interface_details,
                data,
                "airtime_limit_long",
            )
            InterfaceEditor.update_value(
                interface_details,
                data,
                "airtime_limit_short",
            )

        # handle RNodeMultiInterface
        if interface_type == "RNodeMultiInterface":
            # required settings
            interface_port = data.get("port")
            sub_interfaces = data.get("sub_interfaces", [])

            # ensure port provided
            if interface_port is None or interface_port == "":
                return web.json_response(
                    {
                        "message": "Port is required",
                    },
                    status=422,
                )

            # ensure sub interfaces provided
            if not isinstance(sub_interfaces, list) or not sub_interfaces:
                return web.json_response(
                    {
                        "message": "At least one sub-interface is required",
                    },
                    status=422,
                )

            # set required RNodeMultiInterface options
            interface_details["port"] = interface_port

            # remove any existing sub interfaces, which can be found by finding keys that contain a dict value
            # this allows us to replace all sub interfaces with the ones we are about to add, while also ensuring
            # that we do not remove any existing config values from the main interface config
            for key in list(interface_details.keys()):
                value = interface_details[key]
                if isinstance(value, dict):
                    del interface_details[key]

            # process each provided sub interface
            required_subinterface_fields = [
                "name",
                "frequency",
                "bandwidth",
                "txpower",
                "spreadingfactor",
                "codingrate",
                "vport",
            ]
            for idx, sub_interface in enumerate(sub_interfaces):
                # ensure required fields for sub-interface provided
                missing_fields = [
                    field
                    for field in required_subinterface_fields
                    if (
                        field not in sub_interface
                        or sub_interface.get(field) is None
                        or sub_interface.get(field) == ""
                    )
                ]
                if missing_fields:
                    return web.json_response(
                        {
                            "message": f"Sub-interface {idx + 1} is missing required field(s): {', '.join(missing_fields)}",
                        },
                        status=422,
                    )

                sub_txpower_error = InterfaceEditor.validate_rnode_txpower(
                    sub_interface.get("txpower"),
                )
                if sub_txpower_error is not None:
                    return web.json_response(
                        {
                            "message": f"Sub-interface {idx + 1}: {sub_txpower_error}",
                        },
                        status=422,
                    )

                sub_interface_name = sub_interface.get("name")
                interface_details[sub_interface_name] = {
                    "interface_enabled": "true",
                    "frequency": InterfaceEditor.coerce_rnode_frequency_hz(
                        sub_interface["frequency"],
                    ),
                    "bandwidth": int(sub_interface["bandwidth"]),
                    "txpower": InterfaceEditor.normalize_rnode_txpower(
                        sub_interface["txpower"],
                    ),
                    "spreadingfactor": int(sub_interface["spreadingfactor"]),
                    "codingrate": int(sub_interface["codingrate"]),
                    "vport": int(sub_interface["vport"]),
                }

            interfaces[interface_name] = interface_details

        # handle SerialInterface, KISSInterface, and AX25KISSInterface
        if interface_type in (
            "SerialInterface",
            "KISSInterface",
            "AX25KISSInterface",
        ):
            # ensure port provided
            interface_port = data.get("port")
            if interface_port is None or interface_port == "":
                return web.json_response(
                    {
                        "message": "Port is required",
                    },
                    status=422,
                )

            # set required options
            interface_details["port"] = interface_port

            # set optional options
            InterfaceEditor.update_value(interface_details, data, "speed")
            InterfaceEditor.update_value(interface_details, data, "databits")
            InterfaceEditor.update_value(interface_details, data, "parity")
            InterfaceEditor.update_value(interface_details, data, "stopbits")

            # Handle KISS and AX25KISS specific options
            if interface_type in ("KISSInterface", "AX25KISSInterface"):
                # set optional options
                InterfaceEditor.update_value(interface_details, data, "preamble")
                InterfaceEditor.update_value(interface_details, data, "txtail")
                InterfaceEditor.update_value(interface_details, data, "persistence")
                InterfaceEditor.update_value(interface_details, data, "slottime")
                InterfaceEditor.update_value(
                    interface_details,
                    data,
                    "flow_control",
                )
                InterfaceEditor.update_value(
                    interface_details,
                    data,
                    "id_callsign",
                )
                InterfaceEditor.update_value(interface_details, data, "id_interval")
                InterfaceEditor.update_value(interface_details, data, "callsign")
                InterfaceEditor.update_value(interface_details, data, "ssid")

        # RNode Airtime limits and station ID
        InterfaceEditor.update_value(interface_details, data, "callsign")
        InterfaceEditor.update_value(interface_details, data, "id_interval")
        InterfaceEditor.update_value(interface_details, data, "airtime_limit_long")
        InterfaceEditor.update_value(interface_details, data, "airtime_limit_short")

        # handle Pipe Interface
        if interface_type == "PipeInterface":
            # ensure command provided
            interface_command = data.get("command")
            if interface_command is None or interface_command == "":
                return web.json_response(
                    {
                        "message": "Command is required",
                    },
                    status=422,
                )

            # ensure command provided
            interface_respawn_delay = data.get("respawn_delay")
            if interface_respawn_delay is None or interface_respawn_delay == "":
                return web.json_response(
                    {
                        "message": "Respawn delay is required",
                    },
                    status=422,
                )

            # set required options
            interface_details["command"] = interface_command
            interface_details["respawn_delay"] = interface_respawn_delay

        # HTTP tunnel (vendored RNS-over-HTTP). Config mode is client|server,
        # which is distinct from Reticulum interface modes (full/gateway/...).
        if interface_type == "HTTPInterface":
            tunnel_mode = str(data.get("mode") or "").strip().lower()
            if tunnel_mode not in {"client", "server"}:
                return web.json_response(
                    {
                        "message": "HTTPInterface mode must be client or server",
                    },
                    status=422,
                )
            interface_details["mode"] = tunnel_mode

            http_version_raw = data.get("http_version")
            if http_version_raw not in (None, ""):
                try:
                    http_version = int(http_version_raw)
                except (TypeError, ValueError):
                    return web.json_response(
                        {"message": "http_version must be 1, 2, or 3"},
                        status=422,
                    )
                if http_version not in (1, 2, 3):
                    return web.json_response(
                        {"message": "http_version must be 1, 2, or 3"},
                        status=422,
                    )
                interface_details["http_version"] = http_version
            else:
                interface_details.pop("http_version", None)

            if tunnel_mode == "client":
                server_url = data.get("server_url")
                if server_url is None or str(server_url).strip() == "":
                    return web.json_response(
                        {
                            "message": "server_url is required for HTTPInterface client mode"
                        },
                        status=422,
                    )
                interface_details["server_url"] = str(server_url).strip()
                InterfaceEditor.update_value(interface_details, data, "poll_interval")
                for key in (
                    "listen_host",
                    "listen_port",
                    "check_user_agent",
                    "serve_html_page",
                    "html_file_path",
                    "tls_certfile",
                    "tls_keyfile",
                ):
                    interface_details.pop(key, None)
            else:
                listen_host = data.get("listen_host")
                if listen_host is None or str(listen_host).strip() == "":
                    listen_host = "0.0.0.0"
                listen_port = data.get("listen_port")
                if listen_port is None or listen_port == "":
                    return web.json_response(
                        {
                            "message": "listen_port is required for HTTPInterface server mode"
                        },
                        status=422,
                    )
                interface_details["listen_host"] = str(listen_host).strip()
                interface_details["listen_port"] = listen_port
                InterfaceEditor.update_value(
                    interface_details, data, "check_user_agent"
                )
                InterfaceEditor.update_value(interface_details, data, "serve_html_page")
                InterfaceEditor.update_value(interface_details, data, "html_file_path")
                InterfaceEditor.update_value(interface_details, data, "tls_certfile")
                InterfaceEditor.update_value(interface_details, data, "tls_keyfile")
                for key in ("server_url", "poll_interval"):
                    interface_details.pop(key, None)

            InterfaceEditor.update_value(interface_details, data, "mtu")
            InterfaceEditor.update_value(interface_details, data, "user_agent")
            InterfaceEditor.update_value(interface_details, data, "pool_connections")
            InterfaceEditor.update_value(interface_details, data, "pool_maxsize")
            InterfaceEditor.update_value(interface_details, data, "keepalive_timeout")
            InterfaceEditor.update_value(interface_details, data, "tls_verify")
            InterfaceEditor.update_value(interface_details, data, "tls_ca_certs")

        _builtin_interface_types = frozenset(
            {
                "AutoInterface",
                "TCPClientInterface",
                "BackboneInterface",
                "I2PInterface",
                "TCPServerInterface",
                "UDPInterface",
                "RNodeInterface",
                "RNodeIPInterface",
                "RNodeMultiInterface",
                "SerialInterface",
                "KISSInterface",
                "AX25KISSInterface",
                "PipeInterface",
                "HTTPInterface",
            },
        )
        if interface_type not in _builtin_interface_types:
            extra = data.get("extra_config")
            if extra is None:
                extra = {}
            if not isinstance(extra, dict):
                return web.json_response(
                    {
                        "message": "extra_config must be a JSON object",
                    },
                    status=422,
                )
            for key, value in extra.items():
                if key in {"name", "type", "allow_overwriting_interface"}:
                    continue
                if value is None or value == "":
                    interface_details.pop(key, None)
                else:
                    interface_details[key] = value

        # interface discovery options
        for discovery_key in (
            "discoverable",
            "discovery_name",
            "announce_interval",
            "reachable_on",
            "discovery_stamp_value",
            "discovery_encrypt",
            "publish_ifac",
            "latitude",
            "longitude",
            "height",
            "discovery_frequency",
            "discovery_bandwidth",
            "discovery_modulation",
        ):
            InterfaceEditor.update_value(interface_details, data, discovery_key)

        location_cmd_error = InterfaceEditor.apply_location_cmd(
            interface_details,
            data,
        )
        if location_cmd_error is not None:
            return web.json_response(
                {
                    "message": location_cmd_error,
                },
                status=422,
            )

        if interface_type == "TCPClientInterface" or (
            interface_type == "BackboneInterface"
            and str(interface_details.get("remote") or "").strip() != ""
        ):
            default_boot = bool(
                app.current_context.config.default_bootstrap_only.get()
                if app.current_context and app.current_context.config
                else False,
            )
            ReticulumMeshChat.apply_bootstrap_only_to_interface(
                interface_details,
                data,
                default_boot,
                updating_existing=allow_overwriting_interface,
            )

        # set common interface options
        InterfaceEditor.update_value(interface_details, data, "bitrate")
        if interface_type != "HTTPInterface":
            mode_error = InterfaceEditor.apply_interface_mode(interface_details, data)
            if mode_error is not None:
                return web.json_response(
                    {
                        "message": mode_error,
                    },
                    status=422,
                )
        recursive_prs_error = InterfaceEditor.apply_yes_no_option(
            interface_details,
            data,
            "recursive_prs",
        )
        if recursive_prs_error is not None:
            return web.json_response(
                {
                    "message": recursive_prs_error,
                },
                status=422,
            )
        announces_error = InterfaceEditor.apply_yes_no_option(
            interface_details,
            data,
            "announces_from_internal",
        )
        if announces_error is not None:
            return web.json_response(
                {
                    "message": announces_error,
                },
                status=422,
            )
        announces_to_error = InterfaceEditor.apply_yes_no_option(
            interface_details,
            data,
            "announces_to_internal",
        )
        if announces_to_error is not None:
            return web.json_response(
                {
                    "message": announces_to_error,
                },
                status=422,
            )
        gravity_error = InterfaceEditor.apply_positive_number(
            interface_details,
            data,
            "gravity",
            as_int=True,
            minimum=-10_000,
            maximum=10_000,
        )
        if gravity_error is not None:
            return web.json_response(
                {
                    "message": gravity_error,
                },
                status=422,
            )
        InterfaceEditor.update_value(interface_details, data, "network_name")
        InterfaceEditor.update_value(interface_details, data, "passphrase")
        InterfaceEditor.update_value(interface_details, data, "ifac_size")

        # merge new interface into existing interfaces
        interfaces_before_write = app._get_interfaces_snapshot()
        if interface_type == "I2PInterface":
            # I2P must be last: drop and reinsert so ConfigObj order is correct.
            interfaces.pop(interface_name, None)
            interfaces[interface_name] = interface_details
        else:
            interfaces[interface_name] = interface_details
        # save config
        if not app._write_reticulum_config(
            rollback_interfaces=interfaces_before_write,
        ):
            return web.json_response(
                {
                    "message": (
                        "Failed to write Reticulum config. "
                        "Interface names must not contain '[' or ']' "
                        "(ConfigObj section syntax)."
                    ),
                },
                status=500,
            )

        if allow_overwriting_interface:
            return web.json_response(
                {
                    "message": "Interface has been saved",
                },
            )
        if interface_type == "I2PInterface":
            return web.json_response(
                {
                    "message": (
                        "I2P interface has been added as the last interface. "
                        "Please restart MeshChat for these changes to take effect. "
                        "Do not add or reorder other interfaces afterward without "
                        "removing I2P first."
                    ),
                },
            )
        return web.json_response(
            {
                "message": "Interface has been added. Please restart MeshChat for these changes to take effect.",
            },
        )

    # export interfaces

    # export interfaces
    @routes.post("/api/v1/reticulum/interfaces/export")
    async def export_interfaces(request):
        try:
            # get request data
            selected_interface_names = None
            try:
                data = await request.json()
                selected_interface_names = data.get("selected_interface_names")
            except Exception as e:
                # request data was not json, but we don't care
                print(f"Request data was not JSON: {e}")

            # format interfaces for export
            output = []
            interfaces = app._get_interfaces_snapshot()
            for interface_name, interface in interfaces.items():
                # skip interface if not selected
                if (
                    selected_interface_names is not None
                    and selected_interface_names != ""
                ):
                    if interface_name not in selected_interface_names:
                        continue

                # add interface to output
                output.append(f"[[{interface_name}]]")
                for key, value in interface.items():
                    if not isinstance(value, dict):
                        output.append(f"    {key} = {value}")
                output.append("")

                # Handle sub-interfaces for RNodeMultiInterface
                if interface.get("type") == "RNodeMultiInterface":
                    for sub_name, sub_config in interface.items():
                        if sub_name in {"type", "port", "interface_enabled"}:
                            continue
                        if isinstance(sub_config, dict):
                            output.append(f"  [[[{sub_name}]]]")
                            for sub_key, sub_value in sub_config.items():
                                output.append(f"      {sub_key} = {sub_value}")
                            output.append("")

            return web.Response(
                text="\n".join(output),
                content_type="text/plain",
                headers={
                    "Content-Disposition": "attachment; filename=meshchat_interfaces",
                },
            )

        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to export interfaces: {e!s}",
                },
                status=500,
            )

    @routes.post("/api/v1/reticulum/interfaces/import-preview")
    async def import_interfaces_preview(request):
        try:
            # get request data
            data = await request.json()
            config = data.get("config")

            # parse interfaces from config
            interfaces = InterfaceConfigParser.parse(config)
            # I2P must not be imported from files, so hide it from the picker.
            interfaces = [
                iface
                for iface in interfaces
                if str(iface.get("type") or "").strip() != "I2PInterface"
            ]

            return web.json_response(
                {
                    "interfaces": interfaces,
                },
            )

        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to parse config file: {e!s}",
                },
                status=500,
            )

    # import interfaces from config

    # import interfaces from config
    @routes.post("/api/v1/reticulum/interfaces/import")
    async def import_interfaces(request):
        try:
            # get request data
            data = await request.json()
            config = data.get("config")
            selected_interface_names = data.get("selected_interface_names")

            # parse interfaces from config
            interfaces = InterfaceConfigParser.parse(config)

            # find selected interfaces
            selected_interfaces = [
                interface
                for interface in interfaces
                if interface["name"] in selected_interface_names
            ]

            # convert interfaces to object
            interface_config = {}
            for interface in selected_interfaces:
                # add interface and keys/values
                interface_name = InterfaceEditor.sanitize_interface_section_name(
                    interface.get("name"),
                )
                if not interface_name:
                    return web.json_response(
                        {
                            "message": "Imported interface is missing a valid name",
                        },
                        status=422,
                    )
                interface_config[interface_name] = {}
                for key, value in interface.items():
                    interface_config[interface_name][key] = value

                # unset name which isn't part of the config
                del interface_config[interface_name]["name"]

                # force imported interface to be enabled by default
                interface_config[interface_name]["interface_enabled"] = "true"

                # remove enabled config value in favour of interface_enabled
                if "enabled" in interface_config[interface_name]:
                    del interface_config[interface_name]["enabled"]

                iface_body = interface_config[interface_name]
                iface_type = iface_body.get("type")
                if iface_type == "I2PInterface" or i2p_support.is_i2p_interface(
                    iface_body,
                ):
                    return web.json_response(
                        {
                            "message": i2p_support.MSG_IMPORT_FORBIDDEN,
                        },
                        status=422,
                    )
                import_option_error = InterfaceEditor.sanitize_imported_rns_options(
                    iface_body
                )
                if import_option_error is not None:
                    return web.json_response(
                        {
                            "message": import_option_error,
                        },
                        status=422,
                    )
                if iface_type in ("RNodeInterface", "RNodeIPInterface"):
                    freq = iface_body.get("frequency")
                    if freq is not None and freq != "":
                        iface_body["frequency"] = (
                            InterfaceEditor.coerce_rnode_frequency_hz(freq)
                        )
                    txpower = iface_body.get("txpower")
                    if txpower is not None and txpower != "":
                        txpower_error = InterfaceEditor.validate_rnode_txpower(
                            txpower,
                        )
                        if txpower_error is not None:
                            return web.json_response(
                                {
                                    "message": (
                                        f'Interface "{interface_name}": {txpower_error}'
                                    ),
                                },
                                status=422,
                            )
                        iface_body["txpower"] = InterfaceEditor.normalize_rnode_txpower(
                            txpower
                        )
                elif iface_type == "RNodeMultiInterface":
                    for sub_key, sub in list(iface_body.items()):
                        if isinstance(sub, dict):
                            freq = sub.get("frequency")
                            if freq is not None and freq != "":
                                sub["frequency"] = (
                                    InterfaceEditor.coerce_rnode_frequency_hz(freq)
                                )
                            txpower = sub.get("txpower")
                            if txpower is not None and txpower != "":
                                txpower_error = InterfaceEditor.validate_rnode_txpower(
                                    txpower,
                                )
                                if txpower_error is not None:
                                    return web.json_response(
                                        {
                                            "message": (
                                                f'Interface "{interface_name}" '
                                                f'sub-interface "{sub_key}": '
                                                f"{txpower_error}"
                                            ),
                                        },
                                        status=422,
                                    )
                                sub["txpower"] = (
                                    InterfaceEditor.normalize_rnode_txpower(
                                        txpower,
                                    )
                                )

            # update reticulum config with new interfaces
            app._sync_interfaces_from_disk()
            interfaces_before_write = app._get_interfaces_snapshot()
            interfaces = app._get_interfaces_section()
            interfaces.update(interface_config)
            if not app._write_reticulum_config(
                rollback_interfaces=interfaces_before_write,
            ):
                return web.json_response(
                    {
                        "message": (
                            "Failed to write Reticulum config. "
                            "Interface names must not contain '[' or ']' "
                            "(ConfigObj section syntax)."
                        ),
                    },
                    status=500,
                )

            return web.json_response(
                {
                    "message": "Interfaces imported successfully",
                },
            )

        except Exception as e:
            return web.json_response(
                {
                    "message": f"Failed to import interfaces: {e!s}",
                },
                status=500,
            )

    # handle websocket clients

    # get interface stats
    @routes.get("/api/v1/interface-stats")
    async def interface_stats(request):
        return web.json_response(
            {
                "interface_stats": app._get_interface_stats_payload(),
            },
        )

    # get path table
