// SPDX-License-Identifier: 0BSD

export const APP_TOP_NAV_LAYOUT_KEY = "meshchatx.topnav.layout";

/**
 * Nav section buttons shown in the top bar by default, in order. Ids refer to
 * entries in the nav registry (js/registries/coreNavEntries.ts).
 */
export const DEFAULT_TOP_NAV_ITEM_IDS = ["relay-chat", "call", "nomadnetwork"];

const FORBIDDEN_IDS = new Set(["__proto__", "constructor", "prototype"]);

function readRaw(): string | null {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return null;
        }
        return window.localStorage.getItem(APP_TOP_NAV_LAYOUT_KEY);
    } catch {
        return null;
    }
}

export function normalizeTopNavItemIds(raw: unknown): string[] | null {
    if (!Array.isArray(raw)) {
        return null;
    }
    const ids: string[] = [];
    for (const value of raw) {
        if (typeof value !== "string") {
            continue;
        }
        const id = value.trim();
        if (!id || FORBIDDEN_IDS.has(id) || ids.includes(id)) {
            continue;
        }
        ids.push(id);
    }
    return ids;
}

/**
 * Stored item ids, or null when the default set applies.
 */
export function loadTopNavItemIds(): string[] | null {
    const raw = readRaw();
    if (raw == null) {
        return null;
    }
    try {
        return normalizeTopNavItemIds(JSON.parse(raw));
    } catch {
        return null;
    }
}

/**
 * Reactive view of the pinned top-nav item ids. null means defaults.
 * Shared by the app header and the settings editor.
 */
export const topNavLayoutState = $state<{ itemIds: string[] | null }>({
    itemIds: loadTopNavItemIds(),
});

export function saveTopNavItemIds(ids: unknown): void {
    const normalized = normalizeTopNavItemIds(ids) || [];
    try {
        if (typeof window !== "undefined" && window.localStorage) {
            window.localStorage.setItem(APP_TOP_NAV_LAYOUT_KEY, JSON.stringify(normalized));
        }
    } catch {
        // persistence is best-effort
    }
    topNavLayoutState.itemIds = normalized;
}

export function resetTopNavItemIds(): void {
    try {
        if (typeof window !== "undefined" && window.localStorage) {
            window.localStorage.removeItem(APP_TOP_NAV_LAYOUT_KEY);
        }
    } catch {
        // persistence is best-effort
    }
    topNavLayoutState.itemIds = null;
}

/**
 * Effective pinned ids: the stored set, or defaults when nothing is stored.
 */
export function resolveTopNavItemIds(itemIds: string[] | null | undefined): string[] {
    return itemIds == null ? [...DEFAULT_TOP_NAV_ITEM_IDS] : itemIds;
}

/**
 * Filter and order nav registry entries by the pinned id list. Ids that are
 * not registered or not currently visible are skipped.
 */
export function orderedTopNavItems<T extends { id: string }>(
    availableItems: T[] | null | undefined,
    itemIds: string[] | null | undefined
): T[] {
    const byId = new Map((availableItems || []).map((item) => [item.id, item]));
    const ordered: T[] = [];
    for (const id of resolveTopNavItemIds(itemIds)) {
        const item = byId.get(id);
        if (item) {
            ordered.push(item);
        }
    }
    return ordered;
}
