// SPDX-License-Identifier: 0BSD

// Short-lived cache for the first page of conversation history. Sidebar rows
// warm it on hover/focus so opening a conversation skips the network round trip.
const PREFETCH_TTL_MS = 10000;

const cache = new Map();

export function prefetchConversationFirstPage(api, peerHash, pageSize) {
    if (!api || !peerHash || !pageSize) {
        return;
    }
    const key = String(peerHash).toLowerCase();
    const existing = cache.get(key);
    if (existing && Date.now() - existing.ts < PREFETCH_TTL_MS) {
        return;
    }
    const promise = api
        .get(`/api/v1/lxmf-messages/conversation/${peerHash}`, {
            params: { count: pageSize, order: "desc" },
        })
        .catch(() => null);
    cache.set(key, { ts: Date.now(), promise });
}

export function takeConversationPrefetch(peerHash) {
    const key = String(peerHash).toLowerCase();
    const entry = cache.get(key);
    if (!entry) {
        return null;
    }
    cache.delete(key);
    if (Date.now() - entry.ts >= PREFETCH_TTL_MS) {
        return null;
    }
    return entry.promise;
}
