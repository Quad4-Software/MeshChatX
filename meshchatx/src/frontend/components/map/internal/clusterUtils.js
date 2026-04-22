/**
 * Pure helpers for the map's marker clustering logic.
 *
 * These functions intentionally avoid any direct dependency on Vue or
 * OpenLayers internals so they can be unit-tested in isolation. They expect
 * "feature" objects exposing a minimal subset of the OpenLayers Feature API:
 *   - feature.get(key) -> any
 *   - feature.getGeometry() -> { getCoordinates(): [x, y] } | null
 */

/**
 * Compute the diagonal length of an extent in map units. Used to detect
 * degenerate (zero-area) clusters where every contained marker shares the
 * exact same coordinate.
 *
 * @param {Array<number>|null|undefined} extent - [minX, minY, maxX, maxY]
 * @returns {number} 0 for empty or non-finite extents, the diagonal length
 *                   otherwise.
 */
export function extentDiagonal(extent) {
    if (!extent || extent.length < 4) return 0;
    const [minX, minY, maxX, maxY] = extent;
    if (![minX, minY, maxX, maxY].every((v) => Number.isFinite(v))) return 0;
    const dx = maxX - minX;
    const dy = maxY - minY;
    return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Resolve the original (unclustered) coordinate of a feature, falling back to
 * its geometry's current coordinates when no `originalCoord` was tracked.
 *
 * @param {object} feature
 * @returns {Array<number>|null}
 */
export function getFeatureCoord(feature) {
    if (!feature || typeof feature.get !== "function") return null;
    const original = feature.get("originalCoord");
    if (original) return original;
    if (typeof feature.getGeometry !== "function") return null;
    const geom = feature.getGeometry();
    return geom && typeof geom.getCoordinates === "function" ? geom.getCoordinates() : null;
}

/**
 * Build a normalised summary of a cluster suitable for the cluster details
 * overlay. Each entry exposes the source feature plus lightweight metadata
 * (kind, label, identifier, coord).
 *
 * @param {object|null} feature - cluster feature with a "clusterItems" prop.
 * @returns {Array<object>} normalised summary entries.
 */
export function buildClusterItems(feature) {
    if (!feature) return [];
    const rawItems = feature.get("clusterItems") || [];
    const summary = [];
    for (const item of rawItems) {
        if (!item) continue;
        const coord = getFeatureCoord(item);
        const telemetry = item.get("telemetry");
        const peer = item.get("peer");
        const discovered = item.get("discovered");
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
