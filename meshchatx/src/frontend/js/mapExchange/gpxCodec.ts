// SPDX-License-Identifier: 0BSD

import type Feature from "ol/Feature";
import type { ProjectionLike } from "ol/proj";
import GPX from "ol/format/GPX";
import { normalizeFeatureMetadataProps } from "./metadataUtils.js";
import { styleFromMcxProperties } from "./styleFromProperties.js";

type GpxSyncDirection = "read" | "write";

/** Mirror GPX desc onto description (and the reverse before write). */
function syncGpxDescriptionProps(feature: Feature | null | undefined, direction: GpxSyncDirection): void {
    if (!feature) {
        return;
    }
    if (direction === "read") {
        const desc = feature.get("desc");
        if ((feature.get("description") == null || feature.get("description") === "") && desc != null && desc !== "") {
            feature.set("description", typeof desc === "string" ? desc : String(desc));
        }
        return;
    }
    const description = feature.get("description");
    if ((feature.get("desc") == null || feature.get("desc") === "") && description != null && description !== "") {
        feature.set("desc", typeof description === "string" ? description : String(description));
    }
}

export function readGpxToFeatures(text: string, featureProjection: ProjectionLike): Feature[] {
    const format = new GPX();
    const features = format.readFeatures(text, {
        dataProjection: "EPSG:4326",
        featureProjection,
    });
    for (const f of features) {
        normalizeFeatureMetadataProps(f);
        syncGpxDescriptionProps(f, "read");
        if (!f.getStyle()) {
            const s = styleFromMcxProperties(f);
            if (s) {
                f.setStyle(s);
            }
        }
    }
    return features;
}

export function writeFeaturesToGpx(features: Feature[], featureProjection: ProjectionLike): string {
    const format = new GPX();
    for (const f of features) {
        syncGpxDescriptionProps(f, "write");
    }
    return format.writeFeatures(features, {
        dataProjection: "EPSG:4326",
        featureProjection,
    });
}
