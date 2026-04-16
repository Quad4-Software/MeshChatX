# SPDX-License-Identifier: 0BSD

import contextlib
import time
from typing import Any

import RNS
from RNS.Discovery import InterfaceDiscovery


def size_str(num, suffix="B"):
    units = ["", "K", "M", "G", "T", "P", "E", "Z"]
    last_unit = "Y"

    if suffix == "b":
        num *= 8
        units = ["", "K", "M", "G", "T", "P", "E", "Z"]
        last_unit = "Y"

    for unit in units:
        if abs(num) < 1000.0:
            if unit == "":
                return f"{num:.0f} {unit}{suffix}"
            return f"{num:.2f} {unit}{suffix}"
        num /= 1000.0

    return f"{num:.2f}{last_unit}{suffix}"


def fmt_per_second(value: Any) -> str | None:
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return str(value)
    ax = abs(x)
    if ax == 0:
        return "0"
    if ax >= 100:
        return f"{x:.1f}"
    if ax >= 1:
        return f"{x:.2f}"
    return f"{x:.3g}"


def fmt_packet_count(value: Any) -> str | None:
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{int(round(x)):,}"


def fmt_percentage(value: Any) -> str | None:
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return str(value)
    ax = abs(x)
    if ax >= 100:
        return f"{x:.1f}"
    if ax >= 10:
        return f"{x:.2f}"
    return f"{x:.3g}"


def stat_name_matches_discovered(stat_name: str, discovered_list: list) -> bool:
    if not stat_name or not discovered_list:
        return False
    for d in discovered_list:
        if not isinstance(d, dict):
            continue
        ro = d.get("reachable_on")
        if ro and str(ro) in stat_name:
            return True
        dn = d.get("name")
        if dn and str(dn) and str(dn) in stat_name:
            return True
    return False


