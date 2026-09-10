/** Canonical default basemap (OpenStreetMap raster). */
export const DEFAULT_TILE_SERVER_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

/** Raster basemap providers tried in order when tiles fail to load. */
export const RASTER_TILE_PROVIDER_ORDER = ["osm", "carto-dark", "carto-voyager", "carto-light"];

export const TILE_PROVIDER_URLS = {
    osm: DEFAULT_TILE_SERVER_URL,
    openfreemap: "https://tiles.openfreemap.org/styles/bright",
    "carto-dark": "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    "carto-voyager": "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    "carto-light": "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
};

const OSM_ATTR =
    '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors';
const CARTO_ATTR = `${OSM_ATTR} © <a href="https://carto.com/attributions" target="_blank" rel="noopener noreferrer">CARTO</a>`;

/** Required attribution HTML for the known tile providers. */
export const TILE_PROVIDER_ATTRIBUTIONS = {
    osm: OSM_ATTR,
    openfreemap: `© <a href="https://openfreemap.org" target="_blank" rel="noopener noreferrer">OpenFreeMap</a> ${OSM_ATTR}`,
    "carto-dark": CARTO_ATTR,
    "carto-voyager": CARTO_ATTR,
    "carto-light": CARTO_ATTR,
};

/**
 * Parse tile template URLs for hostname and pathname.
 * Leaflet placeholders like {z} are replaced so URL() accepts the string.
 * @param {string} tileServerUrl
 * @returns {{ host: string, path: string }}
 */
function tileUrlParts(tileServerUrl) {
    const raw = String(tileServerUrl || "").trim();
    if (!raw) {
        return { host: "", path: "" };
    }
    try {
        const normalized = raw.replace(/\{[^}]+\}/g, "0");
        const parsed = new URL(normalized);
        return {
            host: String(parsed.hostname || "").toLowerCase(),
            path: String(parsed.pathname || "").toLowerCase(),
        };
    } catch {
        return { host: "", path: "" };
    }
}

export function detectRasterTileProviderId(tileServerUrl) {
    const { host, path } = tileUrlParts(tileServerUrl);
    if (!host) {
        return null;
    }
    if (host === "tile.openstreetmap.org" || host.endsWith(".openstreetmap.org")) {
        return "osm";
    }
    if (host === "basemaps.cartocdn.com") {
        if (path.includes("/dark_all")) {
            return "carto-dark";
        }
        if (path.includes("/rastertiles/voyager")) {
            return "carto-voyager";
        }
        if (path.includes("/light_all")) {
            return "carto-light";
        }
    }
    return null;
}

/**
 * Attribution HTML for a tile server URL, or null when the provider is unknown.
 * @param {string} tileServerUrl
 * @returns {string | null}
 */
export function attributionForTileUrl(tileServerUrl) {
    // openfreemap serves style JSON, not raster tiles, so it is intentionally
    // not part of detectRasterTileProviderId; match its host here instead.
    const { host } = tileUrlParts(tileServerUrl);
    if (host === "tiles.openfreemap.org" || host.endsWith(".openfreemap.org")) {
        return TILE_PROVIDER_ATTRIBUTIONS.openfreemap;
    }
    const id = detectRasterTileProviderId(tileServerUrl);
    return id ? (TILE_PROVIDER_ATTRIBUTIONS[id] ?? null) : null;
}

export function nextRasterTileProviderId(currentId, attemptedIds = []) {
    const order = RASTER_TILE_PROVIDER_ORDER;
    const start = currentId ? order.indexOf(currentId) : -1;
    const attempted = new Set(attemptedIds);
    if (currentId && start >= 0) {
        attempted.add(currentId);
    }
    for (let i = 1; i <= order.length; i++) {
        const idx = (start + i) % order.length;
        const id = order[idx];
        if (!attempted.has(id)) {
            return id;
        }
    }
    return null;
}
