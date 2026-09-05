# SPDX-License-Identifier: 0BSD
"""HTTP routes: interfaces crud."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.interfaces._names import *  # noqa: F403, F405


def register_interfaces_crud_routes(routes, app):

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
