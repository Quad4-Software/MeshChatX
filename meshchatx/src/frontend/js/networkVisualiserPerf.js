// SPDX-License-Identifier: 0BSD AND MIT

export const VIZ_ANNOUNCE_ASPECTS = ["lxmf.delivery", "nomadnetwork.node"];

export const ANNOUNCE_HASH_CHUNK_SIZE = 500;

/**
 * @param {unknown[]} pathTable
 * @param {number|null|undefined} hopMax
 * @returns {string[]}
 */
export function pathHashesWithinHopFilter(pathTable, hopMax) {
    if (!Array.isArray(pathTable) || pathTable.length === 0) {
        return [];
    }
    const out = new Set();
    for (const entry of pathTable) {
        if (!entry || typeof entry !== "object") {
            continue;
        }
        const hops = entry.hops;
        if (hops == null) {
            continue;
        }
        if (hopMax != null && hops > hopMax) {
            continue;
        }
        const hash = entry.hash;
        if (typeof hash === "string" && hash) {
            out.add(hash);
        }
    }
    return Array.from(out);
}

/**
 * Collapse deferred icon work so each unique cacheKey is painted once.
 * @param {unknown[]} queue
 * @returns {{ cacheKey: string, nodeIds: string[], iconName: string, fg: string, bg: string, size: number, generation: number }[]}
 */
export function dedupeIconQueueEntries(queue) {
    if (!Array.isArray(queue) || queue.length === 0) {
        return [];
    }
    const byKey = new Map();
    for (const item of queue) {
        if (!item || typeof item !== "object" || !item.cacheKey || !item.nodeId) {
            continue;
        }
        let bucket = byKey.get(item.cacheKey);
        if (!bucket) {
            bucket = {
                cacheKey: item.cacheKey,
                nodeIds: [],
                iconName: item.iconName,
                fg: item.fg,
                bg: item.bg,
                size: item.size,
                generation: item.generation,
            };
            byKey.set(item.cacheKey, bucket);
        }
        if (!bucket.nodeIds.includes(item.nodeId)) {
            bucket.nodeIds.push(item.nodeId);
        }
    }
    return Array.from(byKey.values());
}

/**
 * Parallel path/announce fetch concurrency scaled to hardware.
 * @returns {number}
 */
export function pickAdaptiveFetchConcurrency() {
    const cores = (typeof navigator !== "undefined" && navigator.hardwareConcurrency) || 4;
    if (cores <= 2) return 2;
    if (cores <= 4) return 3;
    if (cores <= 6) return 4;
    return 6;
}
