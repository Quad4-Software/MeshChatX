// SPDX-License-Identifier: 0BSD

import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { fromLonLat, toLonLat } from "ol/proj";
import { dedupeTelemetryMarkersForMap, dedupeDiscoveredMapNodes } from "./mapDedupe.js";
import { getPeerMarkerStyle } from "./markerStyles.js";
import { formatCoordinate } from "../../../js/mapGeoCoords.js";

export function createPeerFeatures(telemetryList: any[]): Feature[] {
    const deduped = dedupeTelemetryMarkersForMap(telemetryList);
    const features: Feature[] = [];
    for (const item of deduped) {
        const loc = item.telemetry?.location;
        if (!loc || typeof loc.longitude !== "number" || typeof loc.latitude !== "number") continue;
        const feat = new Feature({
            geometry: new Point(fromLonLat([loc.longitude, loc.latitude])),
            peer: item,
        });
        feat.setStyle(getPeerMarkerStyle(item, false));
        features.push(feat);
    }
    return features;
}

export function createDiscoveredFeatures(nodes: any[]): Feature[] {
    const deduped = dedupeDiscoveredMapNodes(nodes);
    const features: Feature[] = [];
    for (const node of deduped) {
        if (typeof node.longitude !== "number" || typeof node.latitude !== "number") continue;
        const feat = new Feature({
            geometry: new Point(fromLonLat([node.longitude, node.latitude])),
            discoveredNode: node,
        });
        features.push(feat);
    }
    return features;
}

export interface ContextMenuCoordRow {
    format: string;
    label: string;
    text: string;
}

export function getContextMenuCoordRows(coord: number[] | null): ContextMenuCoordRow[] {
    if (!coord) return [];
    const lonLat = toLonLat(coord);
    return [
        { format: "wgs84", label: "WGS84", text: `${lonLat[1].toFixed(5)}, ${lonLat[0].toFixed(5)}` },
        { format: "mgrs", label: "MGRS", text: formatCoordinate(lonLat[1], lonLat[0], "mgrs") },
        { format: "maidenhead", label: "Maidenhead", text: formatCoordinate(lonLat[1], lonLat[0], "maidenhead") },
    ];
}

export function extractDrawFeaturePayload(feature: any) {
    if (!feature) return null;
    return {
        name: feature.get("name") || feature.get("text") || "",
        description: feature.get("note") || feature.get("description") || "",
        descriptionIsHtml: false,
        extended: [],
    };
}
