// SPDX-License-Identifier: 0BSD

/**
 * In-process map of Electron Notification instances keyed by destination hash.
 * Extracted for unit tests without loading the full Electron main process.
 */

/** @type {Map<string, Set<{ close: () => void }>>} */
const byDestination = new Map();

/**
 * @param {string|null|undefined} destinationHash
 * @returns {string}
 */
export function normalizeNotifDestinationHash(destinationHash) {
    if (destinationHash == null) {
        return "";
    }
    return String(destinationHash).trim().toLowerCase();
}

/**
 * @param {string|null|undefined} destinationHash
 * @param {{ close: () => void }} notification
 */
export function trackMessageNotification(destinationHash, notification) {
    const key = normalizeNotifDestinationHash(destinationHash) || "__untagged__";
    let set = byDestination.get(key);
    if (!set) {
        set = new Set();
        byDestination.set(key, set);
    }
    set.add(notification);
}

/**
 * @param {string|null|undefined} destinationHash
 * @param {{ close: () => void }} notification
 */
export function untrackMessageNotification(destinationHash, notification) {
    const key = normalizeNotifDestinationHash(destinationHash) || "__untagged__";
    const set = byDestination.get(key);
    if (!set) {
        return;
    }
    set.delete(notification);
    if (set.size === 0) {
        byDestination.delete(key);
    }
}

/**
 * @param {string|null|undefined} destinationHash
 * @returns {number} closed count
 */
export function closeMessageNotificationsFor(destinationHash) {
    const key = normalizeNotifDestinationHash(destinationHash);
    if (!key) {
        return 0;
    }
    const set = byDestination.get(key);
    if (!set) {
        return 0;
    }
    let closed = 0;
    for (const n of Array.from(set)) {
        try {
            n.close();
            closed += 1;
        } catch {
            // ignore
        }
    }
    byDestination.delete(key);
    return closed;
}

/**
 * @returns {number} closed count
 */
export function closeAllMessageNotifications() {
    let closed = 0;
    for (const set of byDestination.values()) {
        for (const n of Array.from(set)) {
            try {
                n.close();
                closed += 1;
            } catch {
                // ignore
            }
        }
    }
    byDestination.clear();
    return closed;
}

/** Test helper. */
export function resetMessageNotificationTrackerForTests() {
    byDestination.clear();
}
