// SPDX-License-Identifier: 0BSD

export const DEFAULT_MAX_SEARCH_RESULTS = 200;
export const DEFAULT_BACKGROUND_COLOUR = "#e5e7eb";
export const DEFAULT_FOREGROUND_COLOUR = "#6b7280";

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
 * Filter icon names by query substring and cap results
 */
export function filterIconNames(
    iconNames: string[],
    search: string,
    limit: number = DEFAULT_MAX_SEARCH_RESULTS
): string[] {
    const searchLower = (search || "").trim().toLowerCase();
    if (!searchLower) {
        return iconNames.slice(0, limit);
    }
    return iconNames.filter((iconName) => iconName.toLowerCase().includes(searchLower)).slice(0, limit);
}

/**
 * Normalize hex colour code to standard 6 char hex
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
