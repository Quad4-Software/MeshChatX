// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import DownloadUtils from "../../../js/DownloadUtils.js";
import { t } from "../../../js/i18n.js";
import {
    DEFAULT_SECTION_ID,
    buildDefaultSection,
    exportSectionFavouritesPayload,
    matchesFavouriteSearch,
} from "./nomadSidebarFavourites.js";
import type { NomadFavourite, NomadSection } from "./types.js";

export interface FavouritesLayoutState {
    sections: NomadSection[];
    sectionOrder: string[];
    favouritesBySection: Record<string, string[]>;
}

export function createDefaultLayout(): FavouritesLayoutState {
    return {
        sections: [buildDefaultSection(t("nomadnet.favourites"))],
        sectionOrder: [DEFAULT_SECTION_ID],
        favouritesBySection: { [DEFAULT_SECTION_ID]: [] },
    };
}

export function parseStoredLayout(layout: any): FavouritesLayoutState | null {
    if (!layout) return null;
    const sections: NomadSection[] = layout.sections || [];
    const sectionOrder: string[] =
        layout.sectionOrder || (layout.sections ? layout.sections.map((s: any) => s.id) : [DEFAULT_SECTION_ID]);
    const favouritesBySection: Record<string, string[]> = layout.favouritesBySection || {};
    if (sections.length === 0) {
        return createDefaultLayout();
    }
    return { sections, sectionOrder, favouritesBySection };
}

export function buildOrderedSections(sections: NomadSection[], sectionOrder: string[]): NomadSection[] {
    const map: Record<string, NomadSection> = {};
    sections.forEach((s) => {
        map[s.id] = s;
    });
    const ids = sectionOrder.length > 0 ? sectionOrder : sections.map((s) => s.id);
    return ids.map((id) => map[id]).filter(Boolean);
}

export function buildSectionsWithFavourites(
    orderedSections: NomadSection[],
    favouritesBySection: Record<string, string[]>,
    favourites: NomadFavourite[],
    searchTerm: string
): NomadSection[] {
    const s = searchTerm.toLowerCase();
    return orderedSections.map((sec) => {
        const hashes = favouritesBySection[sec.id] || [];
        const favs = hashes
            .map((h) => favourites.find((f) => f.destination_hash === h))
            .filter((f): f is NomadFavourite => Boolean(f))
            .filter((f) => matchesFavouriteSearch(f, s));
        return { ...sec, favourites: favs };
    });
}

export async function promptCreateSection(state: FavouritesLayoutState): Promise<FavouritesLayoutState | null> {
    const name = await DialogUtils.prompt(t("nomadnet.add_section_prompt"), "");
    if (!name || !name.trim()) return null;
    const trimmed = name.trim();
    const id = `sec_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    return {
        sections: [...state.sections, { id, name: trimmed, collapsed: false }],
        sectionOrder: [...state.sectionOrder, id],
        favouritesBySection: { ...state.favouritesBySection, [id]: [] },
    };
}

export function removeSectionFromLayout(state: FavouritesLayoutState, secId: string): FavouritesLayoutState {
    if (secId === DEFAULT_SECTION_ID) return state;
    const orphaned = state.favouritesBySection[secId] || [];
    const def = state.favouritesBySection[DEFAULT_SECTION_ID] || [];
    const nextFavBySec = {
        ...state.favouritesBySection,
        [DEFAULT_SECTION_ID]: [...def, ...orphaned],
    };
    delete nextFavBySec[secId];
    return {
        sections: state.sections.filter((s) => s.id !== secId),
        sectionOrder: state.sectionOrder.filter((id) => id !== secId),
        favouritesBySection: nextFavBySec,
    };
}

export function exportSectionFavourites(
    sec: NomadSection,
    favourites: NomadFavourite[],
    favouritesBySection: Record<string, string[]>
): void {
    const hashes = favouritesBySection[sec.id] || [];
    const favs = hashes
        .map((h) => favourites.find((f) => f.destination_hash === h))
        .filter((f): f is NomadFavourite => Boolean(f));
    const payload = exportSectionFavouritesPayload(
        sec,
        favs.map((f) => f.destination_hash)
    );
    const filename = `nomadnet-section-${sec.name.toLowerCase().replace(/[^a-z0-9_-]/g, "_")}.json`;
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    DownloadUtils.downloadFile(filename, blob);
}

export function exportSelectedFavourites(selectedHashes: string[], favourites: NomadFavourite[]): void {
    const targetFavs = selectedHashes
        .map((h) => favourites.find((f) => f.destination_hash === h))
        .filter((f): f is NomadFavourite => Boolean(f));
    if (targetFavs.length === 0) return;
    const payload = exportSectionFavouritesPayload(
        buildDefaultSection("Selected Favourites"),
        targetFavs.map((f) => f.destination_hash)
    );
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    DownloadUtils.downloadFile("nomadnet-favourites-selected.json", blob);
}
