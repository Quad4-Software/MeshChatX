export const MIN_VIRTUAL_RELAY_ENTRIES = 150;

/**
 * Initial row height guess before measureElement runs (variable-height rows).
 * @param {unknown} entry
 * @returns {number}
 */
export function estimateRelayEntryHeight(entry) {
    if (!entry || typeof entry !== "object") {
        return 28;
    }
    if (entry.type === "dateDivider") {
        return 44;
    }
    if (entry.type === "presenceGroup") {
        return 28;
    }
    const text = typeof entry.msg?.text === "string" ? entry.msg.text : "";
    let height = 32;
    if (text) {
        const lines = text.split("\n").reduce((sum, line) => sum + Math.max(1, Math.ceil(line.length / 72)), 0);
        height += Math.max(0, lines - 1) * 20;
    }
    return height;
}

/**
 * Stable identity for a timeline entry, used both as the virtualizer
 * getItemKey and as the Vue row key. Keyed by content rather than index so a
 * prepend keeps each measurement and DOM node attached to its entry. Returns
 * an empty string when the entry has no derivable key; callers fall back to
 * the index for those.
 * @param {unknown} entry
 * @param {(msg: object) => string} keyFn
 * @returns {string}
 */
export function relayVirtualEntryKey(entry, keyFn) {
    if (!entry || typeof entry !== "object") {
        return "";
    }
    if (entry.type === "dateDivider") {
        return typeof entry.dayKey === "string" ? `date-${entry.dayKey}` : "";
    }
    if (entry.type === "presenceGroup") {
        return typeof entry.id === "string" && entry.id ? `presence-${entry.id}` : "";
    }
    if (entry.type === "unreadDivider") {
        return "unread-divider";
    }
    if (entry.type === "message" && entry.msg && typeof keyFn === "function") {
        return keyFn(entry.msg) || "";
    }
    return "";
}

/**
 * @param {unknown[]} entries
 * @param {string} key
 * @param {(msg: object) => string} keyFn
 * @returns {number}
 */
export function findRelayEntryIndexForMessageKey(entries, key, keyFn) {
    if (!entries?.length || !key || typeof keyFn !== "function") {
        return -1;
    }
    for (let i = 0; i < entries.length; i++) {
        const entry = entries[i];
        if (entry?.type === "message" && entry.msg && keyFn(entry.msg) === key) {
            return i;
        }
    }
    return -1;
}
