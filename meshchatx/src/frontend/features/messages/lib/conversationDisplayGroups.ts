// SPDX-License-Identifier: 0BSD

import { CONVERSATION_MESSAGES_PAGE_SIZE } from "./constants.js";
import type { ChatItemLike } from "./conversationMessageHelpers.js";

export { CONVERSATION_MESSAGES_PAGE_SIZE };

export type DisplayGroupSingle = {
    type: "single";
    chatItem: ChatItemLike;
    key: string;
};

export type DisplayGroupImage = {
    type: "imageGroup";
    items: ChatItemLike[];
    key: string;
};

export type DisplayGroup =
    DisplayGroupSingle | DisplayGroupImage | { type: string; key?: string; [k: string]: unknown };

export function itemsFromDisplayGroup(group: unknown): ChatItemLike[] {
    if (!group || typeof group !== "object") {
        return [];
    }
    const g = group as DisplayGroup;
    if (g.type === "single") {
        return (g as DisplayGroupSingle).chatItem ? [(g as DisplayGroupSingle).chatItem] : [];
    }
    if (g.type === "imageGroup" && Array.isArray((g as DisplayGroupImage).items)) {
        return (g as DisplayGroupImage).items.slice();
    }
    return [];
}

export function buildDisplayGroupsNewestFirst(
    itemsOldestFirst: ChatItemLike[],
    canMergeImageIntoImageStrip: (chatItem: ChatItemLike) => boolean
): DisplayGroup[] {
    const items = itemsOldestFirst || [];
    const n = items.length;
    const groups: DisplayGroup[] = [];
    let r = 0;
    while (r < n) {
        const item = items[n - 1 - r];
        if (canMergeImageIntoImageStrip(item)) {
            const run = [item];
            let j = r + 1;
            while (j < n && run.length < 12) {
                const next = items[n - 1 - j];
                if (next.is_outbound !== item.is_outbound) {
                    break;
                }
                if (!canMergeImageIntoImageStrip(next)) {
                    break;
                }
                run.push(next);
                j++;
            }
            if (run.length >= 2) {
                groups.push({
                    type: "imageGroup",
                    items: run,
                    key: run.map((x) => x.lxmf_message?.hash).join("-"),
                });
                r = j;
                continue;
            }
        }
        groups.push({
            type: "single",
            chatItem: item,
            key: String(item.lxmf_message?.hash || ""),
        });
        r++;
    }
    return groups;
}

export function prependDisplayGroupsNewestFirst(
    existingGroupsNewestFirst: DisplayGroup[],
    prependedItemsOldestFirst: ChatItemLike[],
    canMergeImageIntoImageStrip: (chatItem: ChatItemLike) => boolean
): DisplayGroup[] {
    const prepended = prependedItemsOldestFirst || [];
    const existing = existingGroupsNewestFirst || [];
    if (prepended.length === 0) {
        return existing;
    }
    if (existing.length === 0) {
        return buildDisplayGroupsNewestFirst(prepended, canMergeImageIntoImageStrip);
    }

    const tailGroup = existing[existing.length - 1];
    const tailItemsNewestFirst = itemsFromDisplayGroup(tailGroup);
    const tailItemsOldestFirst = tailItemsNewestFirst.slice().reverse();
    const boundaryItemsOldestFirst = prepended.concat(tailItemsOldestFirst);
    const boundaryGroups = buildDisplayGroupsNewestFirst(boundaryItemsOldestFirst, canMergeImageIntoImageStrip);
    const headGroups = existing.slice(0, -1);
    return headGroups.concat(boundaryGroups);
}

export function displayGroupHashesOldestFirst(groupsNewestFirst: DisplayGroup[]): string[] {
    const hashes: string[] = [];
    const groups = groupsNewestFirst || [];
    for (let gi = groups.length - 1; gi >= 0; gi--) {
        const group = groups[gi];
        if (!group || typeof group !== "object") {
            continue;
        }
        if (group.type === "single") {
            const hash = (group as DisplayGroupSingle).chatItem?.lxmf_message?.hash;
            if (hash) {
                hashes.push(hash);
            }
            continue;
        }
        if (group.type === "imageGroup" && Array.isArray((group as DisplayGroupImage).items)) {
            const items = (group as DisplayGroupImage).items;
            for (let ii = items.length - 1; ii >= 0; ii--) {
                const hash = items[ii]?.lxmf_message?.hash;
                if (hash) {
                    hashes.push(hash);
                }
            }
        }
    }
    return hashes;
}

export function incrementalPrependMatchesFullRebuild(
    allItemsOldestFirst: ChatItemLike[],
    pageSizesFromNewest: number[],
    canMergeImageIntoImageStrip: (chatItem: ChatItemLike) => boolean
): boolean {
    const items = allItemsOldestFirst || [];
    const n = items.length;
    let loaded: ChatItemLike[] = [];
    let cached: DisplayGroup[] | null = null;
    for (const count of pageSizesFromNewest) {
        if (count > n) {
            return false;
        }
        const slice = items.slice(n - count);
        const newOlderPrefix = slice.slice(0, slice.length - loaded.length);
        loaded = slice;
        if (cached === null || newOlderPrefix.length === loaded.length) {
            cached = buildDisplayGroupsNewestFirst(loaded, canMergeImageIntoImageStrip);
        } else {
            cached = prependDisplayGroupsNewestFirst(cached, newOlderPrefix, canMergeImageIntoImageStrip);
        }
    }
    const full = buildDisplayGroupsNewestFirst(loaded, canMergeImageIntoImageStrip);
    const incKeys = (cached || []).map((g) => g.key);
    const fullKeys = full.map((g) => g.key);
    if (incKeys.length !== fullKeys.length) {
        return false;
    }
    for (let i = 0; i < incKeys.length; i++) {
        if (incKeys[i] !== fullKeys[i]) {
            return false;
        }
    }
    const incHashes = displayGroupHashesOldestFirst(cached || []);
    const fullHashes = displayGroupHashesOldestFirst(full);
    return incHashes.join("\u241e") === fullHashes.join("\u241e");
}
