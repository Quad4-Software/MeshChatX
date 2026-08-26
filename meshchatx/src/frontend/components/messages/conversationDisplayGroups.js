// SPDX-License-Identifier: 0BSD

/** Messages fetched per incremental history page. */
export const CONVERSATION_MESSAGES_PAGE_SIZE = 50;

/**
 * @param {unknown} group
 * @returns {unknown[]}
 */
export function itemsFromDisplayGroup(group) {
    if (!group || typeof group !== "object") {
        return [];
    }
    if (group.type === "single") {
        return group.chatItem ? [group.chatItem] : [];
    }
    if (group.type === "imageGroup" && Array.isArray(group.items)) {
        return group.items.slice();
    }
    return [];
}

/**
 * Build display groups newest-first from peer chat items oldest-first.
 *
 * @param {unknown[]} itemsOldestFirst
 * @param {(chatItem: unknown) => boolean} canMergeImageIntoImageStrip
 * @returns {unknown[]}
 */
export function buildDisplayGroupsNewestFirst(itemsOldestFirst, canMergeImageIntoImageStrip) {
    const items = itemsOldestFirst || [];
    const n = items.length;
    const groups = [];
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
                    key: run.map((x) => x.lxmf_message.hash).join("-"),
                });
                r = j;
                continue;
            }
        }
        groups.push({
            type: "single",
            chatItem: item,
            key: item.lxmf_message.hash,
        });
        r++;
    }
    return groups;
}

/**
 * Extend cached newest-first groups after prepending older peer chat items.
 *
 * @param {unknown[]} existingGroupsNewestFirst
 * @param {unknown[]} prependedItemsOldestFirst
 * @param {(chatItem: unknown) => boolean} canMergeImageIntoImageStrip
 * @returns {unknown[]}
 */
export function prependDisplayGroupsNewestFirst(
    existingGroupsNewestFirst,
    prependedItemsOldestFirst,
    canMergeImageIntoImageStrip
) {
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

/**
 * Flatten display groups to message hashes oldest-first (oracle helper).
 *
 * @param {unknown[]} groupsNewestFirst
 * @returns {string[]}
 */
export function displayGroupHashesOldestFirst(groupsNewestFirst) {
    const hashes = [];
    const groups = groupsNewestFirst || [];
    for (let gi = groups.length - 1; gi >= 0; gi--) {
        const group = groups[gi];
        if (!group || typeof group !== "object") {
            continue;
        }
        if (group.type === "single") {
            const hash = group.chatItem?.lxmf_message?.hash;
            if (hash) {
                hashes.push(hash);
            }
            continue;
        }
        if (group.type === "imageGroup" && Array.isArray(group.items)) {
            for (let ii = group.items.length - 1; ii >= 0; ii--) {
                const hash = group.items[ii]?.lxmf_message?.hash;
                if (hash) {
                    hashes.push(hash);
                }
            }
        }
    }
    return hashes;
}

/**
 * Simulate incremental page prepends from the newest end (matches ConversationViewer).
 * pageSizesFromNewest: cumulative counts from the newest message backward.
 *
 * @param {unknown[]} allItemsOldestFirst
 * @param {number[]} pageSizesFromNewest
 * @param {(chatItem: unknown) => boolean} canMergeImageIntoImageStrip
 * @returns {boolean}
 */
export function incrementalPrependMatchesFullRebuild(
    allItemsOldestFirst,
    pageSizesFromNewest,
    canMergeImageIntoImageStrip
) {
    const items = allItemsOldestFirst || [];
    const n = items.length;
    let loaded = [];
    let cached = null;
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
    const incHashes = displayGroupHashesOldestFirst(cached);
    const fullHashes = displayGroupHashesOldestFirst(full);
    return incHashes.join("\u241e") === fullHashes.join("\u241e");
}
