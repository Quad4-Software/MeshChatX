// SPDX-License-Identifier: 0BSD

import type Feature from "ol/Feature.js";
import { readGeoJsonToFeatures } from "../../../js/mapExchange/geoJsonCodec.js";
import { readKmlToFeatures } from "../../../js/mapExchange/kmlCodec.js";
import { readKmzToFeatures } from "../../../js/mapExchange/kmzCodec.js";
import { readGpxToFeatures } from "../../../js/mapExchange/gpxCodec.js";

const GEOJSON_TYPES = new Set([
    "FeatureCollection",
    "Feature",
    "Point",
    "MultiPoint",
    "LineString",
    "MultiLineString",
    "Polygon",
    "MultiPolygon",
    "GeometryCollection",
]);

export function isMbtilesFile(file: { name?: string } | null | undefined): boolean {
    return Boolean(file?.name && file.name.toLowerCase().endsWith(".mbtiles"));
}

export function isGeoDropFile(file: { name?: string } | null | undefined): boolean {
    const name = String(file?.name || "").toLowerCase();
    return (
        name.endsWith(".geojson") ||
        name.endsWith(".json") ||
        name.endsWith(".kml") ||
        name.endsWith(".kmz") ||
        name.endsWith(".gpx")
    );
}

export function classifyMapDropFiles(files: ArrayLike<{ name?: string }> | null | undefined): {
    mbtilesFiles: { name?: string }[];
    geoFiles: { name?: string }[];
} {
    const list = Array.from(files || []);
    return {
        mbtilesFiles: list.filter((f) => isMbtilesFile(f)),
        geoFiles: list.filter((f) => isGeoDropFile(f)),
    };
}

export function looksLikeGeoJsonText(text: string): boolean {
    try {
        const obj = JSON.parse(String(text || "")) as { type?: string };
        if (!obj || typeof obj !== "object") {
            return false;
        }
        return GEOJSON_TYPES.has(obj.type || "");
    } catch {
        return false;
    }
}

export async function readFileText(file: Blob): Promise<string> {
    return file.text();
}

export async function readFileArrayBuffer(file: Blob): Promise<ArrayBuffer> {
    return file.arrayBuffer();
}

/**
 * Parse a dropped geo vector file into OpenLayers features in EPSG:3857.
 * Returns null when a .json/.geojson payload is not GeoJSON.
 */
export async function readDroppedGeoFileToFeatures(
    file: File,
    featureProjection: string = "EPSG:3857"
): Promise<Feature[] | null> {
    const name = String(file?.name || "").toLowerCase();
    if (name.endsWith(".kmz")) {
        const buf = await readFileArrayBuffer(file);
        return readKmzToFeatures(buf, featureProjection);
    }
    if (name.endsWith(".kml")) {
        const text = await readFileText(file);
        return readKmlToFeatures(text, featureProjection);
    }
    if (name.endsWith(".gpx")) {
        const text = await readFileText(file);
        return readGpxToFeatures(text, featureProjection);
    }
    const text = await readFileText(file);
    if (!looksLikeGeoJsonText(text)) {
        return null;
    }
    return readGeoJsonToFeatures(text, featureProjection);
}
