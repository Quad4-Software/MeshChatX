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
    if (entry.type === "dateDivider") {
        return 44;
    }
    if (entry.type === "imageGroup") {
        return 340;
    }
    const msg = entry.chatItem?.lxmf_message;
    const fields = msg?.fields;
    if (fields?.image && !fields?.file_attachments?.length && !fields?.audio) {
        return 280;
    }
    let height = 88;
    const content = (msg?.content || "").trim();
    if (content) {
        height += Math.min(160, Math.ceil(content.length / 40) * 18);
    }
    const fileCount = Array.isArray(fields?.file_attachments) ? fields.file_attachments.length : 0;
    if (fileCount > 0) {
        height += fileCount * 56;
    }
    if (fields?.audio) {
        height += 72;
    }
    if (fields?.telemetry || fields?.telemetry_stream || fields?.commands?.length) {
        height += 48;
    }
    return height;
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
        if (g.type === "dateDivider") {
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

/**
 * Keys for inbound groups appended at the tail of an already-live list.
 * The caller keeps a Set of keys it has seen; only brand-new keys inside
 * the last positions animate, so opening a conversation, loading older
 * history, and virtual-scroll remounts never play the entrance.
 *
 * @param {unknown[]} groupsOldestFirst
 * @param {Set<string>} knownKeys
 * @param {number} tailWindow
 * @returns {{ fresh: string[], nextKeys: Set<unknown> }}
 */
export function diffFreshInboundKeys(groupsOldestFirst, knownKeys, tailWindow = 6) {
    const fresh = [];
    const nextKeys = new Set();
    if (!Array.isArray(groupsOldestFirst)) {
        return { fresh, nextKeys };
    }
    const tailStart = Math.max(0, groupsOldestFirst.length - tailWindow);
    groupsOldestFirst.forEach((g, i) => {
        const key = g?.key;
        nextKeys.add(key);
        if (i < tailStart || knownKeys.has(key)) {
            return;
        }
        const item = g?.items?.[0] ?? g?.chatItem;
        if (item && item.is_outbound === false) {
            fresh.push(key);
        }
    });
    return { fresh, nextKeys };
}
