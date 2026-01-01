import time
from typing import Any


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


class RNStatusHandler:
    def __init__(self, reticulum_instance):
        self.reticulum = reticulum_instance

    def get_status(self, include_link_stats: bool = False, sorting: str | None = None, sort_reverse: bool = False):
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

        interfaces = stats.get("interfaces", [])

        if sorting and isinstance(sorting, str):
            sorting = sorting.lower()
            if sorting in ("rate", "bitrate"):
                interfaces.sort(key=lambda i: i.get("bitrate", 0) or 0, reverse=sort_reverse)
            elif sorting == "rx":
                interfaces.sort(key=lambda i: i.get("rxb", 0) or 0, reverse=sort_reverse)
            elif sorting == "tx":
                interfaces.sort(key=lambda i: i.get("txb", 0) or 0, reverse=sort_reverse)
            elif sorting == "rxs":
                interfaces.sort(key=lambda i: i.get("rxs", 0) or 0, reverse=sort_reverse)
            elif sorting == "txs":
                interfaces.sort(key=lambda i: i.get("txs", 0) or 0, reverse=sort_reverse)
            elif sorting == "traffic":
                interfaces.sort(
                    key=lambda i: (i.get("rxb", 0) or 0) + (i.get("txb", 0) or 0),
                    reverse=sort_reverse,
                )
            elif sorting in ("announces", "announce"):
                interfaces.sort(
                    key=lambda i: (i.get("incoming_announce_frequency", 0) or 0)
                    + (i.get("outgoing_announce_frequency", 0) or 0),
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
                interfaces.sort(key=lambda i: i.get("held_announces", 0) or 0, reverse=sort_reverse)

        formatted_interfaces = []
        for ifstat in interfaces:
            name = ifstat.get("name", "")

            if name.startswith("LocalInterface[") or name.startswith("TCPInterface[Client") or name.startswith("BackboneInterface[Client on"):
                continue

            formatted_if: dict[str, Any] = {
                "name": name,
                "status": "Up" if ifstat.get("status") else "Down",
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
                formatted_if["rx_packets"] = ifstat["rxs"]
            if "txs" in ifstat:
                formatted_if["tx_packets"] = ifstat["txs"]

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
                    "short": ifstat["airtime_short"],
                    "long": ifstat["airtime_long"],
                }

            if "channel_load_short" in ifstat and "channel_load_long" in ifstat:
                formatted_if["channel_load"] = {
                    "short": ifstat["channel_load_short"],
                    "long": ifstat["channel_load_long"],
                }

            if "peers" in ifstat and ifstat["peers"] is not None:
                formatted_if["peers"] = ifstat["peers"]

            if "incoming_announce_frequency" in ifstat:
                formatted_if["incoming_announce_frequency"] = ifstat["incoming_announce_frequency"]
            if "outgoing_announce_frequency" in ifstat:
                formatted_if["outgoing_announce_frequency"] = ifstat["outgoing_announce_frequency"]
            if "held_announces" in ifstat:
                formatted_if["held_announces"] = ifstat["held_announces"]

            if "ifac_netname" in ifstat and ifstat["ifac_netname"] is not None:
                formatted_if["network_name"] = ifstat["ifac_netname"]

            formatted_interfaces.append(formatted_if)

        return {
            "interfaces": formatted_interfaces,
            "link_count": link_count,
            "timestamp": time.time(),
        }

