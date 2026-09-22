// SPDX-License-Identifier: 0BSD

import { fromCircle } from "ol/geom/Polygon";
import Circle from "ol/geom/Circle";
import type Feature from "ol/Feature.js";
import { writeFeaturesToGeoJson } from "../../../js/mapExchange/geoJsonCodec.js";
import { writeFeaturesToKml } from "../../../js/mapExchange/kmlCodec.js";
import { writeFeaturesToKmzBlob } from "../../../js/mapExchange/kmzCodec.js";
import { writeFeaturesToGpx } from "../../../js/mapExchange/gpxCodec.js";

export function serializeDrawFeatures(features: Feature[]): Feature[] {
    return features
        .filter((f) => !f.get("bearingPreview"))
        .map((f) => {
            const clone = f.clone();
            clone.unset("_measureOverlay", true);
            const geom = clone.getGeometry();
            if (geom instanceof Circle) {
                clone.setGeometry(fromCircle(geom, 128));
            }
            const st = f.getStyle();
            if (st != null && typeof st !== "function") {
                clone.setStyle(st);
            }
            return clone;
        });
}

export function downloadTextFile(filename: string, text: string, mime: string): void {
    const blob = new Blob([text], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

export function downloadBlobFile(filename: string, blob: Blob, mime: string): void {
    const b = new Blob([blob], { type: mime });
    const url = URL.createObjectURL(b);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

export function exportDrawFeaturesGeoJson(features: Feature[]): string {
    return writeFeaturesToGeoJson(serializeDrawFeatures(features), "EPSG:3857");
}

export function exportDrawFeaturesKml(features: Feature[]): string {
    return writeFeaturesToKml(serializeDrawFeatures(features), "EPSG:3857");
}

export async function exportDrawFeaturesKmz(features: Feature[]): Promise<Blob> {
    return writeFeaturesToKmzBlob(serializeDrawFeatures(features), "EPSG:3857");
}

export function exportDrawFeaturesGpx(features: Feature[]): string {
    return writeFeaturesToGpx(serializeDrawFeatures(features), "EPSG:3857");
}

export function exportFilename(ext: string): string {
    return `meshchatx-drawings-${new Date().toISOString().slice(0, 10)}.${ext}`;
}
