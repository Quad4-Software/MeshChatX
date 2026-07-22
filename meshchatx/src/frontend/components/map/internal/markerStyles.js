// SPDX-License-Identifier: 0BSD

/**
 * Pure OpenLayers marker style builders for the discovery map.
 *
 * Badge SVGs use a dual halo (dark outer plus light inner rim) so the same asset
 * stays readable on both dark and light basemaps without theme branching.
 */

import { Style, Text, Fill, Stroke, Circle as CircleStyle, Icon } from "ol/style";

/** Default indigo face for peers without an LXMF user icon. */
export const DEFAULT_PEER_FACE = "#3730a3";

/** Default white glyph on peer badges. */
export const DEFAULT_PEER_GLYPH = "#ffffff";

/** Emerald face for discovered interface markers. */
export const DEFAULT_DISCOVERED_FACE = "#059669";

/** Fallback MDI-style map pin path (24x24 viewBox). */
export const DEFAULT_MAP_PIN_PATH =
    "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Zm0 11a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z";

/** Show permanent name labels at or above this zoom. */
export const MARKER_LABEL_MIN_ZOOM = 12;

/** Normal badge Icon scale. */
export const BADGE_SCALE_NORMAL = 1;

/** Hovered badge Icon scale. */
export const BADGE_SCALE_HOVER = 1.12;

const STALE_FACE = "#64748b";
const STALE_GLYPH = "#e2e8f0";

/**
 * Parse #rgb / #rrggbb into 0-1 linear-ish sRGB channels for luminance.
 * @param {string} color
 * @returns {{r:number,g:number,b:number}|null}
 */
function parseHexColor(color) {
    if (typeof color !== "string") return null;
    let hex = color.trim();
    if (hex.startsWith("#")) hex = hex.slice(1);
    if (hex.length === 3) {
        hex = hex
            .split("")
            .map((c) => c + c)
            .join("");
    }
    if (!/^[0-9a-fA-F]{6}$/.test(hex)) return null;
    return {
        r: parseInt(hex.slice(0, 2), 16) / 255,
        g: parseInt(hex.slice(2, 4), 16) / 255,
        b: parseInt(hex.slice(4, 6), 16) / 255,
    };
}

/**
 * Relative luminance (WCAG-ish) for a hex color.
 * @param {string} color
 * @returns {number} 0-1, or 0.5 when unparseable
 */
export function relativeLuminance(color) {
    const rgb = parseHexColor(color);
    if (!rgb) return 0.5;
    const lin = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    return 0.2126 * lin(rgb.r) + 0.7152 * lin(rgb.g) + 0.0722 * lin(rgb.b);
}

/**
 * Contrast ratio between two hex colors.
 * @param {string} a
 * @param {string} b
 * @returns {number}
 */
export function contrastRatio(a, b) {
    const L1 = relativeLuminance(a);
    const L2 = relativeLuminance(b);
    const lighter = Math.max(L1, L2);
    const darker = Math.min(L1, L2);
    return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Pick a readable glyph color for a badge face.
 * Prefers the preferred color when contrast against bg is at least 3 to 1.
 * @param {string} bg
 * @param {string} [preferred]
 * @returns {string}
 */
export function contrastGlyphColor(bg, preferred) {
    const white = "#ffffff";
    const ink = "#0f172a";
    if (preferred && contrastRatio(preferred, bg) >= 3) {
        return preferred;
    }
    return relativeLuminance(bg) > 0.45 ? ink : white;
}

/**
 * Whether a marker name label should render.
 * @param {{zoom?:number, hovered?:boolean, selected?:boolean}} opts
 * @returns {boolean}
 */
export function shouldShowMarkerLabel({ zoom, hovered = false, selected = false } = {}) {
    if (hovered || selected) return true;
    return Number.isFinite(zoom) && zoom >= MARKER_LABEL_MIN_ZOOM;
}

/**
 * Encode an SVG markup string as a data URL for ol/style/Icon.
 * @param {string} svg
 * @returns {string}
 */
export function encodeSvgDataUrl(svg) {
    const bytes = new TextEncoder().encode(svg);
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
        binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
    }
    return "data:image/svg+xml;base64," + btoa(binary);
}