class RNStatusHandler:
    def __init__(self, reticulum_instance):
        self.reticulum = reticulum_instance

    def get_status(
        self,
        include_link_stats: bool = False,
        sorting: str | None = None,
        sort_reverse: bool = False,
    ):
        stats = None
        link_count = None

        try:
            if include_link_stats:
                link_count = self.reticulum.get_link_count()
        except Exception as e:
            # We can't do much here if the reticulum instance fails
            print(f"Failed to get link count: {e}")

        try:
            stats = self.reticulum.get_interface_stats()
        except Exception as e:
            # We can't do much here if the reticulum instance fails
            print(f"Failed to get interface stats: {e}")

        if stats is None:
            return {
                "interfaces": [],
                "link_count": link_count,
            }

        discovered_list: list = []
        with contextlib.suppress(Exception):
            discovered_list = InterfaceDiscovery(
                discover_interfaces=False,
            ).list_discovered_interfaces()

        blackhole_enabled = False
        blackhole_sources = []
        blackhole_count = 0
        with contextlib.suppress(Exception):
            blackhole_enabled = RNS.Reticulum.publish_blackhole_enabled()
            blackhole_sources = [s.hex() for s in RNS.Reticulum.blackhole_sources()]

            # Get count of blackholed identities
            if self.reticulum and hasattr(self.reticulum, "get_blackholed_identities"):
                blackhole_count = len(self.reticulum.get_blackholed_identities())

        interfaces = stats.get("interfaces", [])

        if sorting and isinstance(sorting, str):
            sorting = sorting.lower()
            if sorting in ("rate", "bitrate"):
                interfaces.sort(
                    key=lambda i: i.get("bitrate", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "rx":
                interfaces.sort(
                    key=lambda i: i.get("rxb", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "tx":
                interfaces.sort(
                    key=lambda i: i.get("txb", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "rxs":
                interfaces.sort(
                    key=lambda i: i.get("rxs", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "txs":
                interfaces.sort(
                    key=lambda i: i.get("txs", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "traffic":
                interfaces.sort(
                    key=lambda i: (i.get("rxb", 0) or 0) + (i.get("txb", 0) or 0),
                    reverse=sort_reverse,
                )
            elif sorting in ("announces", "announce"):
                interfaces.sort(
                    key=lambda i: (
                        (i.get("incoming_announce_frequency", 0) or 0)
                        + (i.get("outgoing_announce_frequency", 0) or 0)
                    ),
                    reverse=sort_reverse,
                )
            elif sorting == "arx":
                interfaces.sort(
                    key=lambda i: i.get("incoming_announce_frequency", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "atx":
                interfaces.sort(
                    key=lambda i: i.get("outgoing_announce_frequency", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "held":
                interfaces.sort(
                    key=lambda i: i.get("held_announces", 0) or 0,
                    reverse=sort_reverse,
                )

        formatted_interfaces = []
        for ifstat in interfaces:
            name = ifstat.get("name", "")

            if (
                name.startswith("LocalInterface[")
                or name.startswith("TCPInterface[Client")
                or name.startswith("BackboneInterface[Client on")
            ):
                continue

            formatted_if: dict[str, Any] = {
                "name": name,
                "status": "Up" if ifstat.get("status") else "Down",
                "discovered": stat_name_matches_discovered(name, discovered_list),
            }

            mode = ifstat.get("mode")
            if mode == 1:
                formatted_if["mode"] = "Access Point"
            elif mode == 2:
                formatted_if["mode"] = "Point-to-Point"
            elif mode == 3:
                formatted_if["mode"] = "Roaming"
            elif mode == 4:
                formatted_if["mode"] = "Boundary"
            elif mode == 5:
                formatted_if["mode"] = "Gateway"
            else:
                formatted_if["mode"] = "Full"

            if "bitrate" in ifstat and ifstat["bitrate"] is not None:
                formatted_if["bitrate"] = size_str(ifstat["bitrate"], "b") + "ps"

            if "rxb" in ifstat:
                formatted_if["rx_bytes"] = ifstat["rxb"]
                formatted_if["rx_bytes_str"] = size_str(ifstat["rxb"])
            if "txb" in ifstat:
                formatted_if["tx_bytes"] = ifstat["txb"]
                formatted_if["tx_bytes_str"] = size_str(ifstat["txb"])
            if "rxs" in ifstat:
                formatted_if["rx_packets"] = fmt_packet_count(ifstat["rxs"])
            if "txs" in ifstat:
                formatted_if["tx_packets"] = fmt_packet_count(ifstat["txs"])

            if "clients" in ifstat and ifstat["clients"] is not None:
                formatted_if["clients"] = ifstat["clients"]

            if "noise_floor" in ifstat and ifstat["noise_floor"] is not None:
                formatted_if["noise_floor"] = f"{ifstat['noise_floor']} dBm"

            if "interference" in ifstat and ifstat["interference"] is not None:
                formatted_if["interference"] = f"{ifstat['interference']} dBm"

            if "cpu_load" in ifstat and ifstat["cpu_load"] is not None:
                formatted_if["cpu_load"] = f"{ifstat['cpu_load']}%"

            if "cpu_temp" in ifstat and ifstat["cpu_temp"] is not None:
                formatted_if["cpu_temp"] = f"{ifstat['cpu_temp']}°C"

            if "mem_load" in ifstat and ifstat["mem_load"] is not None:
                formatted_if["mem_load"] = f"{ifstat['mem_load']}%"

            if "battery_percent" in ifstat and ifstat["battery_percent"] is not None:
                formatted_if["battery_percent"] = ifstat["battery_percent"]
                if "battery_state" in ifstat:
                    formatted_if["battery_state"] = ifstat["battery_state"]

            if "airtime_short" in ifstat and "airtime_long" in ifstat:
                formatted_if["airtime"] = {
                    "short": fmt_percentage(ifstat["airtime_short"]),
                    "long": fmt_percentage(ifstat["airtime_long"]),
                }

            if "channel_load_short" in ifstat and "channel_load_long" in ifstat:
                formatted_if["channel_load"] = {
                    "short": fmt_percentage(ifstat["channel_load_short"]),
                    "long": fmt_percentage(ifstat["channel_load_long"]),
                }

            if "peers" in ifstat and ifstat["peers"] is not None:
                formatted_if["peers"] = ifstat["peers"]

            if "incoming_announce_frequency" in ifstat:
                formatted_if["incoming_announce_frequency"] = fmt_per_second(
                    ifstat["incoming_announce_frequency"],
                )
            if "outgoing_announce_frequency" in ifstat:
                formatted_if["outgoing_announce_frequency"] = fmt_per_second(
                    ifstat["outgoing_announce_frequency"],
                )
            if "held_announces" in ifstat:
                formatted_if["held_announces"] = fmt_packet_count(
                    ifstat["held_announces"],
                )

            if "ifac_netname" in ifstat and ifstat["ifac_netname"] is not None:
                formatted_if["network_name"] = ifstat["ifac_netname"]

            formatted_interfaces.append(formatted_if)

        return {
            "interfaces": formatted_interfaces,
            "link_count": link_count,
            "timestamp": time.time(),
            "blackhole_enabled": blackhole_enabled,
            "blackhole_sources": blackhole_sources,
            "blackhole_count": blackhole_count,
        }
