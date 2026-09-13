// SPDX-License-Identifier: 0BSD

import VectorLayer from "ol/layer/Vector.js";
import VectorSource from "ol/source/Vector.js";
import type Feature from "ol/Feature.js";
import type OlMap from "ol/Map.js";
import { readGeoJsonToFeatures } from "../../../js/mapExchange/geoJsonCodec.js";
import { readKmlToFeatures } from "../../../js/mapExchange/kmlCodec.js";
import { readKmzToFeatures } from "../../../js/mapExchange/kmzCodec.js";
import { downloadBlobFile } from "./mapVectorExchange.js";
import type { RemoteOverlayEntry as MapRemoteOverlay } from "./types.js";

/** OpenLayers layer cache entry for a remote overlay. */
export type RemoteOverlayLayerEntry = {
    source: VectorSource;
    layer: VectorLayer<VectorSource>;
    sha?: string;
};

/** Layer-cache alias used by MapPage. API overlay rows live in types.RemoteOverlayEntry. */
export type RemoteOverlayEntry = RemoteOverlayLayerEntry;

async function featuresFromOverlayContent(overlay: MapRemoteOverlay, contentRes: Response): Promise<Feature[]> {
    const fmt = overlay.format;
    if (fmt === "kmz") {
        const buf = await contentRes.arrayBuffer();
        return readKmzToFeatures(buf, "EPSG:3857");
    }
    const text = await contentRes.text();
    if (fmt === "kml") {
        return readKmlToFeatures(text, "EPSG:3857");
    }
    return readGeoJsonToFeatures(text, "EPSG:3857");
}

export function removeRemoteOverlayLayer(
    map: OlMap | null | undefined,
    remoteOverlayLayers: Record<string, RemoteOverlayLayerEntry>,
    id: string
): void {
    const entry = remoteOverlayLayers[id];
    if (!entry) return;
    if (map && entry.layer) {
        map.removeLayer(entry.layer);
    }
    delete remoteOverlayLayers[id];
}

export async function ensureRemoteOverlayLayer(
    map: OlMap | null | undefined,
    remoteOverlayLayers: Record<string, RemoteOverlayLayerEntry>,
    overlay: MapRemoteOverlay
): Promise<void> {
    if (!map || !overlay?.id) return;
    const id = String(overlay.id);
    const contentRes = await fetch(`/api/v1/map/overlays/${overlay.id}/content`, {
        credentials: "same-origin",
    });
    if (!contentRes.ok) {
        throw new Error(`overlay content ${contentRes.status}`);
    }
    const features = await featuresFromOverlayContent(overlay, contentRes);
    for (const f of features) {
        f.set("type", "remote_overlay");
        f.set("overlay_id", overlay.id);
    }
    let entry = remoteOverlayLayers[id];
    if (!entry) {
        const source = new VectorSource();
        const layer = new VectorLayer({
            source,
            zIndex: 45,
            opacity: 0.95,
        });
        map.addLayer(layer);
        entry = { source, layer, sha: overlay.content_sha256 };
        remoteOverlayLayers[id] = entry;
    }
    entry.source.clear();
    entry.source.addFeatures(features);
    entry.sha = overlay.content_sha256;
}

export async function exportRemoteOverlay(id: string | number, format: string): Promise<void> {
    const res = await fetch(`/api/v1/map/overlays/${id}/export?format=${encodeURIComponent(format)}`, {
        credentials: "same-origin",
    });
    if (!res.ok) {
        throw new Error(`export ${res.status}`);
    }
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") || "";
    const match = /filename="([^"]+)"/.exec(cd);
    const name = match?.[1] || `overlay-${id}.${format}`;
    downloadBlobFile(name, blob, blob.type || "application/octet-stream");
}

export async function copyRemoteOverlayToDrawings(
    drawSource: VectorSource | null | undefined,
    overlay: MapRemoteOverlay
): Promise<number> {
    if (!drawSource || !overlay?.id) return 0;
    const contentRes = await fetch(`/api/v1/map/overlays/${overlay.id}/content`, {
        credentials: "same-origin",
    });
    if (!contentRes.ok) {
        throw new Error(`overlay content ${contentRes.status}`);
    }
    const features = await featuresFromOverlayContent(overlay, contentRes);
    for (const f of features) {
        f.set("type", "draw");
        f.unset("overlay_id");
    }
    drawSource.addFeatures(features);
    return features.length;
}
