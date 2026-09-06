// SPDX-License-Identifier: 0BSD

import type { MapSearchResult } from "./types.js";
import { buildNominatimSearchUrl } from "../../../js/mapTileNetwork.js";

function isWgs84NumberToken(raw: string): boolean {
    if (!raw) return false;
    let i = 0;
    if (raw[i] === "-") i += 1;
    if (i >= raw.length) return false;
    let sawDigit = false;
    while (i < raw.length && raw[i] >= "0" && raw[i] <= "9") {
        sawDigit = true;
        i += 1;
    }
    if (!sawDigit) return false;
    if (i < raw.length && raw[i] === ".") {
        i += 1;
        let frac = false;
        while (i < raw.length && raw[i] >= "0" && raw[i] <= "9") {
            frac = true;
            i += 1;
        }
        if (!frac) return false;
    }
    return i === raw.length;
}

type NominatimSearchItem = {
    place_id?: string | number;
    display_name?: string;
    lat?: string;
    lon?: string;
    type?: string;
};

export function parseWgs84Coordinates(input: string): MapSearchResult | null {
    const trimmed = String(input || "").trim();
    const comma = trimmed.indexOf(",");
    if (comma < 0) return null;
    const latStr = trimmed.slice(0, comma).trim();
    const lonStr = trimmed.slice(comma + 1).trim();
    if (!isWgs84NumberToken(latStr) || !isWgs84NumberToken(lonStr)) return null;
    const lat = parseFloat(latStr);
    const lon = parseFloat(lonStr);
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

export async function fetchNominatimSearch(
    query: string,
    fetchFn: typeof fetch = fetch,
    nominatimApiUrl = "https://nominatim.openstreetmap.org"
): Promise<MapSearchResult[]> {
    const trimmed = query.trim();
    if (!trimmed) return [];
    const direct = parseWgs84Coordinates(trimmed);
    if (direct) return [direct];

    const url = buildNominatimSearchUrl(nominatimApiUrl, trimmed, 5);
    const res = await fetchFn(url);
    if (!res.ok) return [];
    const data: unknown = await res.json();
    if (!Array.isArray(data)) return [];
    return data.map((raw) => {
        const item = raw as NominatimSearchItem;
        return {
            place_id: item.place_id,
            display_name: item.display_name || "",
            lat: parseFloat(String(item.lat ?? "")),
            lon: parseFloat(String(item.lon ?? "")),
            type: item.type || "place",
        };
    });
}