/**
 * Build dual-halo peer / discovered badge SVG markup.
 * @param {{face:string, glyph:string, pathD?:string, stale?:boolean, tracking?:boolean}} opts
 * @returns {string}
 */
export function buildPeerBadgeSvg({ face, glyph, pathD = DEFAULT_MAP_PIN_PATH, stale = false, tracking = false } = {}) {
    const faceColor = stale ? STALE_FACE : face || DEFAULT_PEER_FACE;
    const glyphColor = stale ? STALE_GLYPH : glyph || DEFAULT_PEER_GLYPH;
    const opacity = stale ? "0.72" : "1";
    const showPulse = tracking && !stale;
    const size = showPulse ? 48 : 40;
    const cx = size / 2;
    const cy = size / 2;
    const r = showPulse ? 12 : 11;

    const pulse = showPulse
        ? `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#38bdf8" stroke-width="2">
            <animate attributeName="r" from="${r}" to="${r + 8}" dur="1.5s" repeatCount="indefinite" />
            <animate attributeName="stroke-opacity" from="0.9" to="0" dur="1.5s" repeatCount="indefinite" />
          </circle>
          <circle cx="${cx}" cy="${cy}" r="${r - 1}" fill="#38bdf8" fill-opacity="0.18">
            <animate attributeName="r" from="${r - 2}" to="${r + 3}" dur="1.5s" repeatCount="indefinite" />
            <animate attributeName="fill-opacity" from="0.22" to="0" dur="1.5s" repeatCount="indefinite" />
          </circle>`
        : "";

    // Dual halo is dark outer rim plus light inner rim then face fill then glyph.
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <g opacity="${opacity}">
    <circle class="badge-shadow" cx="${cx + 0.6}" cy="${cy + 1.1}" r="${r + 1}" fill="rgba(15,23,42,0.28)"/>
    ${pulse}
    <circle class="badge-rim-dark" cx="${cx}" cy="${cy}" r="${r}" fill="${faceColor}" stroke="rgba(15,23,42,0.78)" stroke-width="3"/>
    <circle class="badge-rim-light" cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(255,255,255,0.92)" stroke-width="1.6"/>
    <g transform="translate(${cx},${cy}) scale(0.52) translate(-12,-12)">
      <path d="${pathD}" fill="${glyphColor}"/>
    </g>
  </g>
</svg>`;
}

/**
 * Create an OpenLayers Style for a peer / discovered / note badge.
 * @param {object} opts
 * @param {string} [opts.face]
 * @param {string} [opts.glyph]
 * @param {string} [opts.iconColor] preferred glyph (legacy name from MapPage)
 * @param {string} [opts.bgColor] face (legacy name from MapPage)
 * @param {string} [opts.pathD]
 * @param {string} [opts.iconPath] alias for pathD
 * @param {string} [opts.label]
 * @param {boolean} [opts.showLabel]
 * @param {boolean} [opts.isStale]
 * @param {boolean} [opts.isTracking]
 * @param {number} [opts.scale]
 * @returns {import("ol/style/Style").default}
 */
export function peerBadgeStyle({
    face,
    glyph,
    iconColor,
    bgColor,
    pathD,
    iconPath,
    label = "",
    showLabel = false,
    isStale = false,
    isTracking = false,
    scale = BADGE_SCALE_NORMAL,
} = {}) {
    const resolvedFace = face || bgColor || DEFAULT_PEER_FACE;
    const preferredGlyph = glyph || iconColor || DEFAULT_PEER_GLYPH;
    const resolvedGlyph = isStale ? STALE_GLYPH : contrastGlyphColor(resolvedFace, preferredGlyph);
    const d = pathD || iconPath || DEFAULT_MAP_PIN_PATH;

    const svg = buildPeerBadgeSvg({
        face: resolvedFace,
        glyph: resolvedGlyph,
        pathD: d,
        stale: isStale,
        tracking: isTracking,
    });
    const src = encodeSvgDataUrl(svg);
    const renderSize = isTracking && !isStale ? 48 : 40;
    const displayHeight = renderSize * scale;
    const labelOffset = -(displayHeight / 2 + 8);

    const styleOpts = {
        image: new Icon({
            src,
            anchor: [0.5, 0.5],
            scale,
            imgSize: [renderSize, renderSize],
        }),
    };

    if (showLabel && label) {
        styleOpts.text = new Text({
            text: String(label),
            offsetY: labelOffset,
            font: "bold 12px sans-serif",
            fill: new Fill({ color: isStale ? "#6b7280" : "#111827" }),
            stroke: new Stroke({ color: "#ffffff", width: 3 }),
        });
    }

    return new Style(styleOpts);
}

/**
 * Cluster size / color band for a marker count.
 * @param {number} count
 * @returns {{bandId:string, radius:number, face:string}}
 */
export function clusterBand(count) {
    const n = Number.isFinite(count) ? Math.max(0, Math.floor(count)) : 0;
    if (n < 10) {
        return { bandId: "s", radius: 16, face: "#2563eb" };
    }
    if (n < 50) {
        return { bandId: "m", radius: 20, face: "#7c3aed" };
    }
    return { bandId: "l", radius: 24, face: "#c2410c" };
}

/**
 * Dual-halo cluster badge as layered OpenLayers styles (no SVG encode).
 * @param {{count:number, hovered?:boolean}} opts
 * @returns {import("ol/style/Style").default[]}
 */
export function clusterBadgeStyle({ count = 0, hovered = false } = {}) {
    const band = clusterBand(count);
    const radius = hovered ? band.radius + 2 : band.radius;
    const label = String(count);

    return [
        new Style({
            image: new CircleStyle({
                radius: radius + 2.5,
                fill: new Fill({ color: "rgba(15, 23, 42, 0.32)" }),
                stroke: new Stroke({ color: "rgba(15, 23, 42, 0.55)", width: 2 }),
            }),
            zIndex: 0,
        }),
        new Style({
            image: new CircleStyle({
                radius,
                fill: new Fill({ color: band.face }),
                stroke: new Stroke({ color: "#ffffff", width: 2.5 }),
            }),
            text: new Text({
                text: label,
                font: "bold 13px sans-serif",
                fill: new Fill({ color: "#ffffff" }),
                stroke: new Stroke({ color: "rgba(15,23,42,0.45)", width: 2 }),
            }),
            zIndex: 1,
        }),
    ];
}

/**
 * Cache-aware cluster style helper.
 * @param {Record<string, import("ol/style/Style").default[]>} cache
 * @param {{count:number, hovered?:boolean}} opts
 * @returns {import("ol/style/Style").default[]}
 */
export function getCachedClusterStyle(cache, { count = 0, hovered = false } = {}) {
    const band = clusterBand(count);
    const key = `cluster-v2-${band.bandId}-${count}-${hovered ? "h" : "n"}`;
    if (cache[key]) return cache[key];
    const style = clusterBadgeStyle({ count, hovered });
    cache[key] = style;
    return style;
}

/**
 * Cache-aware peer badge style helper.
 * @param {Record<string, import("ol/style/Style").default>} cache
 * @param {object} opts
 * @returns {import("ol/style/Style").default}
 */
export function getCachedPeerBadgeStyle(cache, opts = {}) {
    const {
        face,
        glyph,
        iconColor,
        bgColor,
        pathD,
        iconPath,
        label = "",
        showLabel = false,
        isStale = false,
        isTracking = false,
        scale = BADGE_SCALE_NORMAL,
    } = opts;
    const resolvedFace = face || bgColor || DEFAULT_PEER_FACE;
    const preferredGlyph = glyph || iconColor || DEFAULT_PEER_GLYPH;
    const resolvedGlyph = isStale ? STALE_GLYPH : contrastGlyphColor(resolvedFace, preferredGlyph);
    const d = pathD || iconPath || DEFAULT_MAP_PIN_PATH;
    const labelKey = showLabel && label ? String(label) : "";
    const key = [
        "peer-v2",
        resolvedFace,
        resolvedGlyph,
        d,
        labelKey,
        showLabel ? "1" : "0",
        isStale ? "1" : "0",
        isTracking ? "1" : "0",
        scale,
    ].join("|");
    if (cache[key]) return cache[key];
    const style = peerBadgeStyle({
        face: resolvedFace,
        glyph: resolvedGlyph,
        pathD: d,
        label,
        showLabel,
        isStale,
        isTracking,
        scale,
    });
    cache[key] = style;
    return style;
}
