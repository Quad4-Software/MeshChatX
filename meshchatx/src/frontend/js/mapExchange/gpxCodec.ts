// SPDX-License-Identifier: 0BSD

import GPX from "ol/format/GPX";
import { normalizeFeatureMetadataProps } from "./metadataUtils.js";
import { styleFromMcxProperties } from "./styleFromProperties.js";

/**
 * Mirror GPX desc onto description (and the reverse before write).
 * @param {import("ol/Feature").default} feature
 * @param {"read"|"write"} direction
 */
function syncGpxDescriptionProps(feature, direction) {
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

/**
 * @param {string} text
 * @param {import("ol/proj").ProjectionLike} featureProjection
 * @returns {import("ol/Feature").default[]}
 */
export function readGpxToFeatures(text, featureProjection) {
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

/**
 * @param {import("ol/Feature").default[]} features
 * @param {import("ol/proj").ProjectionLike} featureProjection
 * @returns {string}
 */
export function writeFeaturesToGpx(features, featureProjection) {
    const format = new GPX();
    for (const f of features) {
        syncGpxDescriptionProps(f, "write");
    }
    return format.writeFeatures(features, {
        dataProjection: "EPSG:4326",
        featureProjection,
    });
}
