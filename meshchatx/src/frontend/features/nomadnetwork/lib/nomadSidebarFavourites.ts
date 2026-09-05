// SPDX-License-Identifier: 0BSD

import { isUnknownNodeDisplayName } from "../../../js/nomadUnknownNodeName.js";
import type { NomadFavourite, NomadNode, NomadSection } from "./types.js";

export const DEFAULT_SECTION_ID = "default";

export function buildDefaultSection(name: string): NomadSection {
    return {
        id: DEFAULT_SECTION_ID,
        name,
        collapsed: false,
    };
}

export function matchesFavouriteSearch(favourite: NomadFavourite, searchTerm: string): boolean {
    if (!searchTerm) {
        return true;
    }
    const clean = searchTerm.toLowerCase();
    const displayName = (favourite.display_name || "").toLowerCase();
    const customName = (favourite.custom_display_name || "").toLowerCase();
    const hash = (favourite.destination_hash || "").toLowerCase();
    return displayName.includes(clean) || customName.includes(clean) || hash.includes(clean);
}

export function favouriteDisplayName(
    favourite: NomadFavourite | null | undefined,
    cachedNode: NomadNode | null | undefined,
    unknownLabel: string
): string {
    if (!favourite) {
        return "";
    }
    const cachedName = cachedNode?.custom_display_name || cachedNode?.display_name || "";
    if (cachedName && !isUnknownNodeDisplayName(cachedName, unknownLabel)) {
        return cachedName;
    }
    const favouriteName = favourite.custom_display_name || favourite.display_name || "";
    if (favouriteName && !isUnknownNodeDisplayName(favouriteName, unknownLabel)) {
        return favouriteName;
    }
    return favouriteName || unknownLabel;
}

export function ensureFavouriteLayout(
    favourites: NomadFavourite[],
    currentSections: NomadSection[],
    currentSectionOrder: string[],
    currentFavouritesBySection: Record<string, string[]>,
    defaultName: string
): {
    sections: NomadSection[];
    sectionOrder: string[];
    favouritesBySection: Record<string, string[]>;
    changed: boolean;
} {
    if (!Array.isArray(favourites) || favourites.length === 0) {
        return {
            sections: currentSections,
            sectionOrder: currentSectionOrder,
            favouritesBySection: currentFavouritesBySection,
            changed: false,
        };
    }

    const hashes = favourites.map((fav) => fav.destination_hash);
    const sectionIds = new Set<string>();
    const sanitizedSections: NomadSection[] = [];

    currentSections.forEach((section) => {
        if (!section || !section.id || sectionIds.has(section.id)) {
            return;
        }
        sectionIds.add(section.id);
        sanitizedSections.push({
            id: section.id,
            name: section.name || defaultName,
            collapsed: section.collapsed === true,
        });
    });

    if (!sectionIds.has(DEFAULT_SECTION_ID)) {
        const defaultSection = buildDefaultSection(defaultName);
        sanitizedSections.unshift(defaultSection);
        sectionIds.add(defaultSection.id);
    }

    const existingOrder = Array.isArray(currentSectionOrder) ? currentSectionOrder : [];
    const filteredOrder = existingOrder.filter((id) => sectionIds.has(id));
    const remaining = sanitizedSections.map((section) => section.id).filter((id) => !filteredOrder.includes(id));
    const nextSectionOrder = [...filteredOrder, ...remaining];

    const nextFavouritesBySection: Record<string, string[]> = {};
    sanitizedSections.forEach((section) => {
        const existing = currentFavouritesBySection[section.id] || [];
        nextFavouritesBySection[section.id] = existing.filter((hash) => hashes.includes(hash));
    });

    const assigned = new Set<string>(Object.values(nextFavouritesBySection).flat());
    hashes.forEach((hash) => {
        if (!assigned.has(hash)) {
            if (!nextFavouritesBySection[DEFAULT_SECTION_ID]) {
                nextFavouritesBySection[DEFAULT_SECTION_ID] = [];
            }
            nextFavouritesBySection[DEFAULT_SECTION_ID].push(hash);
            assigned.add(hash);
        }
    });

    const sectionsChanged = JSON.stringify(currentSections) !== JSON.stringify(sanitizedSections);
    const orderChanged = JSON.stringify(currentSectionOrder) !== JSON.stringify(nextSectionOrder);
    const favouritesChanged = JSON.stringify(currentFavouritesBySection) !== JSON.stringify(nextFavouritesBySection);

    return {
        sections: sanitizedSections,
        sectionOrder: nextSectionOrder,
        favouritesBySection: nextFavouritesBySection,
        changed: sectionsChanged || orderChanged || favouritesChanged,
    };
}

export function moveFavouritesToSection(
    currentMap: Record<string, string[]>,
    hashes: string[],
    targetSectionId: string,
    beforeHash?: string | null
): Record<string, string[]> {
    const unique = [...new Set((hashes || []).filter(Boolean))];
    if (!unique.length || !targetSectionId) {
        return currentMap;
    }

    const updated: Record<string, string[]> = {};
    Object.keys(currentMap).forEach((sectionKey) => {
        updated[sectionKey] = (currentMap[sectionKey] || []).filter((value) => !unique.includes(value));
    });

    if (!updated[targetSectionId]) {
        updated[targetSectionId] = [];
    }

    const targetList = [...updated[targetSectionId]];

    if (beforeHash && !unique.includes(beforeHash)) {
        const insertIndex = targetList.indexOf(beforeHash);
        if (insertIndex === -1) {
            targetList.push(...unique);
        } else {
            targetList.splice(insertIndex, 0, ...unique);
        }
    } else {
        targetList.push(...unique);
    }

    updated[targetSectionId] = targetList;
    return updated;
}

export function exportSectionFavouritesPayload(section: NomadSection, hashes: string[]): Record<string, unknown> {
    return {
        format: "meshchatx/nomadnet_favourites_section/v1",
        exported_at: new Date().toISOString(),
        section: {
            id: section.id,
            name: section.name,
            collapsed: section.collapsed === true,
        },
        destination_hashes: hashes.filter((h) => typeof h === "string"),
    };
}
