// SPDX-License-Identifier: 0BSD

export { DEFAULT_COLOR_SWATCHES, normalizeHexColour } from "../../../js/colorUtils.js";

export const DEFAULT_MAX_SEARCH_RESULTS = 200;
export const DEFAULT_BACKGROUND_COLOUR = "#e5e7eb";
export const DEFAULT_FOREGROUND_COLOUR = "#6b7280";

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
