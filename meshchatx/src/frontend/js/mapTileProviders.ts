/** Canonical default basemap (OpenStreetMap raster). */
export const DEFAULT_TILE_SERVER_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

/** Raster basemap providers tried in order when tiles fail to load. */
export const RASTER_TILE_PROVIDER_ORDER = ["osm", "openfreemap"] as const;

export type RasterTileProviderId = string;

export const TILE_PROVIDER_URLS: Record<string, string> = {
    osm: DEFAULT_TILE_SERVER_URL,
    openfreemap: "https://tiles.openfreemap.org/styles/bright",
    "carto-dark": "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    "carto-voyager": "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    "carto-light": "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
};

type TileUrlParts = {
    host: string;
    path: string;
};

/**
 * Parse tile template URLs for hostname and pathname.
 * Leaflet placeholders like {z} are replaced so URL() accepts the string.
 */
function tileUrlParts(tileServerUrl: string | null | undefined): TileUrlParts {
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

export function detectRasterTileProviderId(tileServerUrl: string | null | undefined): string | null {
    const { host, path } = tileUrlParts(tileServerUrl);
    if (!host) {
        return null;
    }
    if (host === "tiles.openfreemap.org") {
        return "openfreemap";
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

export function nextRasterTileProviderId(
    currentId: string | null | undefined,
    attemptedIds: string[] = []
): string | null {
    const order = RASTER_TILE_PROVIDER_ORDER;
    const start = currentId ? order.indexOf(currentId as (typeof order)[number]) : -1;
    for (let i = 1; i <= order.length; i++) {
        const idx = (start + i) % order.length;
        const id = order[idx];
        if (!attemptedIds.includes(id)) {
            return id;
        }
    }
    return null;
}
