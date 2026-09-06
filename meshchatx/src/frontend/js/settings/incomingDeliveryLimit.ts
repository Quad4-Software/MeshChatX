// SPDX-License-Identifier: 0BSD

/** Max incoming direct LXMF delivery size (matches server clamp). */
export const INCOMING_DELIVERY_MAX_BYTES = 1_000_000_000;

export const INCOMING_DELIVERY_PRESET_BYTES = Object.freeze({
    "1mb": 1_000_000,
    "10mb": 10_000_000,
    "25mb": 25_000_000,
    "50mb": 50_000_000,
    "1gb": 1_000_000_000,
});

export type IncomingDeliveryPresetKey = keyof typeof INCOMING_DELIVERY_PRESET_BYTES;
export type IncomingDeliveryUnit = "mb" | "gb";

export type IncomingDeliveryFields = {
    preset: string;
    customAmount: number;
    customUnit: IncomingDeliveryUnit;
};

export function clampIncomingDeliveryBytes(bytes: unknown): number {
    const n = Number(bytes);
    if (!Number.isFinite(n)) {
        return 10_000_000;
    }
    return Math.min(INCOMING_DELIVERY_MAX_BYTES, Math.max(1000, Math.round(n)));
}

function incomingDeliveryCustomFieldsFromBytes(bytes: number): {
    amount: number;
    unit: IncomingDeliveryUnit;
} {
    const b = clampIncomingDeliveryBytes(bytes);
    if (b >= 1_000_000_000 && b % 1_000_000_000 === 0) {
        return { amount: b / 1_000_000_000, unit: "gb" };
    }
    return { amount: Math.round((b / 1_000_000) * 1_000_000) / 1_000_000, unit: "mb" };
}

export function syncIncomingDeliveryFieldsFromBytes(bytes: unknown): IncomingDeliveryFields {
    const b = clampIncomingDeliveryBytes(bytes);
    for (const [key, v] of Object.entries(INCOMING_DELIVERY_PRESET_BYTES)) {
        if (v === b) {
            const cf = incomingDeliveryCustomFieldsFromBytes(b);
            return { preset: key, customAmount: cf.amount, customUnit: cf.unit };
        }
    }
    const cf = incomingDeliveryCustomFieldsFromBytes(b);
    return { preset: "custom", customAmount: cf.amount, customUnit: cf.unit };
}

export function incomingDeliveryBytesFromCustom(amount: unknown, unit: unknown): number {
    const a = Number(amount);
    if (!Number.isFinite(a) || a <= 0) {
        return 10_000_000;
    }
    const u: IncomingDeliveryUnit = unit === "gb" ? "gb" : "mb";
    const raw = u === "gb" ? a * 1_000_000_000 : a * 1_000_000;
    return clampIncomingDeliveryBytes(raw);
}

export function incomingDeliveryBytesFromPresetKey(presetKey: string): number | null {
    return INCOMING_DELIVERY_PRESET_BYTES[presetKey as IncomingDeliveryPresetKey] ?? null;
}
