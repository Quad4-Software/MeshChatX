# SPDX-License-Identifier: 0BSD

import contextlib
import time
from typing import Any

import RNS
from RNS.Discovery import InterfaceDiscovery

try:
    from RNS._version import __version__ as RNS_VERSION
except Exception:
    RNS_VERSION = None


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


def speed_str(num, suffix="bps"):
    units = ["", "k", "M", "G", "T", "P", "E", "Z"]
    last_unit = "Y"

    if suffix == "Bps":
        num /= 8
        units = ["", "K", "M", "G", "T", "P", "E", "Z"]
        last_unit = "Y"

    for unit in units:
        if abs(num) < 1000.0:
            return f"{num:3.2f} {unit}{suffix}"
        num /= 1000.0

    return f"{num:.2f} {last_unit}{suffix}"


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
    return f"{round(x):,}"


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


_HIDDEN_IFACE_PREFIXES = (
    "LocalInterface[",
    "TCPInterface[Client",
    "BackboneInterface[Client on",
    "AutoInterfacePeer[",
    "WeaveInterfacePeer[",
    "I2PInterfacePeer[Connected peer",
)


def _hex_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    text = str(value).strip()
    return text or None


def _pretty_duration(seconds: Any) -> str | None:
    if seconds is None:
        return None
    try:
        return RNS.prettytime(float(seconds))
    except Exception:
        return None


def _flow_share_percent(part: Any, total: Any) -> int | None:
    try:
        p = float(part)
        t = float(total)
    except (TypeError, ValueError):
        return None
    if t <= 0 or p <= 0:
        return None
    return int(min(100.0, (p / t) * 100.0))


def _format_count_pair(
    down: Any,
    up: Any,
    *,
    down_label: str = "↓",
    up_label: str = "↑",
) -> str | None:
    if down is None and up is None:
        return None
    down_text = fmt_packet_count(down) or "0"
    up_text = fmt_packet_count(up) or "0"
    return f"{down_label}{down_text} {up_label}{up_text}"


def _format_announce_rate_limits(ifstat: dict) -> str | None:
    art = ifstat.get("announce_rate_target")
    arp = ifstat.get("announce_rate_penalty")
    arg = ifstat.get("announce_rate_grace")
    parts: list[str] = []
    if art is not None:
        parts.append(f"t:{_pretty_duration(art)}")
    if arp is not None:
        parts.append(f"p:{_pretty_duration(arp)}")
    if arg is not None:
        parts.append(f"g:{arg}")
    return " ".join(parts) if parts else None


def _format_violations(ifstat: dict) -> str | None:
    protocol = ifstat.get("protocol_violations") or 0
    ifac = ifstat.get("ifac_violations") or 0
    if not protocol and not ifac:
        return None
    parts: list[str] = []
    if protocol:
        parts.append(f"{protocol} protocol")
    if ifac:
        parts.append(f"{ifac} IFAC")
    return ", ".join(parts)


def _format_traffic_totals(stats: dict) -> dict[str, Any] | None:
    payload: dict[str, Any] = {}
    if "rxb" in stats:
        payload["rx_bytes"] = stats["rxb"]
        payload["rx_bytes_str"] = size_str(stats["rxb"])
    if "txb" in stats:
        payload["tx_bytes"] = stats["txb"]
        payload["tx_bytes_str"] = size_str(stats["txb"])
    if "rxs" in stats:
        payload["rx_speed_str"] = speed_str(stats["rxs"])
    if "txs" in stats:
        payload["tx_speed_str"] = speed_str(stats["txs"])

    rxs = stats.get("rxs")
    txs = stats.get("txs")
    if rxs and txs:
        data_rx = _flow_share_percent(
            (stats.get("prxs") or 0) + (stats.get("arxs") or 0),
            rxs,
        )
        data_tx = _flow_share_percent(
            (stats.get("ptxs") or 0) + (stats.get("atxs") or 0),
            txs,
        )
        if data_rx is not None:
            payload["data_rx_pct"] = data_rx
        if data_tx is not None:
            payload["data_tx_pct"] = data_tx

    announce = _format_transport_flow_section(
        stats,
        rxb_key="arxb",
        txb_key="atxb",
        rxs_key="arxs",
        txs_key="atxs",
        rxf_key="arxf",
        txf_key="atxf",
        total_rxs=rxs,
        total_txs=txs,
    )
    if announce:
        payload["announces"] = announce

    path_requests = _format_transport_flow_section(
        stats,
        rxb_key="prxb",
        txb_key="ptxb",
        rxs_key="prxs",
        txs_key="ptxs",
        rxf_key="prxf",
        txf_key="ptxf",
        total_rxs=rxs,
        total_txs=txs,
    )
    if path_requests:
        payload["path_requests"] = path_requests

    return payload or None


