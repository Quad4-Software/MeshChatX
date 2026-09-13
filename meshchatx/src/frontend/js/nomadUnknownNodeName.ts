// SPDX-License-Identifier: 0BSD

/**
 * Canonical and localized placeholder names that must not overwrite a stored
 * favourite display name. Keep in sync with backend UNKNOWN_FAVOURITE_NAMES.
 */
export const UNKNOWN_NODE_DISPLAY_NAMES = Object.freeze([
    "Unknown Node",
    "Anonymous Node",
    "Unbekannter Knoten",
    "Nodo desconocido",
    "Tuntematon solmu",
    "Noeud inconnu",
    "Nodo Sconosciuto",
    "Onbekende knoop",
    "Неизвестный узел",
    "未知节点",
]);

const UNKNOWN_NODE_NAME_SET = new Set(UNKNOWN_NODE_DISPLAY_NAMES.map((n) => n.toLowerCase()));

export function isUnknownNodeDisplayName(name: unknown, localizedUnknown = ""): boolean {
    if (typeof name !== "string") {
        return true;
    }
    const trimmed = name.trim();
    if (!trimmed) {
        return true;
    }
    if (UNKNOWN_NODE_NAME_SET.has(trimmed.toLowerCase())) {
        return true;
    }
    if (typeof localizedUnknown === "string" && localizedUnknown.trim()) {
        return trimmed.toLowerCase() === localizedUnknown.trim().toLowerCase();
    }
    return false;
}

/**
 * Prefer a meaningful name for favourite upserts; never send a localized
 * unknown sentinel that the backend would treat as a real rename.
 */
export function resolveFavouriteUpsertDisplayName(
    node?: { custom_display_name?: string | null; display_name?: string | null; [key: string]: unknown } | null,
    existingFavourite?: {
        custom_display_name?: string | null;
        display_name?: string | null;
        [key: string]: unknown;
    } | null,
    localizedUnknown = ""
): string {
    const candidate =
        (typeof node?.custom_display_name === "string" && node.custom_display_name) ||
        (typeof node?.display_name === "string" && node.display_name) ||
        "";
    if (!isUnknownNodeDisplayName(candidate, localizedUnknown)) {
        return candidate.trim();
    }
    const existing =
        (typeof existingFavourite?.custom_display_name === "string" && existingFavourite.custom_display_name) ||
        (typeof existingFavourite?.display_name === "string" && existingFavourite.display_name) ||
        "";
    if (existing && !isUnknownNodeDisplayName(existing, localizedUnknown)) {
        return existing.trim();
    }
    return "Unknown Node";
}
