// SPDX-License-Identifier: 0BSD

// Detects geographic references in chat text and turns them into geo links.
// Maidenhead grid locators and plain lat/lon pairs decode locally; anything
// else coordinate-looking (MGRS, UTM, Plus Code) resolves on click through
// parseCoordinateQuery so it works without loading geo-wasm during render.

// eslint-disable-next-line security/detect-unsafe-regex -- fixed-width character classes
const MAIDENHEAD_RE = /\b([A-Ra-r]{2}[0-9]{2}[A-Xa-x]{2}([0-9]{2})?)\b/g;
// eslint-disable-next-line security/detect-unsafe-regex -- bounded quantifiers only
const LATLON_RE = /(?<![\w.])(-?\d{1,2}(?:\.\d{1,8})?)\s*[, ]\s*(-?\d{1,3}(?:\.\d{1,8})?)(?![\w.])/g;
const EXPLICIT_RE = /\b(?:geo|grid|locator):([A-Za-z0-9 .,+\-/]{2,32})/g;

function escapeAttr(s) {
    return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

/**
 * Decode a Maidenhead (grid square) locator to its center WGS84 point.
 * Accepts 4, 6 or 8 char forms: FN20, FN20pr, FN20pr42.
 * Returns {lat, lon} or null.
 */
export function decodeMaidenhead(locator) {
    const loc = String(locator || "").trim();
    // eslint-disable-next-line security/detect-unsafe-regex -- single-char captures only
    const m = /^([A-Ra-r])([A-Ra-r])([0-9])([0-9])([A-Xa-x]([A-Xa-x])?)?([0-9]([0-9])?)?$/.exec(loc);
    if (!m) return null;
    const lonField = m[1].toUpperCase().charCodeAt(0) - 65;
    const latField = m[2].toUpperCase().charCodeAt(0) - 65;
    const lonSq = Number(m[3]);
    const latSq = Number(m[4]);
    let lon = lonField * 20 - 180 + lonSq * 2;
    let lat = latField * 10 - 90 + latSq * 1;
    let w = 2;
    let h = 1;
    if (m[5] && m[6]) {
        const lonSub = m[5].toUpperCase().charCodeAt(0) - 65;
        const latSub = m[6].toUpperCase().charCodeAt(0) - 65;
        lon += (lonSub * w) / 24;
        lat += (latSub * h) / 24;
        w /= 24;
        h /= 24;
    }
    if (m[7] && m[8]) {
        lon += Number(m[7]) * (w / 10);
        lat += Number(m[8]) * (h / 10);
        w /= 10;
        h /= 10;
    }
    return { lat: lat + h / 2, lon: lon + w / 2 };
}

function isMaidenhead(token) {
    return decodeMaidenhead(token) !== null;
}

function geoAnchor(display, text) {
    return (
        `<a href="#" class="geo-link text-blue-600 dark:text-blue-400 hover:underline font-mono"` +
        ` data-geo-text="${escapeAttr(text)}">${escapeAttr(display)}</a>`
    );
}

/**
 * Wrap geographic references in the (already HTML-escaped) text with anchors.
 * Runs inside MarkdownRenderer.renderBasic before emphasis rules.
 */
export function linkifyGeoRefs(text) {
    if (typeof text !== "string" || !text) return text;
    let out = text;

    // Explicit geo:/grid:/locator: schemes always link.
    out = out.replace(EXPLICIT_RE, (match, body) => geoAnchor(body.trim(), body.trim()));

    // Maidenhead locators, 6+ chars only for auto-linking to avoid noise.
    out = out.replace(MAIDENHEAD_RE, (match) => geoAnchor(match, match));

    // lat, lon decimal pairs within plausible ranges.
    out = out.replace(LATLON_RE, (match, latS, lonS) => {
        const lat = parseFloat(latS);
        const lon = parseFloat(lonS);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return match;
        if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return match;
        return geoAnchor(match, match);
    });

    return out;
}

/**
 * Resolve geo-link text to {lat, lon} or null. Maidenhead is decoded locally;
 * everything else defers to parseCoordinateQuery (WGS84, UTM, MGRS, Plus Code).
 */
export async function resolveGeoText(text, options = {}) {
    const raw = String(text || "").trim();
    if (!raw) return null;
    const mh = decodeMaidenhead(raw);
    if (mh) return { ...mh, kind: "grid" };
    const { parseCoordinateQuery } = await import("./mapGeoCoords.js");
    const res = parseCoordinateQuery(raw, options);
    if (res && res.ok && Number.isFinite(res.lat) && Number.isFinite(res.lon)) {
        return { lat: res.lat, lon: res.lon, kind: res.kind || "coords" };
    }
    return null;
}

export { isMaidenhead };
