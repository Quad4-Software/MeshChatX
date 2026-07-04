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
    const text = typeof entry.msg?.text === "string" ? entry.msg.text : "";
    let height = 28;
    if (text) {
        height += Math.ceil(text.length / 80) * 18;
    }
    return height;
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
