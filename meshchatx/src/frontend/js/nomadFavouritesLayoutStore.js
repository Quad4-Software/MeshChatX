// SPDX-License-Identifier: 0BSD

import { withRetryableHttp } from "./httpRetry.js";

export const NOMAD_FAVOURITES_LAYOUT_KEY = "meshchat.nomadnet.favourites.layout";
export const NOMAD_FAVOURITES_LEGACY_ORDER_KEY = "meshchat.nomadnet.favourites";

// Keep in sync with meshchatx/src/backend/favourites_layout.py
export const MAX_SECTIONS = 64;
export const MAX_SECTION_ID_LEN = 64;
export const MAX_SECTION_NAME_LEN = 128;
export const MAX_HASHES_PER_SECTION = 2000;
export const MAX_TOTAL_HASHES = 4000;
export const MAX_HASH_LEN = 64;

const FORBIDDEN_SECTION_IDS = new Set(["__proto__", "constructor", "prototype"]);

/**
 * @param {unknown} value
 * @param {number} maxLen
 * @returns {string}
 */
function clipStr(value, maxLen) {
    if (typeof value !== "string") {
        return "";
    }
    return value.length <= maxLen ? value : value.slice(0, maxLen);
}

/**
 * @param {unknown} layout
 * @returns {{sections: object[], sectionOrder: string[], favouritesBySection: Record<string, string[]>}|null}
 */
export function normalizeNomadFavouritesLayout(layout) {
    if (!layout || typeof layout !== "object" || Array.isArray(layout) || !Array.isArray(layout.sections)) {
        return null;
    }
    const favouritesBySection =
        layout.favouritesBySection &&
        typeof layout.favouritesBySection === "object" &&
        !Array.isArray(layout.favouritesBySection)
            ? layout.favouritesBySection
            : {};
    const sections = [];
    const sectionIds = new Set();
    for (const section of layout.sections) {
        if (sections.length >= MAX_SECTIONS) {
            break;
        }
        if (!section || typeof section !== "object" || Array.isArray(section)) {
            continue;
        }
        if (typeof section.id !== "string") {
            continue;
        }
        const sectionId = section.id.trim();
        if (
            !sectionId ||
            sectionId.length > MAX_SECTION_ID_LEN ||
            sectionIds.has(sectionId) ||
            FORBIDDEN_SECTION_IDS.has(sectionId)
        ) {
            continue;
        }
        sectionIds.add(sectionId);
        sections.push({
            id: sectionId,
            name: clipStr(section.name, MAX_SECTION_NAME_LEN),
            collapsed: section.collapsed === true,
        });
    }
    if (sections.length === 0) {
        return null;
    }
    const sectionOrder = [];
    if (Array.isArray(layout.sectionOrder)) {
        for (const sid of layout.sectionOrder) {
            if (typeof sid !== "string") {
                continue;
            }
            const id = sid.trim();
            if (sectionIds.has(id) && !sectionOrder.includes(id)) {
                sectionOrder.push(id);
            }
            if (sectionOrder.length >= MAX_SECTIONS) {
                break;
            }
        }
    }
    for (const section of sections) {
        if (!sectionOrder.includes(section.id)) {
            sectionOrder.push(section.id);
        }
    }
    const sanitizedMap = Object.create(null);
    let totalHashes = 0;
    for (const key of Object.keys(favouritesBySection)) {
        if (!sectionIds.has(key) || FORBIDDEN_SECTION_IDS.has(key)) {
            continue;
        }
        const arr = favouritesBySection[key];
        if (!Array.isArray(arr)) {
            continue;
        }
        const hashes = [];
        const seen = new Set();
        for (const item of arr) {
            if (totalHashes >= MAX_TOTAL_HASHES || hashes.length >= MAX_HASHES_PER_SECTION) {
                break;
            }
            if (typeof item !== "string") {
                continue;
            }
            const h = item.trim();
            if (!h || h.length > MAX_HASH_LEN || seen.has(h)) {
                continue;
            }
            seen.add(h);
            hashes.push(h);
            totalHashes += 1;
        }
        sanitizedMap[key] = hashes;
    }
    for (const section of sections) {
        if (!Object.prototype.hasOwnProperty.call(sanitizedMap, section.id)) {
            sanitizedMap[section.id] = [];
        }
    }
    return { sections, sectionOrder, favouritesBySection: sanitizedMap };
}

/**
 * Stable JSON for equality checks (avoids unnecessary PUTs).
 * @param {object|null} layout
 * @returns {string}
 */
export function serializeNomadFavouritesLayout(layout) {
    const normalized = normalizeNomadFavouritesLayout(layout);
    if (!normalized) {
        return "";
    }
    return JSON.stringify(normalized);
}

