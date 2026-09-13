// SPDX-License-Identifier: 0BSD

import { t } from "../../../js/i18n.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { QUEUE_LABEL_KEYS } from "./constants.js";
import type {
    InterfaceStatRow,
    QueueDisplayRow,
    RNStatusInterface,
    RNStatusQueues,
    RNStatusResponse,
} from "./types.js";

/**
 * Format integer values with commas for display.
 */
export function formatInt(value: unknown): string {
    if (value === null || value === undefined || value === "") {
        return "";
    }
    const n = Number(value);
    if (Number.isNaN(n)) {
        return String(value);
    }
    return n.toLocaleString();
}

/**
 * Shorten hash to 8 characters with ellipsis.
 */
export function shortHash(hash: string | null | undefined): string {
    if (!hash || hash.length < 10) return hash || "";
    return `${hash.slice(0, 8)}...`;
}

/**
 * Copy text to clipboard and show toast feedback.
 */
export async function copyText(value: string | undefined): Promise<boolean> {
    if (!value) {
        return false;
    }
    try {
        await navigator.clipboard.writeText(value);
        ToastUtils.success(t("common.copied"));
        return true;
    } catch {
        ToastUtils.error(t("common.failed_to_copy"));
        return false;
    }
}

/**
 * Check whether the status payload contains any summary card data.
 */
export function hasStatusSummary(data: Partial<RNStatusResponse>): boolean {
    return Boolean(
        (data.link_count !== null && data.link_count !== undefined) ||
        data.transport_uptime_str ||
        data.totals ||
        (data.blackhole_enabled !== null && data.blackhole_enabled !== undefined) ||
        data.rns_version ||
        data.rss_str
    );
}

/**
 * Filter interfaces that have I2P attributes.
 */
export function filterI2pInterfaces(interfaces: RNStatusInterface[]): RNStatusInterface[] {
    return (interfaces || []).filter(
        (iface) => Boolean(iface.i2p_b32) || iface.i2p_connectable === true || iface.i2p_connectable === false
    );
}

/**
 * Extract queue display rows from queues status response.
 */
export function extractQueueRows(queues?: RNStatusQueues | null): QueueDisplayRow[] {
    const list = queues?.queues;
    if (!Array.isArray(list)) {
        return [];
    }
    return list.map((queue) => {
        const key = queue.name;
        const labelKey = QUEUE_LABEL_KEYS[key];
        const label = labelKey ? t(labelKey) : key;
        return {
            key,
            label,
            pressure: queue.pressure,
            packets: queue.packets,
            dropped: queue.dropped,
        };
    });
}

/**
 * Build key-label-value rows for an interface card.
 */
export function buildInterfaceStatRows(iface: RNStatusInterface): InterfaceStatRow[] {
    const rows: InterfaceStatRow[] = [];
    const add = (key: string, value: string | number | undefined | null) => {
        if (value === undefined || value === null || value === "") {
            return;
        }
        rows.push({ key, label: t(`rnstatus.${key}`), value });
    };

    add("mode", iface.mode);
    add("bitrate", iface.bitrate);
    add("rx_bytes", iface.rx_bytes_str);
    add("tx_bytes", iface.tx_bytes_str);
    add("rx_speed", iface.rx_speed_str);
    add("tx_speed", iface.tx_speed_str);
    if (iface.clients !== undefined && iface.clients !== null) {
        add("clients", formatInt(iface.clients));
    }
    if (iface.peers !== undefined && iface.peers !== null) {
        add("peers", `${formatInt(iface.peers)} ${t("rnstatus.peers_reachable")}`);
    }
    add("noise_floor", iface.noise_floor);
    add("interference", iface.interference);
    add("interference_last", iface.interference_last);
    add("cpu_load", iface.cpu_load);
    add("cpu_temp", iface.cpu_temp);
    add("memory_load", iface.mem_load);
    if (iface.battery_percent !== undefined && iface.battery_percent !== null) {
        const battery = `${formatInt(iface.battery_percent)}%`;
        add("battery", iface.battery_state ? `${battery} (${iface.battery_state})` : battery);
    }
    add("network", iface.network_name);
    if (iface.incoming_announce_frequency !== undefined && iface.incoming_announce_frequency !== null) {
        add("incoming_announces", `${iface.incoming_announce_frequency}/s`);
    }
    if (iface.outgoing_announce_frequency !== undefined && iface.outgoing_announce_frequency !== null) {
        add("outgoing_announces", `${iface.outgoing_announce_frequency}/s`);
    }
    if (iface.incoming_pr_frequency !== undefined && iface.incoming_pr_frequency !== null) {
        add("path_requests_in", `${iface.incoming_pr_frequency}/s`);
    }
    if (iface.outgoing_pr_frequency !== undefined && iface.outgoing_pr_frequency !== null) {
        add("path_requests_out", `${iface.outgoing_pr_frequency}/s`);
    }
    add("held_announces", iface.held_announces);
    add("announce_queue", iface.announce_queue);
    add("announce_totals", iface.announce_totals);
    add("path_request_totals", iface.path_request_totals);
    add("announce_rx_bytes", iface.announce_rx_bytes_str);
    add("announce_tx_bytes", iface.announce_tx_bytes_str);
    add("path_rx_bytes", iface.path_rx_bytes_str);
    add("path_tx_bytes", iface.path_tx_bytes_str);
    if (iface.announce_flow_rx_pct !== undefined && iface.announce_flow_rx_pct !== null) {
        add("announce_flow_rx", t("rnstatus.flow_share", { pct: iface.announce_flow_rx_pct }));
    }
    if (iface.announce_flow_tx_pct !== undefined && iface.announce_flow_tx_pct !== null) {
        add("announce_flow_tx", t("rnstatus.flow_share", { pct: iface.announce_flow_tx_pct }));
    }
    if (iface.path_flow_rx_pct !== undefined && iface.path_flow_rx_pct !== null) {
        add("path_flow_rx", t("rnstatus.flow_share", { pct: iface.path_flow_rx_pct }));
    }
    if (iface.path_flow_tx_pct !== undefined && iface.path_flow_tx_pct !== null) {
        add("path_flow_tx", t("rnstatus.flow_share", { pct: iface.path_flow_tx_pct }));
    }
    add("announce_rate_limits", iface.announce_rate_limits);
    add("violations", iface.violations);
    add("filter_hits", iface.filter_hits);
    if (Array.isArray(iface.blocked_ip_list) && iface.blocked_ip_list.length > 0) {
        add("blocked_ip_list", iface.blocked_ip_list.join(", "));
    }
    if (iface.airtime) {
        add("airtime", `${iface.airtime.short}% (15s), ${iface.airtime.long}% (1h)`);
    }
    if (iface.channel_load) {
        add("channel_load", `${iface.channel_load.short}% (15s), ${iface.channel_load.long}% (1h)`);
    }
    add("i2p_tunnel", iface.i2p_tunnel_state);
    add("switch_id", iface.switch_id);
    add("endpoint_id", iface.endpoint_id);
    add("via_switch", iface.via_switch_id);
    add("access_ifac", iface.ifac_access);
    add("parent_interface", iface.parent_interface);
    add("autoconnect_source", iface.autoconnect_source);
    add("blocked_ips", iface.blocked_ips);
    add("burst", iface.burst);
    add("path_burst", iface.path_burst);

    return rows;
}
