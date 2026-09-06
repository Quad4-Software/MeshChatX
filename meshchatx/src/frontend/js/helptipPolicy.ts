// SPDX-License-Identifier: 0BSD

const THROTTLE_MS = 5 * 60 * 1000;
const lastShownAt = new Map<string, number>();

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
    return true;
}

export function deliveryHelptipToastKey(peerHash: string): string {
    return `delivery-helptip:${(peerHash || "").toLowerCase()}`;
}

export function resetHelptipPolicyForTests(): void {
    lastShownAt.clear();
}
