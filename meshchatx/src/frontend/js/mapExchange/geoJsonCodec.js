// SPDX-License-Identifier: 0BSD

import GeoJSON from "ol/format/GeoJSON";
import { normalizeFeatureMetadataProps } from "./metadataUtils.js";
import { copyStyleMetadataToProperties, styleFromMcxProperties } from "./styleFromProperties.js";
import { isAllowedDataImageHref, isRemoteHref } from "./kmlSanitize.js";
import { MCX_ICON_DATA_URL, MCX_ICON_HREF } from "./constants.js";

const ICON_URL_KEYS = new Set(["href", "url", "icon", "image", "iconurl", MCX_ICON_HREF, "marker-symbol"]);

/**
 * Strip remote / unsafe icon URLs from a feature (mirrors backend geojson sanitizer).
 * @param {import("ol/Feature").default} feature
 */
export function stripRemoteIconProperties(feature) {
    if (!feature) {
        return;
    }
    for (const key of feature.getKeys()) {
        const keyL = String(key).toLowerCase();
        const matched = ICON_URL_KEYS.has(key) || ICON_URL_KEYS.has(keyL) || key === MCX_ICON_DATA_URL;
        if (!matched) {
            continue;
        }
        const val = feature.get(key);
        if (typeof val !== "string") {
            continue;
        }
        if (isAllowedDataImageHref(val)) {
            continue;
        }
        if (isRemoteHref(val) || val.trim().toLowerCase().startsWith("data:")) {
            feature.unset(key);
        }
    }
}

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
        stripRemoteIconProperties(f);
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
        stripRemoteIconProperties(f);
    }
    return format.writeFeatures(features, {
        dataProjection: "EPSG:4326",
        featureProjection,
        decimals: 7,
    });
}
