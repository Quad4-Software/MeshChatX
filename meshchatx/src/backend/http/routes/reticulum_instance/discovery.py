# SPDX-License-Identifier: 0BSD
"""HTTP routes: reticulum_instance discovery."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.reticulum_instance._names import *  # noqa: F403, F405


def register_reticulum_instance_discovery_routes(routes, app):

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
