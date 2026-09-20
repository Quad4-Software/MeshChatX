// @ts-check

/**
 * Telemetry location payloads come from peers over the wire. Sideband-style
 * dicts can carry a location object with missing or non-numeric coordinates,
 * so guards must run before calling toFixed or feeding a map view.
 *
 * @param {unknown} location
 * @returns {{ lat: number, lon: number } | null}
 */
export function telemetryLocationCoords(location) {
    if (!location || typeof location !== "object") {
        return null;
    }
    const lat = Number(/** @type {Record<string, unknown>} */ (location).latitude);
    const lon = Number(/** @type {Record<string, unknown>} */ (location).longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        return null;
    }
    return { lat, lon };
}

/**
 * Display string for a telemetry location, or "" when coords are unusable.
 * @param {unknown} location
 * @returns {string}
 */
export function formatTelemetryLocationCoords(location) {
    const coords = telemetryLocationCoords(location);
    return coords ? `${coords.lat.toFixed(6)}, ${coords.lon.toFixed(6)}` : "";
}
