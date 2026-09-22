// SPDX-License-Identifier: 0BSD

import type Feature from "ol/Feature";
import type { ProjectionLike } from "ol/proj";
import KML from "ol/format/KML";
import { normalizeFeatureMetadataProps } from "./metadataUtils.js";
import { normalizeKmlImportedFeatures, ensureOlStylesForKmlExport } from "./styleFromProperties.js";
import { sanitizeKmlText } from "./kmlSanitize.js";

export function readKmlToFeatures(text: string, featureProjection: ProjectionLike): Feature[] {
    const sanitized = sanitizeKmlText(text, { zipLocalOk: false });
    const format = new KML({
        extractStyles: true,
        showNetworkLinks: false,
        showPointNames: false,
    } as any);
    const features = format.readFeatures(sanitized.text, {
        dataProjection: "EPSG:4326",
        featureProjection,
    });
    normalizeKmlImportedFeatures(features);
    for (const f of features) {
        normalizeFeatureMetadataProps(f);
    }
    return features;
}

export function writeFeaturesToKml(features: Feature[], featureProjection: ProjectionLike): string {
    const format = new KML();
    ensureOlStylesForKmlExport(features);
    return format.writeFeatures(features, {
        dataProjection: "EPSG:4326",
        featureProjection,
    });
}
