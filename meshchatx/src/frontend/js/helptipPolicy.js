// SPDX-License-Identifier: 0BSD

const THROTTLE_MS = 5 * 60 * 1000;
const PEER_HELPTIP_COOLDOWN_MS = 30 * 1000;
const MAX_TRACKED_ENTRIES = 500;
const lastShownAt = new Map();
const lastPeerHelptipAt = new Map();

function prune(map, windowMs, now) {
    for (const [key, ts] of map) {
        if (now - ts >= windowMs) {
            map.delete(key);
        }
    }
    while (map.size > MAX_TRACKED_ENTRIES) {
        map.delete(map.keys().next().value);
    }
}

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
    prune(lastShownAt, THROTTLE_MS, now);
    return true;
}

/**
 * @param {string} peerHash
 * @param {number} [now]
 */
export function shouldShowHelptipForPeer(peerHash, now = Date.now()) {
    const key = (peerHash || "").toLowerCase();
    const last = lastPeerHelptipAt.get(key);
    return last == null || now - last >= PEER_HELPTIP_COOLDOWN_MS;
}

/**
 * @param {string} peerHash
 * @param {number} [now]
 */
export function recordHelptipShownForPeer(peerHash, now = Date.now()) {
    lastPeerHelptipAt.set((peerHash || "").toLowerCase(), now);
    prune(lastPeerHelptipAt, PEER_HELPTIP_COOLDOWN_MS, now);
}

/**
 * @param {string} peerHash
 */
export function deliveryHelptipToastKey(peerHash) {
    return `delivery-helptip:${(peerHash || "").toLowerCase()}`;
}

export function resetHelptipPolicyForTests() {
    lastShownAt.clear();
    lastPeerHelptipAt.clear();
}
