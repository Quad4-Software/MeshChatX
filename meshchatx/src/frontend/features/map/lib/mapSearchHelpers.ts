// SPDX-License-Identifier: 0BSD

import type { MapSearchResult } from "./types.js";

const WGS84_REGEX = /^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/u;

export function parseWgs84Coordinates(input: string): MapSearchResult | null {
    const match = WGS84_REGEX.exec(input);
    if (!match) return null;
    const lat = parseFloat(match[1]);
    const lon = parseFloat(match[2]);
    if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
        return null;
    }
    return {
        display_name: `${lat.toFixed(6)}, ${lon.toFixed(6)}`,
        lat,
        lon,
        type: "wgs84",
    };
}

export async function fetchNominatimSearch(query: string, fetchFn: typeof fetch = fetch): Promise<MapSearchResult[]> {
    const trimmed = query.trim();
    if (!trimmed) return [];
    const direct = parseWgs84Coordinates(trimmed);
    if (direct) return [direct];

    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(trimmed)}`;
    const res = await fetchFn(url);
    if (!res.ok) return [];
    const data = await res.json();
    if (!Array.isArray(data)) return [];
    return data.map((item: any) => ({
        place_id: item.place_id,
        display_name: item.display_name || "",
        lat: parseFloat(item.lat),
        lon: parseFloat(item.lon),
        type: item.type || "place",
    }));
}
