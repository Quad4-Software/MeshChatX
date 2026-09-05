// SPDX-License-Identifier: 0BSD

import type VectorSource from "ol/source/Vector.js";
import Feature from "ol/Feature.js";
import Point from "ol/geom/Point.js";
import { fromLonLat } from "ol/proj.js";
import { dedupeDiscoveredMapNodes, dedupeTelemetryMarkersForMap } from "./mapDedupe.js";
import { peerBadgeStyle } from "./markerStyles.js";
import type { MapAnnounceItem } from "./types.js";

export interface MarkerManagerConfig {
    markerSource: VectorSource;
    onNodeSelect?: (node: any) => void;
}

export class MapMarkerManager {
    private markerSource: VectorSource;
    private announces: MapAnnounceItem[] = [];
    private telemetry: any[] = [];
    private markers: any[] = [];
    private onNodeSelectCallback?: (node: any) => void;

    constructor(config: MarkerManagerConfig) {
        this.markerSource = config.markerSource;
        this.onNodeSelectCallback = config.onNodeSelect;
    }

    public updateData(announces: MapAnnounceItem[], telemetry: any[], markers: any[]) {
        this.announces = announces || [];
        this.telemetry = telemetry || [];
        this.markers = markers || [];
        this.refreshMarkers();
    }

    public refreshMarkers(zoom = 10, _extent?: [number, number, number, number]) {
        this.markerSource.clear();

        const validAnnounces = this.announces.filter(
            (a) =>
                typeof a.latitude === "number" &&
                typeof a.longitude === "number" &&
                !isNaN(a.latitude) &&
                !isNaN(a.longitude)
        );

        const dedupedNodes = dedupeDiscoveredMapNodes(validAnnounces as any);
        const dedupedTelemetry = dedupeTelemetryMarkersForMap(this.telemetry);

        const allItems = [...dedupedNodes, ...dedupedTelemetry, ...this.markers];
        for (const item of allItems) {
            this.addSingleMarker(item, zoom);
        }
    }

    private addSingleMarker(item: any, zoom: number) {
        const lat = item.latitude ?? item.lat;
        const lon = item.longitude ?? item.lon;
        if (typeof lat !== "number" || typeof lon !== "number") return;

        const feature = new Feature({
            geometry: new Point(fromLonLat([lon, lat])),
            item,
            destination_hash: item.destination_hash || item.dest_hash,
            display_name: item.display_name || item.custom_display_name || item.name,
        });

        const style = peerBadgeStyle({
            label: item.display_name || item.custom_display_name || item.name || "Node",
            showLabel: zoom >= 12,
        });
        feature.setStyle(style);
        this.markerSource.addFeature(feature);
    }
}
