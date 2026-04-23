// SPDX-License-Identifier: 0BSD

import { Circle as CircleStyle, Fill, Icon, Stroke, Style } from "ol/style";
import LineString from "ol/geom/LineString";
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

const SIMPLE_MARKER_COLOR = "marker-color";
const SIMPLE_MARKER_SIZE_KEY = "marker-size";

const ICON_BASE_CSS_PX = 32;
const ICON_WIDTH_MIN_PX = 8;
const ICON_WIDTH_MAX_PX = 40;

function num(v, fallback) {
    const n = typeof v === "number" ? v : parseFloat(v);
    return Number.isFinite(n) ? n : fallback;
}

function hexToRgba(hex, alpha = 1) {
    if (!hex || typeof hex !== "string") {
        return `rgba(59,130,246,${alpha})`;
    }
    let h = hex.trim();
    if (h.startsWith("#")) {
        h = h.slice(1);
    }
    if (h.length === 3) {
        h = h
            .split("")
            .map((c) => c + c)
            .join("");
    }
    if (h.length !== 6) {
        return `rgba(59,130,246,${alpha})`;
    }
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}

function circleRadiusFromSimpleSize(markerSize) {
    const s = String(markerSize || "medium").toLowerCase();
    if (s === "small") {
        return 5;
    }
    if (s === "large") {
        return 11;
    }
    return 8;
}

/**
 * Build an OpenLayers Style from MeshChatX / simplestyle-ish feature properties.
 * Used when the feature has no per-feature style (e.g. GeoJSON import).
 * @param {import("ol/Feature").default} feature
 * @returns {import("ol/style/Style").default|null}
 */
/**
 * Replace OL KML icon styles with a capped MCX icon style when metadata is present.
 * Avoids full-resolution bitmaps when scale was captured before the image finished loading.
 * @param {import("ol/Feature").default} feature
 */
export function applyCappedMcxIconStyleIfNeeded(feature) {
    const g = feature.getGeometry();
    if (!g) {
        return;
    }
    const t = g.getType();
    if (t !== "Point" && t !== "MultiPoint") {
        return;
    }
    const p = feature.getProperties();
    if (!(p[MCX_ICON_DATA_URL] || p[MCX_ICON_HREF])) {
        return;
    }
    const built = styleFromMcxProperties(feature);
    if (built) {
        feature.setStyle(built);
    }
}

export function styleFromMcxProperties(feature) {
    const geom = feature.getGeometry();
    if (!geom) {
        return null;
    }
    const p = feature.getProperties();
    const type = geom.getType();

    const iconSrc = p[MCX_ICON_DATA_URL] || p[MCX_ICON_HREF];
    if (iconSrc && (type === "Point" || type === "MultiPoint")) {
        const factor = num(p[MCX_ICON_SCALE], 1);
        const widthPx = Math.round(Math.min(ICON_WIDTH_MAX_PX, Math.max(ICON_WIDTH_MIN_PX, ICON_BASE_CSS_PX * factor)));
        const ax = num(p[MCX_ICON_ANCHOR_X], 0.5);
        const ay = num(p[MCX_ICON_ANCHOR_Y], 1);
        const isData = String(iconSrc).startsWith("data:");
        return new Style({
            image: new Icon({
                src: iconSrc,
                width: widthPx,
                anchor: [ax, ay],
                crossOrigin: isData ? undefined : "anonymous",
            }),
        });
    }

    if (type === "Point" || type === "MultiPoint") {
        const mc = p[SIMPLE_MARKER_COLOR] || p["marker-color"];
        if (mc) {
            const r = circleRadiusFromSimpleSize(p[SIMPLE_MARKER_SIZE_KEY]);
            return new Style({
                image: new CircleStyle({
                    radius: r,
                    fill: new Fill({ color: hexToRgba(mc, 0.85) }),
                    stroke: new Stroke({ color: "#1f2937", width: 1 }),
                }),
            });
        }
    }

    const strokeRaw = p[MCX_STROKE_COLOR] ?? p.stroke ?? "#2563eb";
    const strokeWidth = num(p[MCX_STROKE_WIDTH] ?? p["stroke-width"], 2);
    const fillRaw = p[MCX_FILL_COLOR] ?? p.fill;
    const fillOpacity = num(p[MCX_FILL_OPACITY] ?? p["fill-opacity"], fillRaw ? 0.35 : 0);

    const stroke = new Stroke({
        color: /** @type {import("ol/color").Color|string} */ (strokeRaw),
        width: strokeWidth,
    });

    if (type === "LineString" || type === "MultiLineString") {
        return new Style({ stroke });
    }

    if (type === "Polygon" || type === "MultiPolygon") {
        let fill;
        if (fillRaw) {
            fill =
                typeof fillRaw === "string"
                    ? new Fill({
                          color: hexToRgba(fillRaw, fillOpacity > 0 ? fillOpacity : 0.35),
                      })
                    : new Fill({ color: /** @type {import("ol/color").Color} */ (fillRaw) });
        } else {
            fill = new Fill({ color: "rgba(59, 130, 246, 0.2)" });
        }
        return new Style({ stroke, fill });
    }

    if (type === "Circle") {
        const g = /** @type {import("ol/geom/Circle").default} */ (geom);
        const center = g.getCenter();
        const edge = [center[0] + g.getRadius(), center[1]];
        const line = new LineString([center, edge]);
        return new Style({
            stroke,
            geometry: line,
        });
    }

    return null;
}

