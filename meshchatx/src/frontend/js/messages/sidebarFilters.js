// SPDX-License-Identifier: 0BSD AND MIT

/**
 * Sidebar filter registry and layout persistence.
 *
 * Each sidebar context (conversations, announces) has a fixed catalog of
 * available filters. The user layout is just an ordered list of the filter
 * ids shown as chips. Any catalog filter can still be toggled active from
 * the overflow menu. The layout lives in localStorage, matching how other
 * per-browser UI prefs (FOLDERS_EXPANDED, INTERFACES_STATUS_FILTER) persist.
 */

import { STORAGE_KEYS } from "../constants";

export const SIDEBAR_FILTER_DEFS = {
    conversations: [
        { id: "unread", labelKey: "messages.unread", icon: "email-outline" },
        { id: "failed", labelKey: "messages.failed", icon: "alert-circle-outline" },
        { id: "attachments", labelKey: "messages.attachments", icon: "attachment" },
        { id: "favourites", labelKey: "messages.filter_favourites", icon: "star-outline" },
    ],
    announces: [
        { id: "direct", labelKey: "messages.filter_direct", icon: "access-point-network" },
        { id: "nearby", labelKey: "messages.filter_nearby", icon: "map-marker-radius-outline" },
        { id: "pinned", labelKey: "messages.filter_pinned", icon: "pin-outline" },
        { id: "blocked", labelKey: "messages.filter_blocked", icon: "cancel" },
    ],
};

const DEFAULT_LAYOUT = {
    conversations: ["unread", "failed", "attachments"],
    announces: ["direct", "pinned"],
};

/**
 * Custom filters are user-defined text matchers stored inside the layout
 * object under custom[context]. The def shape matches the catalog defs
 * except label is a raw string and query holds comma-separated terms
 * matched case-insensitively against display name, custom name, and
 * destination hash of a conversation or announce peer.
 */
export const CUSTOM_FILTER_PREFIX = "custom_";

let customSeq = 0;

export function isCustomFilterId(id) {
    return typeof id === "string" && id.startsWith(CUSTOM_FILTER_PREFIX);
}

export function makeCustomFilter(label, query) {
    customSeq += 1;
    return {
        id: `${CUSTOM_FILTER_PREFIX}${Date.now().toString(36)}${customSeq}`,
        label: String(label || "").trim() || "Filter",
        query: String(query || "").trim(),
        icon: "tag-outline",
    };
}

export function customFilterTerms(query) {
    return String(query || "")
        .toLowerCase()
        .split(/[,;\s]+/)
        .filter(Boolean);
}

export function matchesCustomQuery(item, query) {
    const terms = customFilterTerms(query);
    if (terms.length === 0 || !item) {
        return true;
    }
    const hay = [item.display_name, item.custom_display_name, item.destination_hash]
        .filter(Boolean)
        .join("\n")
        .toLowerCase();
    return terms.some((t) => hay.includes(t));
}

function sanitizeCustomDefs(raw) {
    const out = [];
    for (const def of Array.isArray(raw) ? raw : []) {
        if (def && isCustomFilterId(def.id) && typeof def.label === "string" && typeof def.query === "string") {
            out.push({ id: def.id, label: def.label, query: def.query, icon: def.icon || "tag-outline" });
        }
    }
    return out;
}

function storageGet(key) {
    try {
        return typeof localStorage !== "undefined" ? localStorage.getItem(key) : null;
    } catch {
        return null;
    }
}

function storageSet(key, value) {
    try {
        if (typeof localStorage !== "undefined") {
            localStorage.setItem(key, value);
        }
    } catch {
        // ignore
    }
}

function sanitizeLayout(raw, context, customDefs) {
    const defIds = new Set(SIDEBAR_FILTER_DEFS[context].map((d) => d.id));
    for (const def of customDefs) {
        defIds.add(def.id);
    }
    const seen = new Set();
    const out = [];
    for (const id of Array.isArray(raw) ? raw : []) {
        if (typeof id === "string" && defIds.has(id) && !seen.has(id)) {
            seen.add(id);
            out.push(id);
        }
    }
    return out;
}

export function loadSidebarFilterLayout() {
    const defaults = { ...DEFAULT_LAYOUT, custom: {} };
    const raw = storageGet(STORAGE_KEYS.SIDEBAR_FILTERS);
    if (!raw) {
        return defaults;
    }
    try {
        const parsed = JSON.parse(raw);
        const layout = { custom: {} };
        for (const context of Object.keys(SIDEBAR_FILTER_DEFS)) {
            const customDefs = sanitizeCustomDefs(parsed?.custom?.[context]);
            layout.custom[context] = customDefs;
            layout[context] =
                parsed && Object.prototype.hasOwnProperty.call(parsed, context)
                    ? sanitizeLayout(parsed[context], context, customDefs)
                    : DEFAULT_LAYOUT[context].slice();
        }
        return layout;
    } catch {
        return defaults;
    }
}

export function saveSidebarFilterLayout(layout) {
    storageSet(STORAGE_KEYS.SIDEBAR_FILTERS, JSON.stringify(layout));
}

export function sidebarFilterDefs(context) {
    return SIDEBAR_FILTER_DEFS[context] || [];
}

/** Catalog defs plus custom defs recorded in a layout object. */
export function resolveSidebarFilterDefs(context, layout) {
    return [...sidebarFilterDefs(context), ...(layout?.custom?.[context] || [])];
}

export function sidebarFilterDefaults(context) {
    return (DEFAULT_LAYOUT[context] || []).slice();
}

/**
 * Move draggedId before/after targetId inside layout[context] and persist.
 * targetId null means drop at the end. Returns the new layout object.
 */
export function moveSidebarFilter(layout, context, draggedId, targetId, after = false) {
    const order = (layout[context] || []).filter((id) => id !== draggedId);
    let idx = targetId === null ? order.length : order.indexOf(targetId);
    if (idx < 0) {
        idx = order.length;
    }
    order.splice(after ? idx + 1 : idx, 0, draggedId);
    const next = { ...layout, [context]: order };
    saveSidebarFilterLayout(next);
    return next;
}
