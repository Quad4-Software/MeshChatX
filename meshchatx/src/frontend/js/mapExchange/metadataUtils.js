// SPDX-License-Identifier: 0BSD

import { getCenter } from "ol/extent";
import {
    MCX_FILL_COLOR,
    MCX_FILL_OPACITY,
    MCX_ICON_ANCHOR_X,
    MCX_ICON_ANCHOR_Y,
    MCX_ICON_DATA_URL,
    MCX_ICON_HREF,
    MCX_ICON_SCALE,
    MCX_STROKE_COLOR,
    MCX_STROKE_WIDTH,
} from "./constants.js";

const SKIP_EXTENDED = new Set([
    "geometry",
    "type",
    "note",
    "telemetry",
    "discovered",
    "cluster",
    "peer",
    "segmentKind",
    "bearingMetrics",
    "_measureOverlay",
    MCX_ICON_DATA_URL,
    MCX_ICON_HREF,
    MCX_ICON_SCALE,
    MCX_ICON_ANCHOR_X,
    MCX_ICON_ANCHOR_Y,
    MCX_STROKE_COLOR,
    MCX_STROKE_WIDTH,
    MCX_FILL_COLOR,
    MCX_FILL_OPACITY,
    "marker-color",
    "marker-size",
    "stroke",
    "stroke-width",
    "fill",
    "fill-opacity",
]);

/**
 * Normalize KML-style Name/Description onto lowercase keys for export.
 * @param {import("ol/Feature").default} feature
 */
export function normalizeFeatureMetadataProps(feature) {
    if (!feature) {
        return;
    }
    const n = feature.get("name");
    const N = feature.get("Name");
    if ((n == null || n === "") && N != null && N !== "") {
        feature.set("name", N);
    }
    const d = feature.get("description");
    const D = feature.get("Description");
    if ((d == null || d === "") && D != null && D !== "") {
        feature.set("description", D);
    }
    const t = feature.get("title");
    const nameAfterKml = feature.get("name");
    if ((nameAfterKml == null || nameAfterKml === "") && t != null && t !== "") {
        feature.set("name", typeof t === "string" ? t : String(t));
    }
}

/**
 * @param {import("ol/Feature").default} feature
 * @returns {import("ol/coordinate").Coordinate|null}
 */
export function getFeatureAnchorCoordinate(feature) {
    const g = feature.getGeometry();
    if (!g) {
        return null;
    }
    const t = g.getType();
    if (t === "Point") {
        return /** @type {import("ol/geom/Point").default} */ (g).getCoordinates();
    }
    if (t === "MultiPoint") {
        return /** @type {import("ol/geom/MultiPoint").default} */ (g).getPoint(0).getCoordinates();
    }
    if (t === "Polygon") {
        return /** @type {import("ol/geom/Polygon").default} */ (g).getInteriorPoint().getCoordinates();
    }
    if (t === "MultiPolygon") {
        const mp = /** @type {import("ol/geom/MultiPolygon").default} */ (g);
        return mp.getPolygon(0).getInteriorPoint().getCoordinates();
    }
    if (t === "LineString") {
        const c = /** @type {import("ol/geom/LineString").default} */ (g).getCoordinates();
        if (!c.length) {
            return null;
        }
        return c[Math.floor(c.length / 2)];
    }
    if (t === "MultiLineString") {
        const ml = /** @type {import("ol/geom/MultiLineString").default} */ (g);
        const line = ml.getLineString(0);
        const c = line.getCoordinates();
        if (!c.length) {
            return null;
        }
        return c[Math.floor(c.length / 2)];
    }
    return getCenter(g.getExtent());
}

function looksLikeHtml(s) {
    return /<\/?[a-z][\s\S]*>/i.test(s);
}

/**
 * @param {import("ol/Feature").default} feature
 * @returns {{ name: string, description: string, descriptionIsHtml: boolean, iconSrc: string|null, extended: { key: string, value: string }[] }|null}
 */
export function getDrawFeatureMetadataPayload(feature) {
    if (!feature) {
        return null;
    }
    normalizeFeatureMetadataProps(feature);
    const props = feature.getProperties();
    if (props.type === "note") {
        return null;
    }
    const name = String(props.name ?? "").trim();
    const rawDesc = props.description;
    const description = rawDesc == null ? "" : typeof rawDesc === "string" ? rawDesc : String(rawDesc);
    const iconSrc = props[MCX_ICON_DATA_URL] || props[MCX_ICON_HREF] || null;
    const extended = [];
    for (const [k, v] of Object.entries(props)) {
        if (k === "geometry" || k.startsWith("_")) {
            continue;
        }
        if (SKIP_EXTENDED.has(k) || k.startsWith("mcx_")) {
            continue;
        }
        if (k === "name" || k === "Name" || k === "description" || k === "Description") {
            continue;
        }
        let vs;
        if (v == null) {
            vs = "";
        } else if (typeof v === "object") {
            try {
                vs = JSON.stringify(v);
            } catch {
                vs = String(v);
            }
        } else {
            vs = String(v);
        }
        if (vs.length > 400) {
            vs = `${vs.slice(0, 400)}…`;
        }
        extended.push({ key: k, value: vs });
    }
    extended.sort((a, b) => a.key.localeCompare(b.key));
    if (!name && !description.trim() && !extended.length && !iconSrc) {
        const geom = feature.getGeometry();
        const geomType = geom ? geom.getType() : null;
        if (geomType) {
            return {
                name: "",
                description: "",
                descriptionIsHtml: false,
                iconSrc: null,
                extended: [{ key: "geometry_type", value: geomType }],
            };
        }
        return null;
    }
    return {
        name,
        description,
        descriptionIsHtml: Boolean(description.trim() && looksLikeHtml(description)),
        iconSrc: iconSrc ? String(iconSrc) : null,
        extended,
    };
}