def _format_transport_flow_section(
    stats: dict,
    *,
    rxb_key: str,
    txb_key: str,
    rxs_key: str,
    txs_key: str,
    rxf_key: str,
    txf_key: str,
    total_rxs: Any,
    total_txs: Any,
) -> dict[str, Any] | None:
    if rxb_key not in stats and txs_key not in stats:
        return None
    section: dict[str, Any] = {}
    if stats.get(rxb_key) is not None:
        section["rx_bytes_str"] = size_str(stats[rxb_key])
    if stats.get(txb_key) is not None:
        section["tx_bytes_str"] = size_str(stats[txb_key])
    if stats.get(rxs_key) is not None:
        section["rx_speed_str"] = speed_str(stats[rxs_key])
    if stats.get(txs_key) is not None:
        section["tx_speed_str"] = speed_str(stats[txs_key])
    rx_pct = _flow_share_percent(stats.get(rxs_key), total_rxs)
    tx_pct = _flow_share_percent(stats.get(txs_key), total_txs)
    if rx_pct is not None:
        section["rx_flow_pct"] = rx_pct
    if tx_pct is not None:
        section["tx_flow_pct"] = tx_pct
    if stats.get(rxf_key) is not None:
        section["rx_frequency"] = fmt_per_second(stats[rxf_key])
    if stats.get(txf_key) is not None:
        section["tx_frequency"] = fmt_per_second(stats[txf_key])
    return section or None


def _format_queue_stats(stats: dict) -> dict[str, Any] | None:
    keys = (
        "tqpressure",
        "dqpressure",
        "aqpressure",
        "pqpressure",
        "ilqpressure",
        "rxqt",
        "rxqd",
        "rxqa",
        "rxqp",
        "rxqil",
        "rxqtd",
        "rxqdd",
        "rxqad",
        "rxqpd",
        "rxqild",
    )
    if not any(key in stats for key in keys):
        return None

    def _pressure(value: Any) -> str | None:
        if value is None:
            return None
        try:
            return f"{round(float(value) * 100.0, 1)}%"
        except (TypeError, ValueError):
            return str(value)

    payload: dict[str, Any] = {}
    for key in keys:
        if key in stats and stats[key] is not None:
            payload[key] = stats[key]

    queues = [
        ("total", "tqpressure", "rxqt", "rxqtd"),
        ("data", "dqpressure", "rxqd", "rxqdd"),
        ("announce", "aqpressure", "rxqa", "rxqad"),
        ("path_request", "pqpressure", "rxqp", "rxqpd"),
        ("ingress_limiter", "ilqpressure", "rxqil", "rxqild"),
    ]
    formatted: list[dict[str, Any]] = []
    for name, pressure_key, packets_key, dropped_key in queues:
        entry: dict[str, Any] = {"name": name}
        pressure = _pressure(stats.get(pressure_key))
        if pressure is not None:
            entry["pressure"] = pressure
        if stats.get(packets_key) is not None:
            entry["packets"] = fmt_packet_count(stats[packets_key])
        if stats.get(dropped_key):
            entry["dropped"] = fmt_packet_count(stats[dropped_key])
        if len(entry) > 1:
            formatted.append(entry)
    if formatted:
        payload["queues"] = formatted
    return payload or None


def _iface_is_hidden(name: str, ifstat: dict, show_all: bool) -> bool:
    if show_all or not name:
        return False
    if name.startswith(_HIDDEN_IFACE_PREFIXES):
        return True
    return (
        name.startswith("I2PInterface[")
        and ifstat.get("i2p_connectable") is False
    )


