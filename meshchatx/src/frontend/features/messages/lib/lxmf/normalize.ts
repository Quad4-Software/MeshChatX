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

/**
 * Parse composer text into LXMF command/request fields.
 * Empty input keeps the legacy behaviour: a telemetry (location) request.
 * JSON arrays/objects are normalised key-by-key; "key arg" text maps via
 * normalizeSidebandCommandKey.
 */
export function parseCommandOrRequestText(text: string): Array<Record<string, unknown>> {
    const trimmed = String(text || "").trim();
    const nowTs = Math.floor(Date.now() / 1000);

    if (!trimmed) {
        return [{ "0x01": nowTs }];
    }

    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
        const parsed = JSON.parse(trimmed);
        const list = Array.isArray(parsed) ? parsed : [parsed];
        const out: Array<Record<string, unknown>> = [];
        for (const cmd of list) {
            if (!cmd || typeof cmd !== "object" || Array.isArray(cmd)) {
                continue;
            }
            const mapped: Record<string, unknown> = {};
            for (const [k, v] of Object.entries(cmd as Record<string, unknown>)) {
                const normalized = normalizeSidebandCommandKey(k);
                if (!normalized) {
                    continue;
                }
                mapped[normalized] = v;
            }
            if (Object.keys(mapped).length > 0) {
                out.push(mapped);
            }
        }
        if (out.length === 0) {
            throw new Error("No valid command keys found");
        }
        return out;
    }

    const firstSpace = trimmed.search(/\s/);
    const keyToken = firstSpace === -1 ? trimmed : trimmed.slice(0, firstSpace);
    const arg = firstSpace === -1 ? "" : trimmed.slice(firstSpace + 1).trim();
    const key = normalizeSidebandCommandKey(keyToken);
    if (!key) {
        return [{ "0x00": trimmed }];
    }

    if (key === "0x01") {
        // request/location_request/telemetry_request
        return [{ "0x01": arg ? Number.parseInt(arg, 10) || nowTs : nowTs }];
    }
    if (key === "0x02" || key === "0x04") {
        return [{ [key]: arg ? arg.toLowerCase() !== "false" : true }];
    }
    if (key === "0x03") {
        return [{ "0x03": arg || "ping" }];
    }
    if (key === "0x00") {
        return [{ "0x00": arg || trimmed }];
    }
    return [{ [key]: arg || true }];
}
