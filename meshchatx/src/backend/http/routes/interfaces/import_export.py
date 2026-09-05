# SPDX-License-Identifier: 0BSD
"""HTTP routes: interfaces import_export."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.interfaces._names import *  # noqa: F403, F405


def register_interfaces_import_export_routes(routes, app):

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
                    iface_body,
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
                            txpower,
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
