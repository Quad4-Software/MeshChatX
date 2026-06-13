/** Raster basemap providers tried in order when tiles fail to load. */

export const RASTER_TILE_PROVIDER_ORDER = ["osm", "openfreemap"];

export const TILE_PROVIDER_URLS = {
    openfreemap: "https://tiles.openfreemap.org/styles/bright",
    osm: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "carto-dark": "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    "carto-voyager": "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    "carto-light": "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
};

export function detectRasterTileProviderId(tileServerUrl) {
    const u = (tileServerUrl || "").toLowerCase();
    if (u.includes("tiles.openfreemap.org")) return "openfreemap";
    if (u.includes("openstreetmap.org")) return "osm";
    if (u.includes("basemaps.cartocdn.com/dark_all")) return "carto-dark";
    if (u.includes("rastertiles/voyager")) return "carto-voyager";
    if (u.includes("basemaps.cartocdn.com/light_all")) return "carto-light";
    return null;
}

export function nextRasterTileProviderId(currentId, attemptedIds = []) {
    const order = RASTER_TILE_PROVIDER_ORDER;
    const start = currentId ? order.indexOf(currentId) : -1;
    for (let i = 1; i <= order.length; i++) {
        const idx = (start + i) % order.length;
        const id = order[idx];
        if (!attemptedIds.includes(id)) {
            return id;
        }
    }
    return null;
}
