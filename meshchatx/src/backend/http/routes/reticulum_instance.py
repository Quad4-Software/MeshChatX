# SPDX-License-Identifier: 0BSD
"""HTTP routes: reticulum_instance."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from aiohttp import web
from RNS.Discovery import InterfaceDiscovery

from meshchatx.src.backend import i2p_support
from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_conflict,
    http_error,
    http_error_from_exception,
    http_not_found,
    http_payload_too_large,
    http_unexpected,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)
from meshchatx.src.backend.interface_editor import InterfaceEditor

logger = logging.getLogger(__name__)


def register_reticulum_instance_routes(routes, app):

    # get or update reticulum discovery configuration
    @routes.get(API_V1_PREFIX + "/reticulum/discovery")
    async def reticulum_discovery_get(request):
        # Lazy: ReticulumMeshChat lives in meshchatx.meshchat, which imports
        # the route table. Resolving at call time keeps
        # patch("meshchatx.meshchat.ReticulumMeshChat") effective.
        from meshchatx.meshchat import ReticulumMeshChat

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

    @routes.patch(API_V1_PREFIX + "/reticulum/discovery")
    async def reticulum_discovery_patch(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_bad_request("Invalid request body")

        reticulum_config = app._get_reticulum_section()

        # Lazy import: see reticulum_discovery_get.
        from meshchatx.meshchat import ReticulumMeshChat

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
                    return http_error(
                        422,
                        "autoconnect_interface_mode must be one of: "
                        "full, gateway, access_point, pointtopoint, "
                        "roaming, boundary, internal",
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
                    return http_error(
                        422,
                        "autoconnect_announces_to_internal must be "
                        "a boolean or yes/no value",
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
                return http_error(422, f"{gravity_key} must be an integer")
            if gravity < -10_000 or gravity > 10_000:
                return http_error(
                    422, f"{gravity_key} must be between -10000 and 10000"
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
            return http_unexpected("Failed to write Reticulum config")

        try:
            reloaded = await app.reload_reticulum()
            if reloaded is False:
                return http_unexpected(
                    "Discovery settings saved but RNS reload failed", reloaded=False
                )
        except Exception as e:
            logger.debug(f"Failed to reload RNS after discovery config update: {e}")
            return http_unexpected(
                "Discovery settings saved but RNS reload failed", reloaded=False
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

    def _collect_discovered_interfaces():
        # Lazy import: see reticulum_discovery_get.
        from meshchatx.meshchat import ReticulumMeshChat

        now = time.time()
        cache = getattr(app, "_discovered_interfaces_cache", None)
        if cache and now - cache["ts"] < 3.0:
            return cache["payload"]
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

            payload = {
                "interfaces": normalized_interfaces,
                "active": to_jsonable(active),
            }
            app._discovered_interfaces_cache = {"ts": now, "payload": payload}
            return payload
        except Exception as e:
            raise RuntimeError(f"Failed to load discovered interfaces: {e!s}") from e

    @routes.get(API_V1_PREFIX + "/reticulum/discovered-interfaces")
    async def reticulum_discovered_interfaces(request):
        try:
            payload = await asyncio.to_thread(_collect_discovered_interfaces)
            return web.json_response(payload)
        except Exception:
            return http_unexpected("Failed to load discovered interfaces")

    # enable transport mode

    # enable transport mode
    @routes.post(API_V1_PREFIX + "/reticulum/enable-transport")
    async def reticulum_enable_transport(request):
        # enable transport mode
        reticulum_config = app._get_reticulum_section()
        reticulum_config["enable_transport"] = True
        if not app._write_reticulum_config():
            return http_unexpected("Failed to write Reticulum config")

        if not await app.reload_reticulum():
            return http_unexpected(
                "Transport mode was enabled in config, but RNS reload failed."
            )

        return web.json_response(
            {
                "message": "Transport mode enabled and RNS restarted successfully.",
            },
        )

    # disable transport mode

    # disable transport mode
    @routes.post(API_V1_PREFIX + "/reticulum/disable-transport")
    async def reticulum_disable_transport(request):
        # disable transport mode
        reticulum_config = app._get_reticulum_section()
        reticulum_config["enable_transport"] = False
        i2p_support.disable_i2p_when_transport_off(
            app._get_interfaces_section(),
            reticulum_config,
        )
        if not app._write_reticulum_config():
            return http_unexpected("Failed to write Reticulum config")

        if not await app.reload_reticulum():
            return http_unexpected(
                "Transport mode was disabled in config, but RNS reload failed."
            )

        return web.json_response(
            {
                "message": "Transport mode disabled and RNS restarted successfully.",
            },
        )

    @routes.get(API_V1_PREFIX + "/reticulum/instance")
    async def reticulum_instance_get(request):
        """Shared-instance, RPC, and hop-obfuscation settings (Sideband parity)."""
        return web.json_response(
            {"instance": app._build_reticulum_instance_settings()},
        )

    @routes.patch(API_V1_PREFIX + "/reticulum/instance")
    async def reticulum_instance_patch(request):
        """Update [reticulum] shared-instance / hop-obfuscation options and reload."""
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_bad_request("Invalid request body")
        if not isinstance(data, dict):
            return http_bad_request("Invalid request body")

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
                    return http_bad_request(
                        "instance_name must be 1-64 characters without whitespace"
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
                    return http_bad_request(
                        "shared_instance_type must be 'tcp' or 'unix'"
                    )
                reticulum_config["shared_instance_type"] = cleaned_type
            changed = True

        if "remote_management_allowed" in data:
            try:
                allowed = app._parse_rns_hash_list(
                    data.get("remote_management_allowed"),
                )
            except ValueError as e:
                return http_bad_request(str(e))
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
            return http_unexpected("Failed to write Reticulum config")

        if not await app.reload_reticulum():
            return http_unexpected(
                "Instance settings were saved, but RNS reload failed.",
                instance=app._build_reticulum_instance_settings(),
            )

        return web.json_response(
            {
                "message": "Reticulum instance settings updated and RNS restarted.",
                "instance": app._build_reticulum_instance_settings(),
            },
        )

    @routes.get(API_V1_PREFIX + "/reticulum/management-identities")
    async def reticulum_management_identities_get(request):
        from meshchatx.src.backend.management_identities import (
            list_management_identities,
        )

        identities = list_management_identities(
            getattr(app, "reticulum_config_dir", None),
        )
        return web.json_response({"identities": identities})

    @routes.post(API_V1_PREFIX + "/reticulum/management-identities")
    async def reticulum_management_identities_post(request):
        from meshchatx.src.backend.management_identities import (
            create_management_identity,
        )

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_bad_request("Invalid request body")
        name = (data or {}).get("name")
        force = bool((data or {}).get("force", False))
        try:
            identity = create_management_identity(
                getattr(app, "reticulum_config_dir", None),
                name or "",
                force=force,
            )
        except FileExistsError as e:
            return http_conflict(str(e))
        except ValueError as e:
            return http_bad_request(str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        return web.json_response({"identity": identity})

    @routes.post(API_V1_PREFIX + "/reticulum/reload")
    async def reticulum_reload(request):
        success = await app.reload_reticulum()
        if success:
            return web.json_response({"message": "Reticulum reloaded successfully"})
        return http_unexpected("Failed to reload Reticulum")

    @routes.get(API_V1_PREFIX + "/reticulum/config/raw")
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
                return http_not_found(f"Reticulum config not found at {config_path}")
            with open(config_path) as f:
                content = f.read()
            return web.json_response(
                {
                    "content": content,
                    "path": config_path,
                },
            )
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    @routes.put(API_V1_PREFIX + "/reticulum/config/raw")
    async def reticulum_config_raw_put(request):
        """Persist new raw text to the Reticulum config file.

        The body must be JSON with a content string. Basic validation
        requires the [reticulum] and [interfaces] sections so we
        do not write a config that would prevent RNS from starting on the
        next reload.
        """
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_bad_request("Invalid JSON body")

        content = data.get("content")
        if not isinstance(content, str):
            return http_bad_request("Missing or invalid 'content' field")

        if "[reticulum]" not in content or "[interfaces]" not in content:
            return http_bad_request(
                "Config must include [reticulum] and [interfaces] sections"
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

                    raw_interfaces = ConfigObj(config_path).get("interfaces")
                    if isinstance(raw_interfaces, dict):
                        previous_interfaces = raw_interfaces
                except Exception:
                    previous_interfaces = {}
            i2p_raw_error = i2p_support.validate_raw_config_i2p_policy(
                content,
                previous_interfaces=previous_interfaces,
            )
            if i2p_raw_error is not None:
                return http_error(422, i2p_raw_error)
            with open(config_path, "w") as f:
                f.write(content)
            i2p_support.guard_i2p_interfaces_in_config(config_path)
            app._sync_interfaces_from_disk(replace=True)
            return web.json_response(
                {
                    "message": "Reticulum config saved",
                    "path": config_path,
                },
            )
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    @routes.post(API_V1_PREFIX + "/reticulum/config/reset")
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
            app._sync_interfaces_from_disk(replace=True)
            return web.json_response(
                {
                    "message": "Reticulum config restored to defaults",
                    "content": default_text,
                    "path": config_path,
                },
            )
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)
