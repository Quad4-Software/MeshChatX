// SPDX-License-Identifier: 0BSD

/** Pure outbound / transfer UI label helpers used by conversation bubbles. */

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
