// SPDX-License-Identifier: 0BSD

/**
 * Pathfinder / stamp / signal helpers. Heavy RNS calls stay on the viewer shell via window.api.
 */

import { fromNow } from "../../../libs/datetime.js";

export type PeerPathSnapshot = {
    hops?: number | null;
    next_hop?: string | null;
    interface_name?: string | null;
    updated_at?: number | null;
};

export type PathClickInfo = {
    hops?: number | null;
    next_hop_interface?: string | null;
    interface_name?: string | null;
};

export type PathClickSnapshot = {
    path_stale?: boolean;
    path_unresponsive?: boolean;
};

export type StampInfoLike = {
    stamp_cost?: number | null;
    outbound_ticket_expiry?: number | null;
};

export type SignalMetricsLike = {
    quality?: number | null;
    rssi?: number | null;
    snr?: number | null;
};

export function emptyPeerPathSnapshot(): PeerPathSnapshot {
    return { hops: null, next_hop: null, interface_name: null, updated_at: null };
}

export function pathHopsLabel(snapshot: PeerPathSnapshot | null | undefined): string {
    if (snapshot?.hops == null) {
        return "";
    }
    return String(snapshot.hops);
}

function estimateStampSolveTime(stampCost: number): string {
    if (stampCost >= 24) return "several hours";
    if (stampCost >= 20) return "more than an hour";
    if (stampCost >= 18) return "~5 minutes";
    if (stampCost >= 17) return "a few minutes";
    if (stampCost >= 16) return "~1 minute";
    if (stampCost >= 13) return "~30 seconds";
    if (stampCost >= 9) return "~10 seconds";
    if (stampCost >= 1) return "a few seconds";
    return "0 seconds";
}

/**
 * Dialog body for stamp-info header click (Vue ConversationViewer parity).
 */
export function formatStampInfoAlert(stampInfo: StampInfoLike | null | undefined): string {
    const stampCost = Number(stampInfo?.stamp_cost ?? 0);
    let estimated = estimateStampSolveTime(stampCost);
    const ticketExpiry = stampInfo?.outbound_ticket_expiry;
    if (ticketExpiry != null) {
        estimated = `instant (ticket expires ${fromNow(Number(ticketExpiry) * 1000)})`;
    }
    return [
        "This peer has enabled stamp security.",
        "",
        "Your device must have a ticket, or solve an automated proof of work task each time you send them a message.",
        "",
        `Time per message: ${estimated}`,
    ].join("\n");
}

/**
 * Dialog body for signal-metrics header click.
 */
export function formatSignalMetricsAlert(
    signalMetrics: SignalMetricsLike | null | undefined,
    t: (key: string, values?: Record<string, unknown>) => string
): string {
    const quality = signalMetrics?.quality ?? "???";
    const rssi = signalMetrics?.rssi ?? "???";
    const snr = signalMetrics?.snr ?? "???";
    return [
        t("messages.signal_quality", { quality }),
        t("messages.rssi_val", { rssi }),
        t("messages.snr_val", { snr }),
    ].join("\n");
}

/**
 * Dialog body for path header click (hops + stale/unresponsive hints).
 */
export function formatPeerPathClickAlert(
    path: PathClickInfo | null | undefined,
    snapshot: PathClickSnapshot | null | undefined,
    t: (key: string, values?: Record<string, unknown>) => string
): string {
    const hops = Number(path?.hops ?? 0);
    const iface =
        path?.next_hop_interface ||
        path?.interface_name ||
        t("messages.path_hops_unknown_iface") ||
        "unknown interface";
    const hopWord = hops === 1 ? "hop" : "hops";
    const parts = [`${hops} ${hopWord} away via ${iface}`];
    if (snapshot?.path_stale) {
        parts.push(t("messages.path_stale_hint"));
    }
    if (snapshot?.path_unresponsive) {
        parts.push(t("messages.path_unresponsive_hint"));
    }
    return parts.join("\n\n");
}
