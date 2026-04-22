/**
 * Coordinate proximity threshold used by the map dedupe helpers. Two points
 * within this distance (in degrees) are considered "the same place" for the
 * purpose of collapsing duplicate markers.
 */
const NEARBY_DEGREE_THRESHOLD = 0.005;

function nearByDegrees(a, b) {
    return (
        Math.abs(a.latitude - b.latitude) < NEARBY_DEGREE_THRESHOLD &&
        Math.abs(a.longitude - b.longitude) < NEARBY_DEGREE_THRESHOLD
    );
}

/**
 * Deduplicate telemetry markers shown on the map.
 *
 * Markers with the same (case-insensitive) display name and which fall within
 * NEARBY_DEGREE_THRESHOLD of each other are collapsed to the freshest one.
 * Entries without a resolvable name are always kept.
 *
 * @param {Array} telemetryList - telemetry entries from the API.
 * @param {Object<string, object>} peers - lookup of peer details keyed by destination_hash.
 * @returns {Array} a filtered telemetry list with duplicates removed.
 */
export function dedupeTelemetryMarkersForMap(telemetryList, peers = {}) {
    if (!Array.isArray(telemetryList)) return [];
    const sorted = [...telemetryList].sort((a, b) => {
        const ta = a.updated_at ? new Date(a.updated_at).getTime() : (a.timestamp || 0) * 1000;
        const tb = b.updated_at ? new Date(b.updated_at).getTime() : (b.timestamp || 0) * 1000;
        return tb - ta;
    });
    const labelName = (t) => {
        const p = peers[t.destination_hash];
        return (p?.display_name || t.destination_hash?.substring(0, 8) || "").trim().toLowerCase();
    };
    const near = (a, b) => {
        const la = a.telemetry?.location;
        const lb = b.telemetry?.location;
        if (!la || !lb || la.latitude == null || lb.latitude == null) return false;
        return nearByDegrees(la, lb);
    };
    const out = [];
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

/**
 * Deduplicate discovered map nodes by name + proximity. Entries without a
 * name are always kept.
 *
 * @param {Array} nodes - discovered map nodes from the API.
 * @returns {Array} a filtered list with duplicates removed.
 */
export function dedupeDiscoveredMapNodes(nodes) {
    if (!Array.isArray(nodes)) return [];
    const sorted = [...nodes].sort((a, b) => (b.last_heard || 0) - (a.last_heard || 0));
    const norm = (n) => (n.name || "").trim().toLowerCase();
    const near = (a, b) => a && b && a.latitude != null && b.latitude != null && nearByDegrees(a, b);
    const out = [];
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
