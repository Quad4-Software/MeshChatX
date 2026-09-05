// SPDX-License-Identifier: 0BSD

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

export type NomadFavouriteSection = {
    id: string;
    name: string;
    collapsed: boolean;
};

export type NomadFavouritesLayout = {
    sections: NomadFavouriteSection[];
    sectionOrder: string[];
    favouritesBySection: Record<string, string[]>;
};

function clipStr(value: unknown, maxLen: number): string {
    if (typeof value !== "string") {
        return "";
    }
    return value.length <= maxLen ? value : value.slice(0, maxLen);
}

export function normalizeNomadFavouritesLayout(layout: unknown): NomadFavouritesLayout | null {
    if (!layout || typeof layout !== "object" || Array.isArray(layout)) {
        return null;
    }
    const rawObj = layout as Record<string, unknown>;
    if (!Array.isArray(rawObj.sections)) {
        return null;
    }
    const favouritesBySection: Record<string, unknown> =
        rawObj.favouritesBySection &&
        typeof rawObj.favouritesBySection === "object" &&
        !Array.isArray(rawObj.favouritesBySection)
            ? (rawObj.favouritesBySection as Record<string, unknown>)
            : {};
    const sections: NomadFavouriteSection[] = [];
    const sectionIds = new Set<string>();
    for (const section of rawObj.sections) {
        if (sections.length >= MAX_SECTIONS) {
            break;
        }
        if (!section || typeof section !== "object" || Array.isArray(section)) {
            continue;
        }
        const s = section as Record<string, unknown>;
        if (typeof s.id !== "string") {
            continue;
        }
        const sectionId = s.id.trim();
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
            name: clipStr(s.name, MAX_SECTION_NAME_LEN),
            collapsed: s.collapsed === true,
        });
    }
    if (sections.length === 0) {
        return null;
    }
    const sectionOrder: string[] = [];
    if (Array.isArray(rawObj.sectionOrder)) {
        for (const sid of rawObj.sectionOrder) {
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
    const sanitizedMap: Record<string, string[]> = Object.create(null);
    let totalHashes = 0;
    for (const key of Object.keys(favouritesBySection)) {
        if (!sectionIds.has(key) || FORBIDDEN_SECTION_IDS.has(key)) {
            continue;
        }
        const arr = favouritesBySection[key];
        if (!Array.isArray(arr)) {
            continue;
        }
        const hashes: string[] = [];
        const seen = new Set<string>();
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

export function serializeNomadFavouritesLayout(layout: unknown): string {
    const normalized = normalizeNomadFavouritesLayout(layout);
    if (!normalized) {
        return "";
    }
    return JSON.stringify(normalized);
}

export function readLocalNomadFavouritesLayout(): NomadFavouritesLayout | null {
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
                    favouritesBySection: {
                        default: parsedOrder.filter((h: unknown): h is string => typeof h === "string"),
                    },
                });
            }
        }
    } catch {
        // ignore
    }
    return null;
}

export function clearLocalNomadFavouritesLayout(): void {
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

function writeLocalLayout(layout: unknown): void {
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

let saveInFlight: Promise<void> | null = null;
let pendingSaveLayout: NomadFavouritesLayout | null = null;
let lastSavedSerialized = "";

export async function loadNomadFavouritesLayout(api: any): Promise<NomadFavouritesLayout | null> {
    if (!api?.get) {
        return readLocalNomadFavouritesLayout();
    }
    try {
        const response = await api.get("/api/v1/favourites/layout");
        const remote = normalizeNomadFavouritesLayout(response?.data?.layout);
        if (remote) {
            writeLocalLayout(remote);
            lastSavedSerialized = serializeNomadFavouritesLayout(remote);
            return remote;
        }
    } catch {
        // fall back to local
    }
    const local = readLocalNomadFavouritesLayout();
    if (local && api?.put) {
        try {
            const pushRes = await api.put("/api/v1/favourites/layout", { layout: local });
            const saved = normalizeNomadFavouritesLayout(pushRes?.data?.layout) || local;
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

async function flushPendingSave(api: any): Promise<void> {
    while (pendingSaveLayout) {
        const layout = pendingSaveLayout;
        pendingSaveLayout = null;
        const serialized = serializeNomadFavouritesLayout(layout);
        if (!serialized || serialized === lastSavedSerialized) {
            continue;
        }
        try {
            const response = await api.put("/api/v1/favourites/layout", { layout });
            if (pendingSaveLayout) {
                continue;
            }
            const saved = normalizeNomadFavouritesLayout(response?.data?.layout) || layout;
            writeLocalLayout(saved);
            lastSavedSerialized = serializeNomadFavouritesLayout(saved);
        } catch {
            writeLocalLayout(layout);
        }
    }
}

export async function saveNomadFavouritesLayout(api: any, layout: unknown): Promise<NomadFavouritesLayout | null> {
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

export function _resetNomadFavouritesLayoutSaveStateForTests(): void {
    saveInFlight = null;
    pendingSaveLayout = null;
    lastSavedSerialized = "";
}
