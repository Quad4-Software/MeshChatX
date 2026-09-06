// SPDX-License-Identifier: 0BSD

import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { fromLonLat, toLonLat } from "ol/proj";
import { dedupeTelemetryMarkersForMap, dedupeDiscoveredMapNodes } from "./mapDedupe.js";
import { getPeerMarkerStyle } from "./markerStyles.js";
import { formatCoordinate } from "../../../js/mapGeoCoords.js";
import type { DiscoveredMapNode, DrawFeatureEditPayload, MapPeer, MarkerPanelPayload, TelemetryPeer } from "./types.js";

interface FeaturePropReader {
    get(key: string): unknown;
}

export function createPeerFeatures(telemetryList: TelemetryPeer[], peers: Record<string, MapPeer> = {}): Feature[] {
    const deduped = dedupeTelemetryMarkersForMap(telemetryList, peers);
    const features: Feature[] = [];
    for (const item of deduped) {
        const loc = item.telemetry?.location;
        if (!loc || typeof loc.longitude !== "number" || typeof loc.latitude !== "number") continue;
        const peer = item.destination_hash ? peers[item.destination_hash] : undefined;
        const coord = fromLonLat([loc.longitude, loc.latitude]);
        const feat = new Feature({
            geometry: new Point(coord),
            telemetry: item,
            peer,
            originalCoord: coord,
        });
        const styleSource = peer
            ? {
                  display_name: peer.display_name,
                  background_colour: peer.lxmf_user_icon?.background_colour,
                  foreground_colour: peer.lxmf_user_icon?.foreground_colour,
                  is_stale: item.is_stale,
              }
            : {
                  display_name: item.destination_hash?.substring(0, 8) || "",
                  is_stale: item.is_stale,
              };
        feat.setStyle(getPeerMarkerStyle(styleSource, false));
        features.push(feat);
    }
    return features;
}

export function createDiscoveredFeatures(nodes: DiscoveredMapNode[]): Feature[] {
    const deduped = dedupeDiscoveredMapNodes(nodes);
    const features: Feature[] = [];
    for (const node of deduped) {
        if (typeof node.longitude !== "number" || typeof node.latitude !== "number") continue;
        const coord = fromLonLat([node.longitude, node.latitude]);
        const feat = new Feature({
            geometry: new Point(coord),
            discovered: node,
            originalCoord: coord,
        });
        features.push(feat);
    }
    return features;
}

export function markerPanelPayloadFromFeature(
    feature: FeaturePropReader | null | undefined
): MarkerPanelPayload | null {
    if (!feature || typeof feature.get !== "function") return null;
    const telemetry = feature.get("telemetry") as TelemetryPeer | null | undefined;
    const peer = feature.get("peer") as MapPeer | null | undefined;
    const discovered = feature.get("discovered") as DiscoveredMapNode | null | undefined;
    if (!telemetry && !peer && !discovered) return null;
    return { telemetry, peer, discovered };
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
        { format: "mgrs", label: "MGRS", text: formatCoordinate(lonLat[0], lonLat[1], "mgrs")?.text || "" },
        {
            format: "maidenhead",
            label: "Maidenhead",
            text: formatCoordinate(lonLat[0], lonLat[1], "maidenhead")?.text || "",
        },
    ];
}

export function extractDrawFeaturePayload(
    feature: FeaturePropReader | null | undefined
): DrawFeatureEditPayload | null {
    if (!feature) return null;
    return {
        name: String(feature.get("name") || feature.get("text") || ""),
        description: String(feature.get("note") || feature.get("description") || ""),
        descriptionIsHtml: false,
        extended: [],
    };
}
