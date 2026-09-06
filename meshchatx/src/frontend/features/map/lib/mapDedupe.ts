// SPDX-License-Identifier: 0BSD

import type { DiscoveredMapNode, MapPeer, TelemetryPeer } from "./types.js";

interface Coordinate {
    latitude: number;
    longitude: number;
}

const NEARBY_DEGREE_THRESHOLD = 0.005;

function nearByDegrees(a: Coordinate, b: Coordinate): boolean {
    return (
        Math.abs(a.latitude - b.latitude) < NEARBY_DEGREE_THRESHOLD &&
        Math.abs(a.longitude - b.longitude) < NEARBY_DEGREE_THRESHOLD
    );
}

export function dedupeTelemetryMarkersForMap(
    telemetryList: TelemetryPeer[],
    peers: Record<string, MapPeer> = {}
): TelemetryPeer[] {
    if (!Array.isArray(telemetryList)) return [];
    const sorted = [...telemetryList].sort((a, b) => {
        const ta = a.updated_at ? new Date(a.updated_at).getTime() : (a.timestamp || 0) * 1000;
        const tb = b.updated_at ? new Date(b.updated_at).getTime() : (b.timestamp || 0) * 1000;
        return tb - ta;
    });
    const labelName = (t: TelemetryPeer): string => {
        const p = t.destination_hash ? peers[t.destination_hash] : undefined;
        return (p?.display_name || t.destination_hash?.substring(0, 8) || "").trim().toLowerCase();
    };
    const near = (a: TelemetryPeer, b: TelemetryPeer): boolean => {
        const la = a.telemetry?.location;
        const lb = b.telemetry?.location;
        if (!la || !lb || la.latitude == null || lb.latitude == null) return false;
        return nearByDegrees(la, lb);
    };
    const out: TelemetryPeer[] = [];
    for (const t of sorted) {
        const nn = labelName(t);
        if (!nn) {
            out.push(t);
            continue;
        }
        if (out.some((k) => labelName(k) === nn && near(k, t))) continue;
        out.push(t);
    }
    return out;
}

export function dedupeDiscoveredMapNodes(nodes: DiscoveredMapNode[]): DiscoveredMapNode[] {
    if (!Array.isArray(nodes)) return [];
    const sorted = [...nodes].sort((a, b) => (b.last_heard || 0) - (a.last_heard || 0));
    const norm = (n: DiscoveredMapNode): string => (n.name || "").trim().toLowerCase();
    const near = (a: DiscoveredMapNode, b: DiscoveredMapNode): boolean =>
        Boolean(
            a &&
            b &&
            a.latitude != null &&
            b.latitude != null &&
            a.longitude != null &&
            b.longitude != null &&
            nearByDegrees(
                { latitude: a.latitude, longitude: a.longitude },
                { latitude: b.latitude, longitude: b.longitude }
            )
        );
    const out: DiscoveredMapNode[] = [];
    for (const n of sorted) {
        const nn = norm(n);
        if (!nn) {
            out.push(n);
            continue;
        }
        if (out.some((k) => norm(k) === nn && near(k, n))) continue;
        out.push(n);
    }
    return out;
}
