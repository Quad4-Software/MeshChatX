// SPDX-License-Identifier: 0BSD

import { reactive } from "vue";

export const APP_TOP_NAV_LAYOUT_KEY = "meshchatx.topnav.layout";

/**
 * Nav section buttons shown in the top bar by default, in order. Ids refer to
 * entries in the nav registry (js/registries/coreNavEntries.js).
 */
export const DEFAULT_TOP_NAV_ITEM_IDS = ["relay-chat", "call", "nomadnetwork"];

const FORBIDDEN_IDS = new Set(["__proto__", "constructor", "prototype"]);

function readRaw() {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return null;
        }
        return window.localStorage.getItem(APP_TOP_NAV_LAYOUT_KEY);
    } catch {
        return null;
    }
}

/**
 * @param {unknown} raw
 * @returns {string[] | null}
 */
export function normalizeTopNavItemIds(raw) {
    if (!Array.isArray(raw)) {
        return null;
    }
    const ids = [];
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
 * @returns {string[] | null}
 */
export function loadTopNavItemIds() {
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
export const topNavLayoutState = reactive({
    itemIds: loadTopNavItemIds(),
});

/**
 * @param {string[]} ids
 */
export function saveTopNavItemIds(ids) {
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

export function resetTopNavItemIds() {
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
 * @param {string[] | null | undefined} itemIds
 * @returns {string[]}
 */
export function resolveTopNavItemIds(itemIds) {
    return itemIds == null ? [...DEFAULT_TOP_NAV_ITEM_IDS] : itemIds;
}

/**
 * Filter and order nav registry entries by the pinned id list. Ids that are
 * not registered or not currently visible are skipped.
 * @param {Array<{ id: string }>} availableItems
 * @param {string[] | null | undefined} itemIds
 * @returns {typeof availableItems}
 */
export function orderedTopNavItems(availableItems, itemIds) {
    const byId = new Map((availableItems || []).map((item) => [item.id, item]));
    const ordered = [];
    for (const id of resolveTopNavItemIds(itemIds)) {
        const item = byId.get(id);
        if (item) {
            ordered.push(item);
        }
    }
    return ordered;
}
