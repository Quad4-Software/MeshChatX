# SPDX-License-Identifier: 0BSD
"""HTTP routes: interfaces add."""

from __future__ import annotations

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_conflict,
    http_error,
    http_payload_too_large,
    http_unexpected,
)

# ruff: noqa: F405
from meshchatx.src.backend.http.routes.interfaces._names import *  # noqa: F403
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_interfaces_add_routes(routes, app):

    # add reticulum interface
    @routes.post(API_V1_PREFIX + "/reticulum/interfaces/add")
    async def reticulum_interfaces_add(request):
        # get request data
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        interface_name = InterfaceEditor.sanitize_interface_section_name(
            data.get("name"),
        )
        interface_type = data.get("type")
        allow_overwriting_interface = data.get("allow_overwriting_interface", False)

        # ensure name is provided
        if interface_name is None or interface_name == "":
            return http_error(422, "Name is required")

        # ensure type name provided
        if interface_type is None or interface_type == "":
            return http_error(422, "Type is required")

        # get existing interfaces
        app._sync_interfaces_from_disk()
        interfaces = app._get_interfaces_section()

        # ensure name is not for an existing interface, to prevent overwriting
        if allow_overwriting_interface is False and interface_name in interfaces:
            return http_error(422, "Name is already in use by another interface")

        i2p_error = i2p_support.validate_i2p_add_or_update(
            interfaces,
            app._get_reticulum_section(),
            interface_name=interface_name,
            interface_type=interface_type,
            updating_existing=bool(allow_overwriting_interface),
        )
        if i2p_error is not None:
            return http_error(422, i2p_error)

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
                return http_error(
                    422,
                    "RNodeMultiInterface is not supported on Android "
                    "(Reticulum has no Android-specific implementation of it).",
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
                        "Serial, classic Bluetooth, BLE, and TCP all need pyserial "
                        "installed; BLE additionally needs bleak."
                    )
                return http_error(422, message)

        elif interface_type == "AwareInterface":
            # WiFi Aware (NAN) only exists in the Android app via the
            # local-link Java bridge. Reject early on desktop, web, and
            # Android devices without Aware hardware so the config can
            # never reference an interface that cannot start.
            from meshchatx.src.backend import android_locallink

            if not android_locallink.is_available():
                return http_error(
                    422,
                    "WiFi Aware is only available in the Android app.",
                )
            aware_caps = android_locallink.probe_capabilities()
            if not aware_caps.get("supported") or not aware_caps.get("wifi_aware"):
                return http_error(
                    422,
                    "WiFi Aware is not supported on this device.",
                )
            if not aware_caps.get("wifi_aware_available"):
                return http_error(
                    422,
                    "WiFi Aware is currently unavailable. Check that WiFi is enabled.",
                )

            # mode is the Aware role (publish/subscribe), not a Reticulum
            # interface mode, so apply_interface_mode is skipped below.
            aware_role = str(data.get("mode") or "subscribe").strip().lower()
            if aware_role not in {"subscribe", "publish"}:
                return http_error(
                    422,
                    "AwareInterface mode must be subscribe or publish",
                )
            interface_details["mode"] = aware_role

            aware_peers = data.get("peers")
            if aware_peers not in (None, ""):
                try:
                    aware_peers = int(aware_peers)
                except (TypeError, ValueError):
                    aware_peers = -1
                if aware_peers < 1 or aware_peers > 8:
                    return http_error(
                        422,
                        "AwareInterface peers must be an integer from 1 to 8",
                    )
                interface_details["peers"] = aware_peers

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
                    return http_error(
                        422,
                        "Discovery scope must be one of: link, admin, "
                        "site, organisation, global",
                    )

            multicast_address_type_value = data.get("multicast_address_type")
            if multicast_address_type_value not in (None, "") and str(
                multicast_address_type_value,
            ).lower() not in {"temporary", "permanent"}:
                return http_error(
                    422,
                    "Multicast address type must be either 'temporary' or 'permanent'",
                )

            # validate ports if provided and ensure they are not in use
            discovery_port_value = data.get("discovery_port")
            if discovery_port_value not in (None, "") and is_port_in_use(
                None,
                discovery_port_value,
                kind="udp",
            ):
                return http_conflict(
                    describe_port_conflict(
                        None,
                        discovery_port_value,
                        kind="udp",
                        interface_name=interface_name,
                    )
                )
            data_port_value = data.get("data_port")
            if data_port_value not in (None, "") and is_port_in_use(
                None,
                data_port_value,
                kind="udp",
            ):
                return http_conflict(
                    describe_port_conflict(
                        None,
                        data_port_value,
                        kind="udp",
                        interface_name=interface_name,
                    )
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
                return http_error(422, "Target Host is required")

            # ensure target port provided
            interface_target_port = data.get("target_port")
            if interface_target_port is None or interface_target_port == "":
                return http_error(422, "Target Port is required")

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
                return http_error(422, fixed_mtu_error)

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
                    return http_conflict(
                        describe_port_conflict(
                            listen_ip_value,
                            listen_port_value,
                            kind="tcp",
                            interface_name=interface_name,
                        )
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
                    return http_error(422, flap_error)
            else:
                remote = data.get("remote") or data.get("target_host")
                if remote is None or str(remote).strip() == "":
                    return http_error(422, "Remote host is required")
                interface_target_port = data.get("target_port")
                if interface_target_port is None or interface_target_port == "":
                    return http_error(422, "Target Port is required")
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
                return http_error(422, "At least one I2P peer is required")
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
                return http_error(422, "Listen IP is required")

            # ensure listen port provided
            interface_listen_port = data.get("listen_port")
            if interface_listen_port is None or interface_listen_port == "":
                return http_error(422, "Listen Port is required")

            # ensure listen port is not currently in use by another process
            if is_port_in_use(
                interface_listen_ip,
                interface_listen_port,
                kind="tcp",
            ):
                return http_conflict(
                    describe_port_conflict(
                        interface_listen_ip,
                        interface_listen_port,
                        kind="tcp",
                        interface_name=interface_name,
                    )
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
                return http_error(422, "Listen IP is required")

            # ensure listen port provided
            interface_listen_port = data.get("listen_port")
            if interface_listen_port is None or interface_listen_port == "":
                return http_error(422, "Listen Port is required")

            # ensure forward ip provided
            interface_forward_ip = data.get("forward_ip")
            if interface_forward_ip is None or interface_forward_ip == "":
                return http_error(422, "Forward IP is required")

            # ensure forward port provided
            interface_forward_port = data.get("forward_port")
            if interface_forward_port is None or interface_forward_port == "":
                return http_error(422, "Forward Port is required")

            # ensure listen port is not currently in use by another process
            if is_port_in_use(
                interface_listen_ip,
                interface_listen_port,
                kind="udp",
            ):
                return http_conflict(
                    describe_port_conflict(
                        interface_listen_ip,
                        interface_listen_port,
                        kind="udp",
                        interface_name=interface_name,
                    )
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
                return http_error(422, "Port is required")

            interface_tcp_host = None
            if str(interface_port).strip().lower().startswith("tcp://"):
                interface_port = InterfaceEditor.normalize_rnode_tcp_port(
                    str(interface_port),
                )
                host_part = str(interface_port)[len("tcp://") :].strip().strip(":")
                if not host_part:
                    return http_error(422, "TCP host is required for RNode over IP")
                interface_tcp_host = host_part

            # ensure frequency provided
            interface_frequency = data.get("frequency")
            if interface_frequency is None or interface_frequency == "":
                return http_error(422, "Frequency is required")

            # ensure bandwidth provided
            interface_bandwidth = data.get("bandwidth")
            if interface_bandwidth is None or interface_bandwidth == "":
                return http_error(422, "Bandwidth is required")

            # ensure txpower provided and within Reticulum limits
            interface_txpower = data.get("txpower")
            txpower_error = InterfaceEditor.validate_rnode_txpower(
                interface_txpower,
            )
            if txpower_error is not None:
                return http_error(422, txpower_error)

            # ensure spreading factor provided
            interface_spreadingfactor = data.get("spreadingfactor")
            if interface_spreadingfactor is None or interface_spreadingfactor == "":
                return http_error(422, "Spreading Factor is required")

            # ensure coding rate provided
            interface_codingrate = data.get("codingrate")
            if interface_codingrate is None or interface_codingrate == "":
                return http_error(422, "Coding Rate is required")

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
                return http_error(422, "Port is required")

            # ensure sub interfaces provided
            if not isinstance(sub_interfaces, list) or not sub_interfaces:
                return http_error(422, "At least one sub-interface is required")

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
                    return http_error(
                        422,
                        f"Sub-interface {idx + 1} is missing required field(s): {', '.join(missing_fields)}",
                    )

                sub_txpower_error = InterfaceEditor.validate_rnode_txpower(
                    sub_interface.get("txpower"),
                )
                if sub_txpower_error is not None:
                    return http_error(
                        422, f"Sub-interface {idx + 1}: {sub_txpower_error}"
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
                return http_error(422, "Port is required")

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
                return http_error(422, "Command is required")

            # ensure command provided
            interface_respawn_delay = data.get("respawn_delay")
            if interface_respawn_delay is None or interface_respawn_delay == "":
                return http_error(422, "Respawn delay is required")

            # set required options
            interface_details["command"] = interface_command
            interface_details["respawn_delay"] = interface_respawn_delay

        # HTTP tunnel (vendored RNS-over-HTTP). Config mode is client|server,
        # which is distinct from Reticulum interface modes (full/gateway/...).
        if interface_type == "HTTPInterface":
            tunnel_mode = str(data.get("mode") or "").strip().lower()
            if tunnel_mode not in {"client", "server"}:
                return http_error(422, "HTTPInterface mode must be client or server")
            interface_details["mode"] = tunnel_mode

            http_version_raw = data.get("http_version")
            if http_version_raw not in (None, ""):
                try:
                    http_version = int(http_version_raw)
                except (TypeError, ValueError):
                    return http_error(422, "http_version must be 1, 2, or 3")
                if http_version not in (1, 2, 3):
                    return http_error(422, "http_version must be 1, 2, or 3")
                interface_details["http_version"] = http_version
            else:
                interface_details.pop("http_version", None)

            if tunnel_mode == "client":
                server_url = data.get("server_url")
                if server_url is None or str(server_url).strip() == "":
                    return http_error(
                        422, "server_url is required for HTTPInterface client mode"
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
                    listen_host = "127.0.0.1"
                listen_port = data.get("listen_port")
                if listen_port is None or listen_port == "":
                    return http_error(
                        422, "listen_port is required for HTTPInterface server mode"
                    )
                interface_details["listen_host"] = str(listen_host).strip()
                interface_details["listen_port"] = listen_port
                InterfaceEditor.update_value(
                    interface_details,
                    data,
                    "check_user_agent",
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
                "AwareInterface",
            },
        )
        if interface_type not in _builtin_interface_types:
            extra = data.get("extra_config")
            if extra is None:
                extra = {}
            if not isinstance(extra, dict):
                return http_error(422, "extra_config must be a JSON object")
            for key, value in extra.items():
                if key in InterfaceEditor.UI_METADATA_KEYS | {
                    "type",
                    "allow_overwriting_interface",
                }:
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
            return http_error(422, location_cmd_error)

        if interface_type == "TCPClientInterface" or (
            interface_type == "BackboneInterface"
            and str(interface_details.get("remote") or "").strip() != ""
        ):
            default_boot = bool(
                app.current_context.config.default_bootstrap_only.get()
                if app.current_context and app.current_context.config
                else False,
            )
            # Lazy: ReticulumMeshChat lives in meshchatx.meshchat, which
            # imports the route table. Resolving here also keeps
            # patch("meshchatx.meshchat.ReticulumMeshChat") effective.
            from meshchatx.meshchat import ReticulumMeshChat

            ReticulumMeshChat.apply_bootstrap_only_to_interface(
                interface_details,
                data,
                default_boot,
                updating_existing=allow_overwriting_interface,
            )

        # set common interface options
        InterfaceEditor.update_value(interface_details, data, "bitrate")
        if interface_type not in ("HTTPInterface", "AwareInterface"):
            mode_error = InterfaceEditor.apply_interface_mode(interface_details, data)
            if mode_error is not None:
                return http_error(422, mode_error)
        recursive_prs_error = InterfaceEditor.apply_yes_no_option(
            interface_details,
            data,
            "recursive_prs",
        )
        if recursive_prs_error is not None:
            return http_error(422, recursive_prs_error)
        announces_error = InterfaceEditor.apply_yes_no_option(
            interface_details,
            data,
            "announces_from_internal",
        )
        if announces_error is not None:
            return http_error(422, announces_error)
        announces_to_error = InterfaceEditor.apply_yes_no_option(
            interface_details,
            data,
            "announces_to_internal",
        )
        if announces_to_error is not None:
            return http_error(422, announces_to_error)
        gravity_error = InterfaceEditor.apply_positive_number(
            interface_details,
            data,
            "gravity",
            as_int=True,
            minimum=-10_000,
            maximum=10_000,
        )
        if gravity_error is not None:
            return http_error(422, gravity_error)
        InterfaceEditor.update_value(interface_details, data, "network_name")
        InterfaceEditor.update_value(interface_details, data, "passphrase")
        InterfaceEditor.update_value(interface_details, data, "ifac_size")

        # merge new interface into existing interfaces
        InterfaceEditor.strip_ui_metadata(interface_details)
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
            return http_unexpected(
                "Failed to write Reticulum config. "
                "Interface names must not contain '[' or ']' "
                "(ConfigObj section syntax)."
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
