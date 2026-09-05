// SPDX-License-Identifier: 0BSD

import { MAX_CACHED_AUDIO_ATTACHMENTS } from "./constants.js";

const MAX_CACHED_AUDIO = MAX_CACHED_AUDIO_ATTACHMENTS;

export type AudioCacheEntry = { hash: string; objectUrl: string };

export function rememberAudioAttachment(
    order: string[],
    cache: Record<string, string>,
    hash: string,
    objectUrl: string
): { order: string[]; cache: Record<string, string> } {
    const nextCache = { ...cache, [hash]: objectUrl };
    const nextOrder = order.filter((h) => h !== hash).concat(hash);
    while (nextOrder.length > MAX_CACHED_AUDIO) {
        const drop = nextOrder.shift();
        if (drop && nextCache[drop]) {
            try {
                URL.revokeObjectURL(nextCache[drop]);
            } catch {
                /* ignore */
            }
            delete nextCache[drop];
        }
    }
    return { order: nextOrder, cache: nextCache };
}

export function clearAudioAttachmentCache(order: string[], cache: Record<string, string>): void {
    for (const hash of order) {
        const url = cache[hash];
        if (url) {
            try {
                URL.revokeObjectURL(url);
            } catch {
                /* ignore */
            }
        }
    }
}
