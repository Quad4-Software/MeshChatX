// SPDX-License-Identifier: 0BSD

interface FeatureLike {
    get(key: string): any;
    getGeometry?(): {
        getCoordinates?(): number[];
    } | null;
}

interface ClusterCandidate {
    coord: number[];
    clusterable?: boolean;
    [key: string]: unknown;
}

export function extentDiagonal(extent: number[] | null | undefined): number {
    if (!extent || extent.length < 4) return 0;
    const [minX, minY, maxX, maxY] = extent;
    if (![minX, minY, maxX, maxY].every((v) => Number.isFinite(v))) return 0;
    const dx = maxX - minX;
    const dy = maxY - minY;
    return Math.sqrt(dx * dx + dy * dy);
}

export function getFeatureCoord(feature: FeatureLike | null | undefined): number[] | null {
    if (!feature || typeof feature.get !== "function") return null;
    const original = feature.get("originalCoord");
    if (original) return original;
    if (typeof feature.getGeometry !== "function") return null;
    const geom = feature.getGeometry();
    return geom && typeof geom.getCoordinates === "function" ? geom.getCoordinates() : null;
}

export function buildClusterItems(feature: FeatureLike | null): Array<{
    feature: FeatureLike;
    kind: string;
    label: string;
    identifier: string;
    iconKey: Record<string, any> | null;
    coord: number[] | null;
    telemetry: Record<string, any> | null;
    peer: Record<string, any> | null;
    discovered: Record<string, any> | null;
}> {
    if (!feature) return [];
    const rawItems = (feature.get("clusterItems") || []) as FeatureLike[];
    const summary: Array<{
        feature: FeatureLike;
        kind: string;
        label: string;
        identifier: string;
        iconKey: Record<string, any> | null;
        coord: number[] | null;
        telemetry: Record<string, any> | null;
        peer: Record<string, any> | null;
        discovered: Record<string, any> | null;
    }> = [];
    for (const item of rawItems) {
        if (!item) continue;
        const coord = getFeatureCoord(item);
        const telemetry = item.get("telemetry") as Record<string, any> | null;
        const peer = item.get("peer") as Record<string, any> | null;
        const discovered = item.get("discovered") as Record<string, any> | null;
        let kind = "unknown";
        let label = "Unknown";
        let identifier = "";
        let iconKey = null;
        if (telemetry) {
            kind = "telemetry";
            label = peer?.display_name || (telemetry.destination_hash || "").substring(0, 8) || "Peer";
            identifier = telemetry.destination_hash || "";
        } else if (discovered) {
            kind = "discovered";
            label = discovered.name || "Discovered Interface";
            identifier = discovered.interface || discovered.via || "";
            iconKey = discovered;
        }
        summary.push({ feature: item, kind, label, identifier, iconKey, coord, telemetry, peer, discovered });
    }
    return summary;
}

export function gridClusterCandidates(candidates: ClusterCandidate[], cellSize: number): ClusterCandidate[][] {
    const size = Number.isFinite(cellSize) && cellSize > 0 ? cellSize : 1;
    const cells = new Map<string, ClusterCandidate[]>();
    const singles: ClusterCandidate[][] = [];
    for (const c of candidates || []) {
        if (!c || !Array.isArray(c.coord) || c.coord.length < 2) {
            continue;
        }
        if (c.clusterable === false) {
            singles.push([c]);
            continue;
        }
        const gx = Math.floor(c.coord[0] / size);
        const gy = Math.floor(c.coord[1] / size);
        const key = `${gx}:${gy}`;
        let arr = cells.get(key);
        if (!arr) {
            arr = [];
            cells.set(key, arr);
        }
        arr.push(c);
    }
    return [...cells.values(), ...singles];
}
