// SPDX-License-Identifier: 0BSD

import KML from "ol/format/KML";
import { normalizeFeatureMetadataProps } from "./metadataUtils.js";
import { normalizeKmlImportedFeatures, ensureOlStylesForKmlExport } from "./styleFromProperties.js";

/**
 * @param {string} text
 * @param {import("ol/proj").ProjectionLike} featureProjection
 * @returns {import("ol/Feature").default[]}
 */
export function readKmlToFeatures(text, featureProjection) {
    const format = new KML({
        extractStyles: true,
        showNetworkLinks: false,
        showPointNames: false,
    });
    const features = format.readFeatures(text, {
        dataProjection: "EPSG:4326",
        featureProjection,
    });
    normalizeKmlImportedFeatures(features);
    for (const f of features) {
        normalizeFeatureMetadataProps(f);
    }
    return features;
}

/**
 * @param {import("ol/Feature").default[]} features
 * @param {import("ol/proj").ProjectionLike} featureProjection
 * @returns {string}
 */
export function writeFeaturesToKml(features, featureProjection) {
    const format = new KML();
    ensureOlStylesForKmlExport(features);
    return format.writeFeatures(features, {
        dataProjection: "EPSG:4326",
        featureProjection,
    });
}