def _set_if_present(target: dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        return
    target[key] = value


class RNStatusHandler:
    def __init__(self, reticulum_instance):
        self.reticulum = reticulum_instance

    def get_status(
        self,
        include_link_stats: bool = False,
        sorting: str | None = None,
        sort_reverse: bool = False,
        stats: dict | None = None,
        link_count: int | None = None,
        *,
        include_local_blackhole: bool = True,
        show_all: bool = False,
    ):
        if stats is None:
            active_link_count = None
            try:
                if include_link_stats and link_count is None:
                    link_count = self.reticulum.get_link_count()
                if include_link_stats:
                    active_link_count = self.reticulum.get_active_link_count()
            except Exception as e:
                print(f"Failed to get link count: {e}")

            try:
                stats = self.reticulum.get_interface_stats()
            except Exception as e:
                print(f"Failed to get interface stats: {e}")
                stats = None
        else:
            active_link_count = None

        if not isinstance(stats, dict):
            return {
                "interfaces": [],
                "link_count": link_count,
                "active_link_count": None,
                "rns_version": RNS_VERSION,
            }

        discovered_list: list = []
        with contextlib.suppress(Exception):
            discovered_list = InterfaceDiscovery(
                discover_interfaces=False,
            ).list_discovered_interfaces()

        blackhole_enabled = False
        blackhole_sources = []
        blackhole_count = 0
        if include_local_blackhole:
            with contextlib.suppress(Exception):
                blackhole_enabled = RNS.Reticulum.publish_blackhole_enabled()
                blackhole_sources = [s.hex() for s in RNS.Reticulum.blackhole_sources()]

                if self.reticulum and hasattr(
                    self.reticulum, "get_blackholed_identities"
                ):
                    blackhole_count = len(self.reticulum.get_blackholed_identities())

        interfaces = stats.get("interfaces", [])
        if not isinstance(interfaces, list):
            interfaces = []

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
            elif sorting == "arxc":
                interfaces.sort(
                    key=lambda i: i.get("arxc", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "atxc":
                interfaces.sort(
                    key=lambda i: i.get("atxc", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "prx":
                interfaces.sort(
                    key=lambda i: i.get("incoming_pr_frequency", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "ptx":
                interfaces.sort(
                    key=lambda i: i.get("outgoing_pr_frequency", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "prxc":
                interfaces.sort(
                    key=lambda i: i.get("prxc", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "ptxc":
                interfaces.sort(
                    key=lambda i: i.get("ptxc", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "pvs":
                interfaces.sort(
                    key=lambda i: i.get("protocol_violations", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "ivs":
                interfaces.sort(
                    key=lambda i: i.get("ifac_violations", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "flt":
                interfaces.sort(
                    key=lambda i: i.get("packet_filter_hits", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting in ("gravity", "g"):
                interfaces.sort(
                    key=lambda i: i.get("gravity", 0) or 0,
                    reverse=sort_reverse,
                )
            elif sorting == "held":
                interfaces.sort(
                    key=lambda i: i.get("held_announces", 0) or 0,
                    reverse=sort_reverse,
                )

        formatted_interfaces = []
        for ifstat in interfaces:
            if not isinstance(ifstat, dict):
                continue
            name = ifstat.get("name", "")
            if _iface_is_hidden(name, ifstat, show_all):
                continue
            formatted_interfaces.append(
                self._format_interface(ifstat, discovered_list),
            )

        transport_uptime = stats.get("transport_uptime")
        rss = stats.get("rss")
        totals = _format_traffic_totals(stats)
        queues = _format_queue_stats(stats)

        return {
            "interfaces": formatted_interfaces,
            "link_count": link_count,
            "active_link_count": active_link_count,
            "timestamp": time.time(),
            "rns_version": RNS_VERSION,
            "blackhole_enabled": blackhole_enabled,
            "blackhole_sources": blackhole_sources,
            "blackhole_count": blackhole_count,
            "transport_id": _hex_value(stats.get("transport_id")),
            "network_id": _hex_value(stats.get("network_id")),
            "probe_responder": _hex_value(stats.get("probe_responder")),
            "transport_uptime": transport_uptime,
            "transport_uptime_str": _pretty_duration(transport_uptime),
            "totals": totals,
            "queues": queues,
            "rss": rss,
            "rss_str": size_str(rss) if rss is not None else None,
        }

    def _format_interface(self, ifstat: dict, discovered_list: list) -> dict[str, Any]:
        name = ifstat.get("name", "")
        formatted_if: dict[str, Any] = {
            "name": name,
            "status": "Up" if ifstat.get("status") else "Down",
            "discovered": stat_name_matches_discovered(name, discovered_list),
        }
        _set_if_present(formatted_if, "short_name", ifstat.get("short_name"))
        _set_if_present(formatted_if, "type", ifstat.get("type"))
        _set_if_present(formatted_if, "hash", _hex_value(ifstat.get("hash")))

        gravity = ifstat.get("gravity")
        if gravity:
            formatted_if["gravity"] = gravity
            formatted_if["status"] = f"{formatted_if['status']}, gravity {gravity}"

        mode = ifstat.get("mode")
        iface_modes = RNS.Interfaces.Interface.Interface
        if mode == iface_modes.MODE_ACCESS_POINT:
            mode_label = "Access Point"
        elif mode == iface_modes.MODE_POINT_TO_POINT:
            mode_label = "Point-to-Point"
        elif mode == iface_modes.MODE_ROAMING:
            mode_label = "Roaming"
        elif mode == iface_modes.MODE_BOUNDARY:
            mode_label = "Boundary"
        elif mode == iface_modes.MODE_GATEWAY:
            mode_label = "Gateway"
        elif mode == iface_modes.MODE_INTERNAL:
            mode_label = "Internal"
        else:
            mode_label = "Full"
        if ifstat.get("announces_to_internal"):
            mode_label += " (a>i)"
        formatted_if["mode"] = mode_label

        if "bitrate" in ifstat and ifstat["bitrate"] is not None:
            formatted_if["bitrate"] = speed_str(ifstat["bitrate"])

        if "rxb" in ifstat:
            formatted_if["rx_bytes"] = ifstat["rxb"]
            formatted_if["rx_bytes_str"] = size_str(ifstat["rxb"])
        if "txb" in ifstat:
            formatted_if["tx_bytes"] = ifstat["txb"]
            formatted_if["tx_bytes_str"] = size_str(ifstat["txb"])
        if "rxs" in ifstat and ifstat["rxs"] is not None:
            formatted_if["rx_speed_str"] = speed_str(ifstat["rxs"])
        if "txs" in ifstat and ifstat["txs"] is not None:
            formatted_if["tx_speed_str"] = speed_str(ifstat["txs"])

        if "clients" in ifstat and ifstat["clients"] is not None:
            formatted_if["clients"] = ifstat["clients"]

        if "noise_floor" in ifstat and ifstat["noise_floor"] is not None:
            formatted_if["noise_floor"] = f"{ifstat['noise_floor']} dBm"

        if "interference" in ifstat and ifstat["interference"] is not None:
            formatted_if["interference"] = f"{ifstat['interference']} dBm"

        if ifstat.get("interference_last_dbm") is not None:
            ago = _pretty_duration(
                time.time() - float(ifstat["interference_last_ts"])
                if ifstat.get("interference_last_ts") is not None
                else None,
            )
            last = f"{ifstat['interference_last_dbm']} dBm"
            if ago:
                last = f"{last} {ago} ago"
            formatted_if["interference_last"] = last

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
        if "incoming_pr_frequency" in ifstat:
            formatted_if["incoming_pr_frequency"] = fmt_per_second(
                ifstat["incoming_pr_frequency"],
            )
        if "outgoing_pr_frequency" in ifstat:
            formatted_if["outgoing_pr_frequency"] = fmt_per_second(
                ifstat["outgoing_pr_frequency"],
            )
        if "held_announces" in ifstat:
            formatted_if["held_announces"] = fmt_packet_count(
                ifstat["held_announces"],
            )
        if ifstat.get("announce_queue"):
            formatted_if["announce_queue"] = fmt_packet_count(ifstat["announce_queue"])

        announce_totals = _format_count_pair(ifstat.get("arxc"), ifstat.get("atxc"))
        if announce_totals:
            formatted_if["announce_totals"] = announce_totals
        path_totals = _format_count_pair(ifstat.get("prxc"), ifstat.get("ptxc"))
        if path_totals:
            formatted_if["path_request_totals"] = path_totals

        if ifstat.get("arxb") is not None:
            formatted_if["announce_rx_bytes_str"] = size_str(ifstat["arxb"])
        if ifstat.get("atxb") is not None:
            formatted_if["announce_tx_bytes_str"] = size_str(ifstat["atxb"])
        if ifstat.get("prxb") is not None:
            formatted_if["path_rx_bytes_str"] = size_str(ifstat["prxb"])
        if ifstat.get("ptxb") is not None:
            formatted_if["path_tx_bytes_str"] = size_str(ifstat["ptxb"])

        rxs = ifstat.get("rxs")
        txs = ifstat.get("txs")
        announce_rx_pct = _flow_share_percent(ifstat.get("arxs"), rxs)
        announce_tx_pct = _flow_share_percent(ifstat.get("atxs"), txs)
        if announce_rx_pct is not None:
            formatted_if["announce_flow_rx_pct"] = announce_rx_pct
        if announce_tx_pct is not None:
            formatted_if["announce_flow_tx_pct"] = announce_tx_pct
        path_rx_pct = _flow_share_percent(ifstat.get("prxs"), rxs)
        path_tx_pct = _flow_share_percent(ifstat.get("ptxs"), txs)
        if path_rx_pct is not None:
            formatted_if["path_flow_rx_pct"] = path_rx_pct
        if path_tx_pct is not None:
            formatted_if["path_flow_tx_pct"] = path_tx_pct

        rate_limits = _format_announce_rate_limits(ifstat)
        if rate_limits:
            formatted_if["announce_rate_limits"] = rate_limits

        violations = _format_violations(ifstat)
        if violations:
            formatted_if["violations"] = violations
        if ifstat.get("packet_filter_hits"):
            formatted_if["filter_hits"] = fmt_packet_count(ifstat["packet_filter_hits"])

        if ifstat.get("ifac_netname") is not None:
            formatted_if["network_name"] = ifstat["ifac_netname"]

        if ifstat.get("ifac_signature") is not None and ifstat.get("ifac_size"):
            sig = ifstat["ifac_signature"]
            tail = _hex_value(sig[-5:] if isinstance(sig, (bytes, bytearray)) else sig)
            formatted_if["ifac_access"] = f"{int(ifstat['ifac_size']) * 8}-bit IFAC"
            if tail:
                formatted_if["ifac_signature_tail"] = tail

        if "i2p_connectable" in ifstat:
            formatted_if["i2p_connectable"] = bool(ifstat["i2p_connectable"])
        if "i2p_b32" in ifstat:
            formatted_if["i2p_b32"] = ifstat.get("i2p_b32")
        if ifstat.get("tunnelstate"):
            formatted_if["i2p_tunnel_state"] = ifstat["tunnelstate"]

        _set_if_present(formatted_if, "switch_id", ifstat.get("switch_id"))
        _set_if_present(formatted_if, "endpoint_id", ifstat.get("endpoint_id"))
        _set_if_present(formatted_if, "via_switch_id", ifstat.get("via_switch_id"))
        _set_if_present(
            formatted_if,
            "parent_interface",
            ifstat.get("parent_interface_name"),
        )
        _set_if_present(
            formatted_if,
            "autoconnect_source",
            ifstat.get("autoconnect_source"),
        )
        if ifstat.get("blocked_ips"):
            formatted_if["blocked_ips"] = ifstat["blocked_ips"]
        blocked_list = ifstat.get("blocked_ip_list")
        if isinstance(blocked_list, list) and blocked_list:
            formatted_if["blocked_ip_list"] = blocked_list

        if ifstat.get("burst_active") and ifstat.get("burst_activated") is not None:
            burst = _pretty_duration(
                time.time() - float(ifstat["burst_activated"]),
            )
            if ifstat.get("burst_count"):
                burst = f"on {ifstat['burst_count']} for {burst}"
            formatted_if["burst"] = burst
        if (
            ifstat.get("pr_burst_active")
            and ifstat.get("pr_burst_activated") is not None
        ):
            path_burst = _pretty_duration(
                time.time() - float(ifstat["pr_burst_activated"]),
            )
            if ifstat.get("pr_burst_count"):
                path_burst = f"on {ifstat['pr_burst_count']} for {path_burst}"
            formatted_if["path_burst"] = path_burst

        return formatted_if
