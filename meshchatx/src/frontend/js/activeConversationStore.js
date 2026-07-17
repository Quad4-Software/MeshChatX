// SPDX-License-Identifier: 0BSD

/**
 * Tracks destination hashes open in Messages panes for notification suppress/clear.
 */

import { normalizeDestinationHash } from "./notificationPolicy.js";

/** @type {Set<string>} */
const openHashes = new Set();

/** @type {Set<(hashes: string[]) => void>} */
const listeners = new Set();

function notifyListeners() {
    const snapshot = listOpenDestinationHashes();
    for (const listener of listeners) {
        try {
            listener(snapshot);
        } catch (e) {
            console.error("activeConversationStore listener failed", e);
        }
    }
}

/**
 * Replace the full set of open conversation destination hashes.
 * @param {Iterable<string>|string[]|null|undefined} hashes
 */
export function setOpenDestinationHashes(hashes) {
    const next = new Set();
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

/**
 * @param {string} hash
 */
export function addOpenDestinationHash(hash) {
    const n = normalizeDestinationHash(hash);
    if (!n || openHashes.has(n)) {
        return;
    }
    openHashes.add(n);
    notifyListeners();
}

/**
 * @param {string} hash
 */
export function removeOpenDestinationHash(hash) {
    const n = normalizeDestinationHash(hash);
    if (!n || !openHashes.has(n)) {
        return;
    }
    openHashes.delete(n);
    notifyListeners();
}

/**
 * @returns {string[]}
 */
export function listOpenDestinationHashes() {
    return Array.from(openHashes);
}

/**
 * @param {string|null|undefined} hash
 * @returns {boolean}
 */
export function hasOpenDestinationHash(hash) {
    const n = normalizeDestinationHash(hash);
    return Boolean(n && openHashes.has(n));
}

/**
 * @param {(hashes: string[]) => void} listener
 * @returns {() => void} unsubscribe
 */
export function subscribeOpenDestinationHashes(listener) {
    if (typeof listener !== "function") {
        return () => {};
    }
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}

/** Test helper. */
export function clearOpenDestinationHashesForTests() {
    openHashes.clear();
    listeners.clear();
}