/**
 * Copy icon/stroke metadata from an OpenLayers Style into feature properties for GeoJSON export.
 * @param {import("ol/style/Style").default} style
 * @param {import("ol/Feature").default} feature
 */
export function copyStyleMetadataToProperties(style, feature) {
    if (!style || !feature) {
        return;
    }
    const styles = Array.isArray(style) ? style : [style];
    for (const st of styles) {
        if (!st || typeof st.getImage !== "function") {
            continue;
        }
        const img = st.getImage();
        if (img && typeof img.getSrc === "function") {
            const src = img.getSrc();
            if (src) {
                if (String(src).startsWith("data:")) {
                    feature.set(MCX_ICON_DATA_URL, src);
                } else {
                    feature.set(MCX_ICON_HREF, src);
                }
                const sc = img.getScale();
                if (sc != null) {
                    feature.set(MCX_ICON_SCALE, sc);
                }
                const anchor = img.getAnchor && img.getAnchor();
                if (anchor && anchor.length >= 2) {
                    feature.set(MCX_ICON_ANCHOR_X, anchor[0]);
                    feature.set(MCX_ICON_ANCHOR_Y, anchor[1]);
                }
            }
        }
        if (typeof st.getStroke === "function") {
            const s = st.getStroke();
            if (s && s.getColor()) {
                feature.set(MCX_STROKE_COLOR, s.getColor());
                feature.set(MCX_STROKE_WIDTH, s.getWidth());
            }
        }
        if (typeof st.getFill === "function") {
            const f = st.getFill();
            if (f && f.getColor()) {
                feature.set(MCX_FILL_COLOR, f.getColor());
            }
        }
    }
}

/**
 * After KML import, mirror style into mcx_* props so GeoJSON export keeps icons.
 * @param {import("ol/Feature").default[]} features
 */
export function normalizeKmlImportedFeatures(features) {
    for (const f of features) {
        let st = f.getStyle();
        if (typeof st === "function") {
            st = st(f);
        }
        const list = st == null ? [] : Array.isArray(st) ? st : [st];
        for (const s of list) {
            copyStyleMetadataToProperties(s, f);
        }
        applyCappedMcxIconStyleIfNeeded(f);
    }
}

/**
 * Ensure each feature has an OL style for KML export when only properties were set.
 * Mutates features (sets style).
 * @param {import("ol/Feature").default[]} features
 */
export function ensureOlStylesForKmlExport(features) {
    for (const f of features) {
        let st = f.getStyle();
        if (typeof st === "function") {
            st = null;
        }
        if (st != null) {
            continue;
        }
        const built = styleFromMcxProperties(f);
        if (built) {
            f.setStyle(built);
        }
    }
}
