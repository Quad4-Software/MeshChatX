// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";
import { t } from "../../../js/i18n.js";
import type { NodePathInfo, PropagationNodeStats } from "./types.js";

/**
 * Convert bytes to megabytes with 3-decimal precision.
 */
export function bytesToMb(value: number | string | undefined | null): number {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) {
        return 0;
    }
    return Math.max(0.001, Math.round((n / 1000000) * 1000) / 1000);
}

/**
 * Convert megabytes to bytes.
 */
export function mbToBytes(value: number | string | undefined | null): number {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) {
        return 1000;
    }
    return Math.max(1000, Math.round(n * 1000000));
}

/**
 * Format raw byte size into human readable string.
 */
export function formatByteSize(bytes: number | string | undefined | null): string {
    const value = Number(bytes);
    if (!Number.isFinite(value) || value < 0) return "0 B";
    if (value < 1000) return `${Math.round(value)} B`;
    if (value < 1000 * 1000) return `${(value / 1000).toFixed(1)} KB`;
    if (value < 1000 * 1000 * 1000) return `${(value / (1000 * 1000)).toFixed(2)} MB`;
    return `${(value / (1000 * 1000 * 1000)).toFixed(2)} GB`;
}

/**
 * Format message store storage usage against its limit.
 */
export function formatStorageUsage(stats: PropagationNodeStats | null | undefined): string {
    if (!stats || typeof stats !== "object") {
        return "0 B";
    }
    const used = formatByteSize(stats.messagestore_bytes);
    const limitValue = Number(stats.messagestore_limit_bytes);
    if (!Number.isFinite(limitValue) || limitValue <= 0) {
        return used;
    }
    return `${used} / ${formatByteSize(limitValue)}`;
}

/**
 * Format uptime seconds into human-friendly duration.
 */
export function formatSeconds(seconds: number | string | undefined | null): string {
    if (seconds == null || Number.isNaN(Number(seconds))) return "0s";
    const total = Math.max(0, Number(seconds));
    if (total < 60) return `${Math.floor(total)}s`;
    const minutes = Math.floor(total / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
}

/**
 * Format relative time ago from datetime string.
 */
export function formatTimeAgo(datetimeString: string | undefined | null): string {
    return Utils.formatTimeAgo(datetimeString || "");
}

/**
 * Format destination hash with standard formatting.
 */
export function formatDestinationHash(hash: string | undefined | null): string {
    return Utils.formatDestinationHash(hash || "");
}

/**
 * Format path information into localized hops and interface text.
 */
export function formatPathLabel(path: NodePathInfo | null | undefined): string {
    if (!path) {
        return t("tools.propagation_nodes.no_path");
    }
    const hops = Number(path.hops);
    let hopsText = t("tools.propagation_nodes.unknown_hops");
    if (Number.isFinite(hops)) {
        hopsText =
            hops === 1 ? t("tools.propagation_nodes.hop_one") : t("tools.propagation_nodes.hop_many", { count: hops });
    }
    const iface = path.next_hop_interface || t("tools.propagation_nodes.unknown_interface");
    return t("tools.propagation_nodes.path_via", { hops: hopsText, iface });
}
