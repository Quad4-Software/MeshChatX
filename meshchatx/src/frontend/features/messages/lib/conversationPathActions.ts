// SPDX-License-Identifier: 0BSD

/**
 * Pathfinder / stamp / signal helpers. Heavy RNS calls stay on the viewer shell via window.api.
 */

export type PeerPathSnapshot = {
    hops?: number | null;
    next_hop?: string | null;
    interface_name?: string | null;
    updated_at?: number | null;
};

export function emptyPeerPathSnapshot(): PeerPathSnapshot {
    return { hops: null, next_hop: null, interface_name: null, updated_at: null };
}

export function pathHopsLabel(snapshot: PeerPathSnapshot | null | undefined): string {
    if (snapshot?.hops == null) {
        return "";
    }
    return String(snapshot.hops);
}
