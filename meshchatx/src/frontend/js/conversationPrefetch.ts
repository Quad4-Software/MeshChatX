// SPDX-License-Identifier: 0BSD

// Short-lived cache for the first page of conversation history. Sidebar rows
// warm it on hover/focus so opening a conversation skips the network round
// trip, and the viewer stashes each loaded first page so re-opening a peer
// paints instantly while the resync catches up in the background.
import { apiPath } from "./constants.js";

const PREFETCH_TTL_MS = 10000;
const STASH_TTL_MS = 5 * 60 * 1000;
const MAX_ENTRIES = 20;

interface PrefetchEntry {
    ts: number;
    ttl: number;
    promise: Promise<unknown>;
}

interface ApiLike {
    get(url: string, options?: { params?: Record<string, unknown> }): Promise<unknown>;
}

const cache = new Map<string, PrefetchEntry>();

function evictExpired() {
    const now = Date.now();
    for (const [key, entry] of cache) {
        if (now - entry.ts >= entry.ttl) {
            cache.delete(key);
        }
    }
    while (cache.size > MAX_ENTRIES) {
        const oldest = cache.keys().next().value;
        if (oldest === undefined) {
            break;
        }
        cache.delete(oldest);
    }
}

export function prefetchConversationFirstPage(api: ApiLike | null | undefined, peerHash: unknown, pageSize: number) {
    if (!api || !peerHash || !pageSize) {
        return;
    }
    const key = String(peerHash).toLowerCase();
    const existing = cache.get(key);
    if (existing && Date.now() - existing.ts < existing.ttl) {
        return;
    }
    const promise = api
        .get(apiPath(`/lxmf-messages/conversation/${peerHash}`), {
            params: { count: pageSize, order: "desc" },
        })
        .catch(() => null);
    cache.set(key, { ts: Date.now(), ttl: PREFETCH_TTL_MS, promise });
    evictExpired();
}

export function stashConversationFirstPage(peerHash: unknown, data: unknown) {
    if (!peerHash || !data) {
        return;
    }
    const key = String(peerHash).toLowerCase();
    cache.set(key, {
        ts: Date.now(),
        ttl: STASH_TTL_MS,
        promise: Promise.resolve({ data }),
    });
    evictExpired();
}

export function clearConversationPrefetchCache() {
    cache.clear();
}

export function takeConversationPrefetch(peerHash: unknown): Promise<unknown> | null {
    const key = String(peerHash).toLowerCase();
    const entry = cache.get(key);
    if (!entry) {
        return null;
    }
    cache.delete(key);
    if (Date.now() - entry.ts >= entry.ttl) {
        return null;
    }
    return entry.promise;
}
