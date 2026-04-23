// SPDX-License-Identifier: 0BSD

import GeoJSON from "ol/format/GeoJSON";
import { normalizeFeatureMetadataProps } from "./metadataUtils.js";
import { copyStyleMetadataToProperties, styleFromMcxProperties } from "./styleFromProperties.js";

/**
 * @param {string} text
 * @param {import("ol/proj").ProjectionLike} featureProjection
 * @returns {import("ol/Feature").default[]}
 */
export function readGeoJsonToFeatures(text, featureProjection) {
    const format = new GeoJSON();
    const features = format.readFeatures(text, {
        dataProjection: "EPSG:4326",
        featureProjection,
    });
    for (const f of features) {
        normalizeFeatureMetadataProps(f);
        if (!f.getStyle()) {
            const s = styleFromMcxProperties(f);
            if (s) {
                f.setStyle(s);
            }
        }
    }
    return features;
}

/**
 * @param {import("ol/Feature").default[]} features
 * @param {import("ol/proj").ProjectionLike} featureProjection
 * @returns {string}
 */
export function writeFeaturesToGeoJson(features, featureProjection) {
    const format = new GeoJSON();
    for (const f of features) {
        let st = f.getStyle();
        if (typeof st === "function") {
            st = null;
        }
        if (st) {
            copyStyleMetadataToProperties(st, f);
        } else {
            const built = styleFromMcxProperties(f);
            if (built) {
                copyStyleMetadataToProperties(built, f);
            }
        }
    }
    return format.writeFeatures(features, {
        dataProjection: "EPSG:4326",
        featureProjection,
        decimals: 7,
    });
}
