// SPDX-License-Identifier: 0BSD

/**
 * Identity-scoped TileCache map_state keys so view state does not leak across identities.
 */

export const LEGACY_MAP_STATE_KEY = "last_view";

export function mapViewStateKey(identityHash: string | null = null, tabStorageId: string | null = null): string {
    const id = String(identityHash || "anon")
        .toLowerCase()
        .replace(/[^0-9a-f]/g, "")
        .slice(0, 16);
    const scoped = id.length > 0 ? id : "anon";
    if (tabStorageId) {
        return `map_tab_${scoped}_${tabStorageId}`;
    }
    return `last_view_${scoped}`;
}

export function legacyMapTabStateKey(tabStorageId: string | null = null): string {
    return `map_tab_${tabStorageId}`;
}
