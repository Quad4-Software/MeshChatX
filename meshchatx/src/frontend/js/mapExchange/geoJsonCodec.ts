// SPDX-License-Identifier: 0BSD

import type Feature from "ol/Feature";
import type { ProjectionLike } from "ol/proj";
import type Style from "ol/style/Style";
import GeoJSON from "ol/format/GeoJSON";
import { normalizeFeatureMetadataProps } from "./metadataUtils.js";
import { copyStyleMetadataToProperties, styleFromMcxProperties } from "./styleFromProperties.js";
import { isAllowedDataImageHref, isRemoteHref } from "./kmlSanitize.js";
import { MCX_ICON_DATA_URL, MCX_ICON_HREF } from "./constants.js";

const ICON_URL_KEYS = new Set(["href", "url", "icon", "image", "iconurl", MCX_ICON_HREF, "marker-symbol"]);

/** Strip remote / unsafe icon URLs from a feature (mirrors backend geojson sanitizer). */
export function stripRemoteIconProperties(feature: Feature | null | undefined): void {
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

export function readGeoJsonToFeatures(text: string, featureProjection: ProjectionLike): Feature[] {
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

export function writeFeaturesToGeoJson(features: Feature[], featureProjection: ProjectionLike): string {
    const format = new GeoJSON();
    for (const f of features) {
        let st: ReturnType<Feature["getStyle"]> = f.getStyle();
        if (typeof st === "function") {
            st = undefined;
        }
        if (st) {
            copyStyleMetadataToProperties(st as Style | Style[], f);
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
