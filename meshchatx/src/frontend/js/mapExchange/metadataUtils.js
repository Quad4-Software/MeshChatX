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
import { extractKeyedDescriptionLines, isNullishMapValue } from "./descriptionFlatten.js";
import { isAllowedDataImageHref, isRemoteHref } from "./kmlSanitize.js";

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
    "styleUrl",
    "style",
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
    "overlay_id",
]);

const URL_RE = /\bhttps?:\/\/[^\s<>"'`]+/gi;

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
 * Only data-URI raster icons are safe in the local UI img tag.
 * @param {unknown} src
 * @returns {string|null}
 */
export function safeFeatureIconSrc(src) {
    if (src == null || src === "") {
        return null;
    }
    const s = String(src).trim();
    if (!s) {
        return null;
    }
    if (isAllowedDataImageHref(s)) {
        return s;
    }
    if (isRemoteHref(s) || s.toLowerCase().startsWith("data:")) {
        return null;
    }
    return null;
}

/**
 * @param {unknown} v
 * @returns {string}
 */
function stringifyPropValue(v) {
    if (v == null) {
        return "";
    }
    if (typeof v === "object") {
        try {
            return JSON.stringify(v);
        } catch {
            return String(v);
        }
    }
    return String(v);
}

/**
 * @param {string} text
 * @returns {{ kind: "text"|"link", text: string, href?: string }[]}
 */
export function splitTextWithLinks(text) {
    const raw = String(text || "");
    if (!raw) {
        return [];
    }
    const parts = [];
    let last = 0;
    URL_RE.lastIndex = 0;
    let m;
    while ((m = URL_RE.exec(raw)) !== null) {
        if (m.index > last) {
            parts.push({ kind: "text", text: raw.slice(last, m.index) });
        }
        let href = m[0];
        while (/[),.;!?]$/.test(href)) {
            href = href.slice(0, -1);
        }
        parts.push({ kind: "link", text: href, href });
        last = m.index + href.length;
        URL_RE.lastIndex = last;
    }
    if (last < raw.length) {
        parts.push({ kind: "text", text: raw.slice(last) });
    }
    return parts.length ? parts : [{ kind: "text", text: raw }];
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
    let description = rawDesc == null ? "" : typeof rawDesc === "string" ? rawDesc : String(rawDesc);
    const iconSrc = safeFeatureIconSrc(props[MCX_ICON_DATA_URL] || props[MCX_ICON_HREF] || null);
    const extended = [];
    const seenKeys = new Set();
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
        let vs = stringifyPropValue(v).trim();
        if (vs.length > 400) {
            vs = `${vs.slice(0, 400)}…`;
        }
        if (isNullishMapValue(vs)) {
            continue;
        }
        extended.push({ key: k, value: vs });
        seenKeys.add(k.toLowerCase());
    }
    if (description.trim() && !looksLikeHtml(description)) {
        const extracted = extractKeyedDescriptionLines(description);
        for (const pair of extracted.pairs) {
            if (seenKeys.has(pair.key.toLowerCase())) {
                continue;
            }
            extended.push(pair);
            seenKeys.add(pair.key.toLowerCase());
        }
        description = extracted.leftover;
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
        iconSrc,
        extended,
    };
}

/**
 * Apply edited name and description onto a draw feature.
 * @param {import("ol/Feature").default} feature
 * @param {{ name?: string, description?: string }} fields
 */
export function applyFeatureMetadataEdits(feature, fields) {
    if (!feature || !fields) {
        return;
    }
    if (Object.prototype.hasOwnProperty.call(fields, "name")) {
        feature.set("name", String(fields.name ?? "").trim());
        feature.unset("Name");
    }
    if (Object.prototype.hasOwnProperty.call(fields, "description")) {
        feature.set("description", String(fields.description ?? ""));
        feature.unset("Description");
    }
}
