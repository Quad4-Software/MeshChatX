// SPDX-License-Identifier: 0BSD

/**
 * Tracks destination hashes open in Messages panes for notification suppress/clear.
 */

import { EMITTER_EVENTS } from "./constants.js";
import { normalizeDestinationHash } from "./notificationPolicy.js";
import GlobalEmitter from "./GlobalEmitter";

const openHashes = new Set<string>();

const listeners = new Set<(hashes: string[]) => void>();

function notifyListeners(): void {
    const snapshot = listOpenDestinationHashes();
    for (const listener of listeners) {
        try {
            listener(snapshot);
        } catch (e) {
            console.error("activeConversationStore listener failed", e);
        }
    }
}

/** Replace the full set of open conversation destination hashes. */
export function setOpenDestinationHashes(hashes: Iterable<string> | null | undefined): void {
    const next = new Set<string>();
    if (hashes) {
        for (const h of hashes) {
            const n = normalizeDestinationHash(h);
            if (n) {
                next.add(n);
            }
        }
    }
    let changed = next.size !== openHashes.size;
    if (!changed) {
        for (const h of next) {
            if (!openHashes.has(h)) {
                changed = true;
                break;
            }
        }
    }
    if (!changed) {
        return;
    }
    openHashes.clear();
    for (const h of next) {
        openHashes.add(h);
    }
    notifyListeners();
}

export function addOpenDestinationHash(hash: string): void {
    const n = normalizeDestinationHash(hash);
    if (!n || openHashes.has(n)) {
        return;
    }
    openHashes.add(n);
    notifyListeners();
}

export function removeOpenDestinationHash(hash: string): void {
    const n = normalizeDestinationHash(hash);
    if (!n || !openHashes.has(n)) {
        return;
    }
    openHashes.delete(n);
    notifyListeners();
}

export function listOpenDestinationHashes(): string[] {
    return Array.from(openHashes);
}

export function hasOpenDestinationHash(hash: string | null | undefined): boolean {
    const n = normalizeDestinationHash(hash);
    return Boolean(n && openHashes.has(n));
}

export function subscribeOpenDestinationHashes(listener: (hashes: string[]) => void): () => void {
    if (typeof listener !== "function") {
        return () => {};
    }
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}

/** Test helper. */
export function clearOpenDestinationHashesForTests(): void {
    openHashes.clear();
    listeners.clear();
}

// Open panes belong to the active identity. After an identity switch the old
// destination hashes must not keep suppressing notifications for the new one.
GlobalEmitter.on(EMITTER_EVENTS.IDENTITY_SWITCHED, () => {
    if (openHashes.size === 0) {
        return;
    }
    openHashes.clear();
    notifyListeners();
});
