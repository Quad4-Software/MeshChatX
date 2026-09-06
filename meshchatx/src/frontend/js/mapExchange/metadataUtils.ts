// SPDX-License-Identifier: 0BSD

import type Feature from "ol/Feature";
import type { Coordinate } from "ol/coordinate";
import type LineString from "ol/geom/LineString";
import type MultiLineString from "ol/geom/MultiLineString";
import type MultiPoint from "ol/geom/MultiPoint";
import type MultiPolygon from "ol/geom/MultiPolygon";
import type Point from "ol/geom/Point";
import type Polygon from "ol/geom/Polygon";
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
import {
    descriptionNeedsFlatten,
    extractKeyedDescriptionLines,
    flattenHtmlDescription,
    isNullishMapValue,
} from "./descriptionFlatten.js";
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

export type TextLinkPart = { kind: "text"; text: string } | { kind: "link"; text: string; href: string };

export type FeatureMetadataExtended = {
    key: string;
    value: string;
};

export type DrawFeatureMetadataPayload = {
    name: string;
    description: string;
    descriptionIsHtml: boolean;
    iconSrc: string | null;
    extended: FeatureMetadataExtended[];
};

export type FeatureMetadataEditFields = {
    name?: string;
    description?: string;
};

/** Normalize KML-style Name/Description onto lowercase keys for export. */
export function normalizeFeatureMetadataProps(feature: Feature | null | undefined): void {
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

export function getFeatureAnchorCoordinate(feature: Feature): Coordinate | null {
    const g = feature.getGeometry();
    if (!g) {
        return null;
    }
    const t = g.getType();
    if (t === "Point") {
        return (g as Point).getCoordinates();
    }
    if (t === "MultiPoint") {
        return (g as MultiPoint).getPoint(0).getCoordinates();
    }
    if (t === "Polygon") {
        return (g as Polygon).getInteriorPoint().getCoordinates();
    }
    if (t === "MultiPolygon") {
        const mp = g as MultiPolygon;
        return mp.getPolygon(0).getInteriorPoint().getCoordinates();
    }
    if (t === "LineString") {
        const c = (g as LineString).getCoordinates();
        if (!c.length) {
            return null;
        }
        return c[Math.floor(c.length / 2)];
    }
    if (t === "MultiLineString") {
        const ml = g as MultiLineString;
        const line = ml.getLineString(0);
        const c = line.getCoordinates();
        if (!c.length) {
            return null;
        }
        return c[Math.floor(c.length / 2)];
    }
    return getCenter(g.getExtent());
}

function looksLikeHtml(s: unknown): boolean {
    const cleaned = String(s || "").replace(/<\/?null>/gi, "");
    return /<\/?[a-z][\s\S]*>/i.test(cleaned);
}

/** Only data-URI raster icons are safe in the local UI img tag. */
export function safeFeatureIconSrc(src: unknown): string | null {
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

function stringifyPropValue(v: unknown): string {
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

export function splitTextWithLinks(text: unknown): TextLinkPart[] {
    const raw = String(text || "");
    if (!raw) {
        return [];
    }
    const parts: TextLinkPart[] = [];
    let last = 0;
    URL_RE.lastIndex = 0;
    let m: RegExpExecArray | null;
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

export function getDrawFeatureMetadataPayload(feature: Feature | null | undefined): DrawFeatureMetadataPayload | null {
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
    if (description.trim() && descriptionNeedsFlatten(description)) {
        description = flattenHtmlDescription(description);
    }
    const iconSrc = safeFeatureIconSrc(props[MCX_ICON_DATA_URL] || props[MCX_ICON_HREF] || null);
    const extended: FeatureMetadataExtended[] = [];
    const seenKeys = new Set<string>();
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

/** Apply edited name and description onto a draw feature. */
export function applyFeatureMetadataEdits(
    feature: Feature | null | undefined,
    fields: FeatureMetadataEditFields | null | undefined
): void {
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
