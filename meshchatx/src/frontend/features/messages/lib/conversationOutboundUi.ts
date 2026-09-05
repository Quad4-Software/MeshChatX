// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";

/** Pure outbound and transfer UI label helpers used by conversation bubbles */

export function transferProgressPercent(loaded: number, total: number): number {
    if (!total || total <= 0) {
        return 0;
    }
    return Math.max(0, Math.min(100, Math.round((loaded / total) * 100)));
}

export function outboundStateTitle(state: string | null | undefined): string {
    const s = String(state || "").toLowerCase();
    if (s === "delivered" || s === "received") return "delivered";
    if (s === "sent" || s === "outbound") return "sent";
    if (s === "failed" || s === "cancelled") return s;
    if (s === "sending") return "sending";
    return s || "unknown";
}

export function outboundStateIconName(state: string | null | undefined): string {
    const s = String(state || "").toLowerCase();
    if (s === "delivered" || s === "received") return "check-all";
    if (s === "sent" || s === "outbound") return "check";
    if (s === "failed") return "alert-circle";
    if (s === "cancelled") return "cancel";
    if (s === "sending") return "loading";
    return "clock-outline";
}

export function outboundTransferStatsLabel(message?: Record<string, unknown> | null): string {
    if (!message || typeof message !== "object") {
        return "";
    }
    const transferred = Number(message.transferred_bytes ?? message.bytes_transferred ?? 0);
    const total = Number(message.total_bytes ?? message.size ?? 0);
    const speed = Number(message.transfer_speed ?? message.speed ?? 0);
    const parts: string[] = [];
    if (total > 0) {
        if (transferred > 0) {
            parts.push(`${Utils.formatBytes(transferred)} / ${Utils.formatBytes(total)}`);
        } else {
            parts.push(Utils.formatBytes(total));
        }
    }
    if (speed > 0) {
        parts.push(`${Utils.formatBytes(speed)}/s`);
    }
    return parts.join(" / ");
}
