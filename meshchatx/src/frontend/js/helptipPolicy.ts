// SPDX-License-Identifier: 0BSD

const THROTTLE_MS = 5 * 60 * 1000;
const lastShownAt = new Map();

/**
 * @param {object | null | undefined} config
 */
export function shouldShowDeliveryHelptips(config) {
    return config?.delivery_helptips_enabled !== false;
}

/**
 * @param {string} peerHash
 * @param {string} tipId
 */
export function helptipDedupeKey(peerHash, tipId) {
    return `${(peerHash || "").toLowerCase()}:${tipId}`;
}

/**
 * @param {string} peerHash
 * @param {string} tipId
 */
export function shouldShowHelptip(peerHash, tipId) {
    const key = helptipDedupeKey(peerHash, tipId);
    const now = Date.now();
    const last = lastShownAt.get(key);
    if (last != null && now - last < THROTTLE_MS) {
        return false;
    }
    lastShownAt.set(key, now);
    return true;
}

/**
 * @param {string} peerHash
 */
export function deliveryHelptipToastKey(peerHash) {
    return `delivery-helptip:${(peerHash || "").toLowerCase()}`;
}

export function resetHelptipPolicyForTests() {
    lastShownAt.clear();
}