export function readLocalNomadFavouritesLayout() {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return null;
        }
        const stored = window.localStorage.getItem(NOMAD_FAVOURITES_LAYOUT_KEY);
        if (stored) {
            return normalizeNomadFavouritesLayout(JSON.parse(stored));
        }
        const legacyOrder = window.localStorage.getItem(NOMAD_FAVOURITES_LEGACY_ORDER_KEY);
        if (legacyOrder) {
            const parsedOrder = JSON.parse(legacyOrder);
            if (Array.isArray(parsedOrder)) {
                return normalizeNomadFavouritesLayout({
                    sections: [{ id: "default", name: "Favourites", collapsed: false }],
                    sectionOrder: ["default"],
                    favouritesBySection: { default: parsedOrder.filter((h) => typeof h === "string") },
                });
            }
        }
    } catch {
        // ignore
    }
    return null;
}

export function clearLocalNomadFavouritesLayout() {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return;
        }
        window.localStorage.removeItem(NOMAD_FAVOURITES_LAYOUT_KEY);
        window.localStorage.removeItem(NOMAD_FAVOURITES_LEGACY_ORDER_KEY);
    } catch {
        // ignore
    }
    lastSavedSerialized = "";
    pendingSaveLayout = null;
}

function writeLocalLayout(layout) {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return;
        }
        const normalized = normalizeNomadFavouritesLayout(layout);
        if (!normalized) {
            return;
        }
        window.localStorage.setItem(NOMAD_FAVOURITES_LAYOUT_KEY, JSON.stringify(normalized));
    } catch {
        // ignore
    }
}

let saveInFlight = null;
let pendingSaveLayout = null;
let lastSavedSerialized = "";

/**
 * Load favourite section layout from the identity DB, migrating localStorage once.
 * @param {*} api window.api-like client
 * @returns {Promise<object|null>}
 */
export async function loadNomadFavouritesLayout(api) {
    if (!api?.get) {
        return readLocalNomadFavouritesLayout();
    }
    try {
        const response = await withRetryableHttp(() => api.get("/api/v1/favourites/layout"));
        const remote = normalizeNomadFavouritesLayout(response?.data?.layout);
        if (remote) {
            writeLocalLayout(remote);
            lastSavedSerialized = serializeNomadFavouritesLayout(remote);
            return remote;
        }
    } catch {
        // fall through to local
    }
    const local = readLocalNomadFavouritesLayout();
    if (local && api?.put) {
        try {
            const response = await api.put("/api/v1/favourites/layout", { layout: local });
            const saved = normalizeNomadFavouritesLayout(response?.data?.layout) || local;
            writeLocalLayout(saved);
            lastSavedSerialized = serializeNomadFavouritesLayout(saved);
            try {
                window.localStorage?.removeItem(NOMAD_FAVOURITES_LEGACY_ORDER_KEY);
            } catch {
                // ignore
            }
            return saved;
        } catch {
            return local;
        }
    }
    if (local) {
        lastSavedSerialized = serializeNomadFavouritesLayout(local);
    }
    return local;
}

async function flushPendingSave(api) {
    while (pendingSaveLayout) {
        const layout = pendingSaveLayout;
        pendingSaveLayout = null;
        const serialized = serializeNomadFavouritesLayout(layout);
        if (!serialized || serialized === lastSavedSerialized) {
            continue;
        }
        try {
            const response = await api.put("/api/v1/favourites/layout", { layout });
            // A newer save may have arrived while this PUT was in flight, so prefer that.
            if (pendingSaveLayout) {
                continue;
            }
            const saved = normalizeNomadFavouritesLayout(response?.data?.layout) || layout;
            writeLocalLayout(saved);
            lastSavedSerialized = serializeNomadFavouritesLayout(saved);
        } catch {
            writeLocalLayout(layout);
            // Keep lastSavedSerialized unchanged so a later retry can push again.
        }
    }
}

/**
 * Persist favourite section layout to the identity DB (and local cache).
 * Coalesces concurrent saves and skips no-op PUTs.
 * @param {*} api window.api-like client
 * @param {object} layout
 * @returns {Promise<object|null>}
 */
export async function saveNomadFavouritesLayout(api, layout) {
    const normalized = normalizeNomadFavouritesLayout(layout);
    if (!normalized) {
        return null;
    }
    writeLocalLayout(normalized);
    if (!api?.put) {
        lastSavedSerialized = serializeNomadFavouritesLayout(normalized);
        return normalized;
    }
    const serialized = serializeNomadFavouritesLayout(normalized);
    if (serialized && serialized === lastSavedSerialized) {
        return normalized;
    }
    pendingSaveLayout = normalized;
    if (!saveInFlight) {
        saveInFlight = flushPendingSave(api).finally(() => {
            saveInFlight = null;
        });
    }
    await saveInFlight;
    return readLocalNomadFavouritesLayout() || normalized;
}

/** Test helper: reset coalescing state between cases. */
export function _resetNomadFavouritesLayoutSaveStateForTests() {
    saveInFlight = null;
    pendingSaveLayout = null;
    lastSavedSerialized = "";
}
