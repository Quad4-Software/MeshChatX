// SPDX-License-Identifier: 0BSD

import { isLocalMapServiceUrl } from "../../../js/mapLocalUrl.js";

export const DEFAULT_OSM_RASTER = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
export const OPENFREEMAP_DEFAULT_STYLE = "https://tiles.openfreemap.org/styles/liberty";

const KNOWN_ONLINE_PATTERNS = [
    "openstreetmap.org",
    "openfreemap.org",
    "cartocdn.com",
    "thunderforest.com",
    "stamen.com",
    "google.com",
    "mapbox.com",
    "arcgisonline.com",
    "wmflabs.org",
    "maptiler.com",
];

export function isLocalUrl(url: string): boolean {
    return isLocalMapServiceUrl(url, typeof window !== "undefined" ? window.location.origin : "");
}

export function isDefaultOnlineUrl(url?: string | null): boolean {
    if (!url) return false;
    const lower = url.toLowerCase();
    return KNOWN_ONLINE_PATTERNS.some((pattern) => lower.includes(pattern));
}

export function isOpenFreeMapStyleUrl(url?: string | null): boolean {
    return typeof url === "string" && url.includes("tiles.openfreemap.org/styles/");
}

export function isKnownDefaultBasemapUrl(url?: string | null): boolean {
    const normalized = (url || "").trim();
    return normalized === OPENFREEMAP_DEFAULT_STYLE || normalized === DEFAULT_OSM_RASTER;
}

export function resolveRasterTileUrl(url?: string | null): string {
    const normalized = (url || DEFAULT_OSM_RASTER).trim();
    if (isOpenFreeMapStyleUrl(normalized)) {
        return DEFAULT_OSM_RASTER;
    }
    return normalized;
}

export function usesOfflineMbtilesRaster(offlineEnabled: boolean, tileServerUrl?: string | null): boolean {
    if (!offlineEnabled) return false;
    const customTileUrl = tileServerUrl || DEFAULT_OSM_RASTER;
    const isCustomLocal = isLocalUrl(customTileUrl);
    if (isCustomLocal) return false;
    const isDefaultOnline = isDefaultOnlineUrl(customTileUrl);
    if (isDefaultOnline) return true;
    if (!isKnownDefaultBasemapUrl(customTileUrl)) return false;
    return true;
}

export function parseZxyFromTileUrl(url: string): { z: number; x: number; y: number } | null {
    const match = url.match(/\/(\d{1,8})\/(\d{1,8})\/(\d{1,8})(?:\.[a-zA-Z0-9]+)?(?:\?|$)/);
    if (!match) return null;
    return {
        z: parseInt(match[1], 10),
        x: parseInt(match[2], 10),
        y: parseInt(match[3], 10),
    };
}

export function expandRasterTileUrlTemplates(template: string, z: number, x: number, y: number): string[] {
    const subdomains = ["a", "b", "c"];
    const hasSubdomain = template.includes("{s}");
    const templatesToUse = hasSubdomain ? subdomains.map((s) => template.replace("{s}", s)) : [template];
    return templatesToUse.map((t) => t.replace("{z}", String(z)).replace("{x}", String(x)).replace("{y}", String(y)));
}

export function offlineTileCacheLookupUrls(tileCoord: number[], primarySrc: string, tileServerUrl?: string): string[] {
    const urls = new Set<string>();
    if (primarySrc) {
        urls.add(primarySrc);
    }
    if (tileCoord && tileCoord.length >= 3) {
        const [z, x, yRaw] = tileCoord;
        const y = Math.max(0, -yRaw - 1);
        const resolvedTemplate = resolveRasterTileUrl(tileServerUrl);
        for (const u of expandRasterTileUrlTemplates(resolvedTemplate, z, x, y)) {
            urls.add(u);
        }
        for (const u of expandRasterTileUrlTemplates(DEFAULT_OSM_RASTER, z, x, y)) {
            urls.add(u);
        }
    }
    return Array.from(urls);
}

export function lonToTile(lon: number, zoom: number): number {
    return Math.floor(((lon + 180) / 360) * Math.pow(2, zoom));
}

export function latToTile(lat: number, zoom: number): number {
    const latRad = (lat * Math.PI) / 180;
    return Math.floor(((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * Math.pow(2, zoom));
}

export function tileProviderLabel(providerId: string): string {
    const labels: Record<string, string> = {
        osm: "OpenStreetMap",
        openfreemap: "OpenFreeMap",
        "carto-dark": "CARTO Dark",
        "carto-voyager": "CARTO Voyager",
        "carto-light": "CARTO Light",
    };
    return labels[providerId] || providerId;
}
