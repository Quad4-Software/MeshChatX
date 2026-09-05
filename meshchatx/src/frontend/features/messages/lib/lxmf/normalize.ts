// SPDX-License-Identifier: 0BSD

export type LxmfMessageNormalized = Record<string, unknown> & {
    created_at?: string;
    timestamp?: number;
    state?: string;
};

export function normalizeLxmfMessage(msg: LxmfMessageNormalized, isOutbound: boolean): LxmfMessageNormalized {
    const normalized = { ...msg };
    if (!normalized.created_at && normalized.timestamp) {
        normalized.created_at = new Date(normalized.timestamp * 1000).toISOString();
    }
    if (isOutbound && normalized.state === "unknown") {
        normalized.state = "outbound";
    }
    return normalized;
}

export function normalizeSidebandCommandKey(key: unknown): string | null {
    const raw = String(key ?? "").trim();
    if (!raw) {
        return null;
    }
    const known: Record<string, string> = {
        plugin: "0x00",
        telemetry_request: "0x01",
        request: "0x01",
        location_request: "0x01",
        ping: "0x02",
        echo: "0x03",
        signal_report: "0x04",
    };
    if (Object.prototype.hasOwnProperty.call(known, raw.toLowerCase())) {
        return known[raw.toLowerCase()];
    }
    if (/^\d+$/.test(raw)) {
        const n = Number.parseInt(raw, 10);
        if (Number.isInteger(n) && n >= 0 && n <= 255) {
            return `0x${n.toString(16).padStart(2, "0")}`;
        }
    }
    if (/^0x[0-9a-f]{1,2}$/i.test(raw)) {
        return `0x${raw.slice(2).toLowerCase().padStart(2, "0")}`;
    }
    return null;
}
