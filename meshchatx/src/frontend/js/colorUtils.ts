// SPDX-License-Identifier: 0BSD

/** Shared hex colour helpers and default picker swatches. */

export const DEFAULT_COLOR_SWATCHES = [
    "#ef4444",
    "#f97316",
    "#eab308",
    "#22c55e",
    "#3b82f6",
    "#8b5cf6",
    "#ec4899",
    "#64748b",
    "#ffffff",
    "#18181b",
    "#0ea5e9",
    "#14b8a6",
];

/**
 * Normalize a hex colour code to a standard 6 char lowercase hex string.
 * Returns an empty string for anything that is not a valid colour.
 */
export function normalizeHexColour(value: unknown): string {
    if (typeof value !== "string") {
        return "";
    }
    let hex = value.trim();
    if (hex.length === 9) {
        hex = hex.substring(0, 7);
    }
    if (/^#[0-9a-fA-F]{6}$/.test(hex)) {
        return hex.toLowerCase();
    }
    return "";
}
