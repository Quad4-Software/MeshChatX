export const MIN_VIRTUAL_DISPLAY_GROUPS = 48;

/**
 * Display groups from {@link selectedPeerChatDisplayGroups} are newest-first.
 * Virtual + normal document flow use oldest at the top (index 0).
 * @param {unknown[]} displayGroups
 * @returns {unknown[]}
 */
export function displayGroupsOldestFirst(displayGroups) {
    if (!displayGroups?.length) {
        return [];
    }
    return displayGroups.slice().reverse();
}

/**
 * Initial row height guess before measureElement runs (variable-height rows).
 * @param {unknown} entry
 * @returns {number}
 */
export function estimateGroupHeight(entry) {
    if (!entry || typeof entry !== "object") {
        return 96;
    }
    if (entry.type === "imageGroup") {
        return 340;
    }
    return 120;
}

/**
 * @param {unknown[]} groupsOldestFirst
 * @param {string} hash
 * @returns {number}
 */
export function findDisplayGroupIndexForMessageHash(groupsOldestFirst, hash) {
    if (!groupsOldestFirst?.length || !hash) {
        return -1;
    }
    for (let i = 0; i < groupsOldestFirst.length; i++) {
        const g = groupsOldestFirst[i];
        if (!g || typeof g !== "object") {
            continue;
        }
        if (g.type === "imageGroup" && Array.isArray(g.items)) {
            if (g.items.some((it) => it?.lxmf_message?.hash === hash)) {
                return i;
            }
        } else if (g.type === "single" && g.chatItem?.lxmf_message?.hash === hash) {
            return i;
        }
    }
    return -1;
}
