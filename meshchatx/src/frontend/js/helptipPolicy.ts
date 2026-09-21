// SPDX-License-Identifier: 0BSD

const THROTTLE_MS = 5 * 60 * 1000;
const PEER_HELPTIP_COOLDOWN_MS = 30 * 1000;
const MAX_TRACKED_ENTRIES = 500;
const lastShownAt = new Map<string, number>();
const lastPeerHelptipAt = new Map<string, number>();

function prune(map: Map<string, number>, windowMs: number, now: number): void {
    for (const [key, ts] of map) {
        if (now - ts >= windowMs) {
            map.delete(key);
        }
    }
    while (map.size > MAX_TRACKED_ENTRIES) {
        const oldest = map.keys().next().value;
        if (oldest === undefined) break;
        map.delete(oldest);
    }
}

export function shouldShowDeliveryHelptips(config: Record<string, unknown> | null | undefined): boolean {
    return config?.delivery_helptips_enabled !== false;
}

export function helptipDedupeKey(peerHash: string, tipId: string): string {
    return `${(peerHash || "").toLowerCase()}:${tipId}`;
}

export function shouldShowHelptip(peerHash: string, tipId: string): boolean {
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

export function shouldShowHelptipForPeer(peerHash: string, now: number = Date.now()): boolean {
    const key = (peerHash || "").toLowerCase();
    const last = lastPeerHelptipAt.get(key);
    return last == null || now - last >= PEER_HELPTIP_COOLDOWN_MS;
}

export function recordHelptipShownForPeer(peerHash: string, now: number = Date.now()): void {
    lastPeerHelptipAt.set((peerHash || "").toLowerCase(), now);
    prune(lastPeerHelptipAt, PEER_HELPTIP_COOLDOWN_MS, now);
}

export function deliveryHelptipToastKey(peerHash: string): string {
    return `delivery-helptip:${(peerHash || "").toLowerCase()}`;
}

export function resetHelptipPolicyForTests(): void {
    lastShownAt.clear();
    lastPeerHelptipAt.clear();
}
