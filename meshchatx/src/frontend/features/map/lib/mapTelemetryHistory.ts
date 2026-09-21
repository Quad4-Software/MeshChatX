// SPDX-License-Identifier: 0BSD

import Feature from "ol/Feature";
import LineString from "ol/geom/LineString";
import { fromLonLat } from "ol/proj";
import { Style, Stroke } from "ol/style";
import { isValidLatLon } from "../../../js/mapGeoCoords.js";
import type { TelemetryPeer } from "./types.js";

export function createTelemetryHistoryStyle(): Style {
    return new Style({
        stroke: new Stroke({
            color: "rgba(234, 179, 8, 0.6)",
            width: 3,
            lineDash: [10, 10],
        }),
    });
}

/**
 * Build a dashed trail Feature from telemetry history entries.
 * Returns null when fewer than two located points exist.
 */
export function buildTelemetryHistoryTrailFeature(history: TelemetryPeer[] | null | undefined): Feature | null {
    if (!Array.isArray(history) || history.length < 2) {
        return null;
    }
    const coords: number[][] = [];
    for (const entry of history) {
        const loc = entry?.telemetry?.location;
        if (loc && isValidLatLon(loc.latitude, loc.longitude)) {
            coords.push(fromLonLat([Number(loc.longitude), Number(loc.latitude)]));
        }
    }
    if (coords.length < 2) {
        return null;
    }
    return new Feature({
        geometry: new LineString(coords),
        type: "history_trail",
    });
}
